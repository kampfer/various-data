"""调度器入口。

启动方式：
    uv run --project src/backend python src/backend/scheduler/main.py --mode dev
    uv run --project src/backend python src/backend/scheduler/main.py --mode dev --run-once sina_news
    uv run --project src/backend python src/backend/scheduler/main.py --mode dev --print-registry
"""

from __future__ import annotations

import argparse
import sys
from datetime import timedelta
from pathlib import Path

# 直接执行本文件时，把 backend 加入 sys.path，使 scheduler / admin 包可导入。
_SRC_DIR = Path(__file__).resolve().parents[1]
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

from apscheduler.schedulers.blocking import BlockingScheduler  # noqa: E402

from admin.api import AdminContext, create_app  # noqa: E402
from admin.server import AdminServer, AdminServerError  # noqa: E402
from scheduler.alert import Notifier  # noqa: E402
from scheduler.catchup import previous_trigger, run_catchup  # noqa: E402
from scheduler.config import (  # noqa: E402
    ADMIN_ROOT_PATH,
    TZ,
    AdminSettings,
    build_config,
    describe_config,
    now,
    now_iso,
    to_iso,
)
from scheduler.lib.log import LOG_FILE_NAME, setup_logging  # noqa: E402
from scheduler.registry import build_registry, find_spec  # noqa: E402
from scheduler.runner import Runner  # noqa: E402
from scheduler.store import Store  # noqa: E402

RETENTION_DAYS = 90


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="各种数据定时任务调度器（APScheduler + SQLite 账本）"
    )
    parser.add_argument(
        "--mode",
        choices=["dev", "pro"],
        default="dev",
        help="运行环境：dev 使用 various_data_dev.db（默认），pro 使用 various_data.db",
    )
    parser.add_argument(
        "--run-once",
        metavar="JOB_ID",
        help="立即执行一次指定任务后退出（sina_news / omo / db_backup）",
    )
    parser.add_argument(
        "--print-registry",
        action="store_true",
        help="打印任务注册表后退出",
    )
    parser.add_argument(
        "--no-admin",
        action="store_true",
        help="不启动后台管理服务（默认在 127.0.0.1:8787 启动）",
    )
    parser.add_argument(
        "--admin-host",
        default="127.0.0.1",
        help="后台管理服务监听地址（默认 127.0.0.1）",
    )
    parser.add_argument(
        "--admin-port",
        type=int,
        default=8787,
        help="后台管理服务监听端口（默认 8787）",
    )
    return parser.parse_args(argv)


def _make_enqueue_callback(spec, trigger, store, runner, logger):
    def callback() -> None:
        at = now()
        scheduled = previous_trigger(trigger, at) or at
        scheduled_iso = to_iso(scheduled)
        inserted = store.enqueue(
            job_id=spec.id,
            scheduled_at=scheduled_iso,
            trigger_kind="schedule",
            max_attempts=spec.max_attempts,
            missed_count=1,
            created_at=to_iso(at),
        )
        store.advance_state(spec.id, scheduled_iso, to_iso(at))
        if inserted:
            logger.info("触发入账 job=%s scheduled_at=%s", spec.id, scheduled_iso)
        runner.wake()

    return callback


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    admin_settings = AdminSettings(
        enabled=not args.no_admin,
        host=args.admin_host,
        port=args.admin_port,
    )
    if not 1 <= admin_settings.port <= 65535:
        raise SystemExit(f"管理服务端口不合法: {admin_settings.port}")
    config = build_config(args.mode, admin_settings)
    logger = setup_logging(config.log_dir)
    logger.info("调度器配置: %s", describe_config(config))

    registry = build_registry(config)

    if args.print_registry:
        for spec in registry:
            logger.info("注册任务: %s", spec.describe())
        return 0

    if args.run_once:
        try:
            spec = find_spec(registry, args.run_once)
        except KeyError as exc:
            logger.error("%s", exc.args[0])
            return 2
        try:
            spec.func()
        except Exception:
            logger.exception("任务 %s 单次执行失败", spec.id)
            return 1
        logger.info("任务 %s 单次执行成功", spec.id)
        return 0

    store = Store(config.ledger_path)
    notifier = Notifier(config.smtp)
    at = now()

    requeued, terminal = store.recover_interrupted(
        at=to_iso(at), error="进程在执行中中断"
    )
    removed = store.cleanup(
        cutoff=to_iso(at - timedelta(days=RETENTION_DAYS)), at=to_iso(at)
    )
    catchup = run_catchup(store, registry, notifier, at)
    pending_retries = store.count_pending_retries()

    logger.info(
        "启动摘要: 补跑=%d 丢失=%d 待重试=%d 中断重排=%d 中断判失败=%d 清理=%d",
        catchup.backfilled,
        catchup.lost,
        pending_retries,
        requeued,
        terminal,
        removed,
    )

    runner = Runner(store, registry, notifier, logger)
    runner.start()

    admin_server: AdminServer | None = None
    if config.admin.enabled:
        if not config.admin.is_loopback:
            logger.warning(
                "管理服务已对外暴露且无鉴权: %s（请确认网络访问范围）",
                config.admin.describe(),
            )
        context = AdminContext(
            config=config,
            store=store,
            registry=registry,
            runner=runner,
            started_at=now(),
            log_path=config.log_dir / LOG_FILE_NAME,
            static_dir=config.repo_root / ADMIN_ROOT_PATH,
        )
        admin_server = AdminServer(create_app(context), config.admin, logger)
        try:
            admin_server.start()
        except AdminServerError as exc:
            logger.error("管理服务启动失败（%s）: %s", exc.kind, exc)
            runner.stop()
            return 1
        logger.info("管理服务已启动: %s", config.admin.describe())

    scheduler = BlockingScheduler(
        job_defaults={
            "coalesce": False,
            "max_instances": 1,
            "misfire_grace_time": None,
        },
        timezone=TZ,
    )

    for spec in registry:
        trigger = spec.build_trigger()
        scheduler.add_job(
            _make_enqueue_callback(spec, trigger, store, runner, logger),
            trigger=trigger,
            id=spec.id,
            name=spec.name,
            replace_existing=True,
            misfire_grace_time=None,
        )
        logger.info("注册任务: %s", spec.describe())

    logger.info("调度器启动（按 Ctrl+C 退出）")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("收到退出信号，正在停止调度器")
    finally:
        try:
            scheduler.shutdown(wait=False)
        except Exception:
            pass
        runner.stop()
        if admin_server is not None:
            admin_server.stop()
        logger.info("调度器已停止")

    return 0


if __name__ == "__main__":
    sys.exit(main())
