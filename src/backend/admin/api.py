"""管理服务 REST 接口。

所有依赖通过 :class:`AdminContext` 显式注入，模块内不读取全局状态，便于测试。
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from scheduler.config import Config, now, now_iso, to_iso
from scheduler.registry import JobSpec
from scheduler.store import (
    ACTIVE_STATUSES,
    ALL_STATUSES,
    STATUS_FAILED,
    Store,
    TRIGGER_MANUAL,
)

logger = logging.getLogger("scheduler")

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 200
DEFAULT_LOG_LINES = 200
MAX_LOG_LINES = 2000
MAX_CLEANUP_DAYS = 3650
LOG_READ_BLOCK = 8192


class RunnerWaker(Protocol):
    """只依赖唤醒能力，测试里可用假实现替换真实消费者。"""

    def wake(self) -> None: ...


@dataclass(frozen=True)
class AdminContext:
    config: Config
    store: Store
    registry: list[JobSpec]
    runner: RunnerWaker
    started_at: datetime
    log_path: Path
    static_dir: Path


class CleanupRequest(BaseModel):
    days: int = Field(ge=1, le=MAX_CLEANUP_DAYS, description="保留天数")


def _describe_cron(cron: dict) -> str:
    """把注册表里的 cron 参数转成可读描述，覆盖本项目现有三种周期。"""

    try:
        minute = int(cron.get("minute", 0))
        hour = cron.get("hour")
        day = cron.get("day")
        if day is not None and hour is not None:
            return f"每月 {int(day)} 日 {int(hour):02d}:{minute:02d}"
        if hour is not None:
            return f"每天 {int(hour):02d}:{minute:02d}"
        return f"每小时第 {minute} 分"
    except (TypeError, ValueError):
        return " ".join(f"{key}={value}" for key, value in cron.items())


def _tail_lines(path: Path, limit: int) -> tuple[list[str], bool, str | None]:
    """从文件尾部按块读取，返回 (行列表, 是否截断, 错误提示)。"""

    if not path.exists():
        return [], False, "日志文件不存在"
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            position = handle.tell()
            data = b""
            while position > 0 and data.count(b"\n") <= limit:
                step = min(LOG_READ_BLOCK, position)
                position -= step
                handle.seek(position)
                data = handle.read(step) + data
    except OSError as exc:
        return [], False, f"读取日志失败: {exc}"

    lines = data.decode("utf-8", errors="replace").splitlines()
    truncated = len(lines) > limit
    return lines[-limit:], truncated, None


def create_app(context: AdminContext) -> FastAPI:
    app = FastAPI(
        title="various-data scheduler admin",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.state.context = context

    store = context.store
    registry = context.registry
    runner = context.runner

    def find_spec(job_id: str) -> JobSpec:
        for spec in registry:
            if spec.id == job_id:
                return spec
        raise HTTPException(status_code=404, detail=f"未注册的任务: {job_id}")

    def load_run(run_id: int) -> dict:
        run = store.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail=f"运行记录不存在: {run_id}")
        return run

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/api/overview")
    def overview() -> dict:
        moment = now()
        today_start = to_iso(
            moment.replace(hour=0, minute=0, second=0, microsecond=0)
        )
        stats = store.overview_stats(today_start)
        return {
            "mode": context.config.mode,
            "db_path": str(context.config.db_path),
            "ledger_path": str(context.config.ledger_path),
            "started_at": to_iso(context.started_at),
            "admin": {
                "enabled": context.config.admin.enabled,
                "host": context.config.admin.host,
                "port": context.config.admin.port,
            },
            "today_start": today_start,
            **stats,
        }

    @app.get("/api/jobs")
    def jobs() -> list[dict]:
        moment = now()
        items: list[dict] = []
        for spec in registry:
            trigger = spec.build_trigger()
            next_fire = trigger.get_next_fire_time(None, moment)
            items.append(
                {
                    "id": spec.id,
                    "name": spec.name,
                    "cron": spec.cron,
                    "cron_text": _describe_cron(spec.cron),
                    "catchup": spec.catchup,
                    "max_attempts": spec.max_attempts,
                    "retry_interval_seconds": spec.retry_interval_seconds,
                    "next_run_at": to_iso(next_fire) if next_fire else None,
                    "watermark": store.get_state(spec.id),
                    "last_run": store.last_run(spec.id),
                }
            )
        return items

    @app.get("/api/runs")
    def runs(
        job_id: str | None = None,
        status: str | None = None,
        page: int = Query(1),
        page_size: int = Query(DEFAULT_PAGE_SIZE),
    ) -> dict:
        if status is not None and status not in ALL_STATUSES:
            raise HTTPException(status_code=422, detail=f"未知状态: {status}")
        page = max(1, page)
        page_size = min(max(1, page_size), MAX_PAGE_SIZE)
        total, items = store.list_runs(
            job_id=job_id, status=status, page=page, page_size=page_size
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
            "statuses": list(ALL_STATUSES),
        }

    @app.get("/api/runs/{run_id}")
    def run_detail(run_id: int) -> dict:
        return load_run(run_id)

    @app.get("/api/logs")
    def logs(lines: int = Query(DEFAULT_LOG_LINES)) -> dict:
        limit = min(max(1, lines), MAX_LOG_LINES)
        content, truncated, error = _tail_lines(context.log_path, limit)
        return {
            "path": str(context.log_path),
            "requested": lines,
            "limit": limit,
            "count": len(content),
            "truncated": truncated,
            "lines": content,
            "error": error,
        }

    @app.post("/api/jobs/{job_id}/run")
    def run_job(job_id: str) -> dict:
        spec = find_spec(job_id)
        at = now_iso()
        created, run_id = store.enqueue_manual(
            job_id=spec.id,
            scheduled_at=at,
            max_attempts=spec.max_attempts,
            created_at=at,
        )
        if created:
            runner.wake()
        return {
            "created": created,
            "run_id": run_id,
            "trigger_kind": TRIGGER_MANUAL,
            "message": "已入队" if created else "同一秒内已存在，未重复入队",
        }

    @app.post("/api/runs/{run_id}/retry")
    def retry_run(run_id: int) -> dict:
        run = load_run(run_id)
        if run["status"] != STATUS_FAILED:
            raise HTTPException(
                status_code=409,
                detail=f"只有 failed 记录可以重试，当前为 {run['status']}",
            )
        if not store.requeue_failed(run_id):
            raise HTTPException(status_code=409, detail="记录状态已变化，重试未生效")
        runner.wake()
        return {"ok": True, "run_id": run_id, "message": "已重新入队，将补充一次尝试"}

    @app.post("/api/runs/{run_id}/cancel")
    def cancel_run(run_id: int) -> dict:
        run = load_run(run_id)
        if run["status"] not in ACTIVE_STATUSES:
            raise HTTPException(
                status_code=409,
                detail=f"只有待执行记录可以取消，当前为 {run['status']}",
            )
        if not store.cancel_pending(run_id, now_iso()):
            raise HTTPException(status_code=409, detail="记录状态已变化，取消失败")
        return {"ok": True, "run_id": run_id, "message": "已取消"}

    @app.post("/api/runs/cleanup")
    def cleanup(payload: CleanupRequest) -> dict:
        at = now()
        cutoff = to_iso(at - timedelta(days=payload.days))
        removed = store.cleanup(cutoff=cutoff, at=to_iso(at))
        return {"ok": True, "removed": removed, "cutoff": cutoff}

    if (context.static_dir / "index.html").exists():
        app.mount(
            "/",
            StaticFiles(directory=str(context.static_dir), html=True),
            name="admin",
        )
    else:
        logger.warning(
            "管理页面未构建，静态资源目录不存在: %s（请在 src/frontEnd 执行 npm run build）",
            context.static_dir,
        )

        @app.get("/", response_class=PlainTextResponse)
        def index_missing() -> PlainTextResponse:
            return PlainTextResponse(
                "管理页面尚未构建，请先在 src/frontEnd 执行 npm install && npm run build",
                status_code=503,
            )

    return app
