"""定时任务调度器独立服务入口。

将原本随 FastAPI Web 服务一起启动的调度器提取为独立进程运行，
便于将 Web 服务与定时任务解耦、单独部署与重启。

调度器实际执行的任务及其数据依赖（见 app/tasks/）：
    - crawlSinaNews：每小时抓取新浪财经快讯，写入 sinaFinanceNews 相关表
    - crawlOMO：每天抓取央行公开市场操作，写入 omo 相关表（含 app_state）
    - backupDatabase：每月拷贝数据库文件，无需任何 model
    - pickStock：未注册定时任务，仅供调试，无数据库依赖

因此本服务只初始化上述任务真正用到的表（新浪快讯、OMO），
不涉及 Web 端投资台账（investmentLedger）的表结构。

启动方式（在 backEnd 目录下）：
    python scheduler_service.py            # 开发环境（默认，使用 various_data_dev.db）
    python scheduler_service.py --mode pro # 生产环境（使用 various_data.db）
"""

import argparse
import os


def parseArgs() -> argparse.Namespace:
    """解析命令行参数，控制运行环境（dev / pro）。"""
    parser = argparse.ArgumentParser(description="定时任务调度器独立服务")
    parser.add_argument(
        "--mode",
        choices=["dev", "pro"],
        default="dev",
        help="运行环境：dev 使用开发数据库（默认），pro 使用生产数据库",
    )
    return parser.parse_args()


def main() -> None:
    args = parseArgs()
    # 必须在导入 app.database 之前设置 mode 环境变量，
    # 因为 database 模块在导入时即根据 mode 决定使用的数据库文件与日志开关。
    os.environ["mode"] = args.mode

    # 延迟导入：确保上面的环境变量已生效
    from app.database import engine
    from app.sinaFinanceNews.models import Base as SinaNewsBase
    from app.omo.models import Base as OMOBase
    from app.scheduler import initScheduler

    # 仅创建定时任务所依赖的表：新浪财经快讯与央行公开市场操作，
    # 不含 Web 端投资台账（investmentLedger）的表。
    SinaNewsBase.metadata.create_all(bind=engine)
    OMOBase.metadata.create_all(bind=engine)

    # 独立服务使用阻塞式调度器，占用主线程持续运行
    scheduler = initScheduler(blocking=True)
    print(f"定时任务调度器独立服务启动中（mode={args.mode}）……（按 Ctrl+C 退出）")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        # 收到中断信号时优雅关闭，等待正在执行的任务结束
        scheduler.shutdown(wait=True)
        print("定时任务调度器已关闭")


if __name__ == "__main__":
    main()
