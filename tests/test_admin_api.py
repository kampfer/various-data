"""管理服务 API 的接口契约测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from admin.api import AdminContext, create_app
from scheduler.config import build_config, now
from scheduler.registry import build_registry
from scheduler.store import Store


class FakeRunner:
    def __init__(self) -> None:
        self.wake_count = 0

    def wake(self) -> None:
        self.wake_count += 1


@dataclass
class Env:
    client: TestClient
    store: Store
    runner: FakeRunner
    log_path: Path


def make_env(tmp_path: Path, with_static: bool = False) -> Env:
    config = build_config("dev")
    store = Store(tmp_path / "ledger.db")
    runner = FakeRunner()
    log_path = tmp_path / "scheduler.log"
    static_dir = tmp_path / "static"
    if with_static:
        static_dir.mkdir()
        (static_dir / "index.html").write_text("<div id=\"admin-marker\">ok</div>", encoding="utf-8")
    context = AdminContext(
        config=config,
        store=store,
        registry=build_registry(config),
        runner=runner,
        started_at=now(),
        log_path=log_path,
        static_dir=static_dir,
    )
    return Env(TestClient(create_app(context)), store, runner, log_path)


def _pending_run(store: Store, job_id: str = "sina_news", scheduled: str = "2026-01-01T10:00:00+08:00") -> int:
    assert store.enqueue(job_id, scheduled, "schedule", 3, 1, "2026-01-01T09:00:00+08:00")
    _, rows = store.list_runs(job_id=job_id)
    return int(rows[0]["id"])


def test_overview_exposes_required_fields(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    _pending_run(env.store)

    payload = env.client.get("/api/overview").json()

    for key in (
        "mode",
        "db_path",
        "ledger_path",
        "started_at",
        "pending",
        "retrying",
        "running",
        "success_today",
        "failed_today",
    ):
        assert key in payload
    assert payload["pending"] == 1
    assert payload["admin"]["host"] == "127.0.0.1"


def test_jobs_include_registry_and_next_run(tmp_path: Path) -> None:
    env = make_env(tmp_path)

    items = env.client.get("/api/jobs").json()

    assert len(items) == 3
    first = items[0]
    for key in (
        "id",
        "name",
        "cron",
        "cron_text",
        "catchup",
        "max_attempts",
        "retry_interval_seconds",
        "next_run_at",
        "watermark",
        "last_run",
    ):
        assert key in first
    assert first["next_run_at"] is not None
    assert first["last_run"] is None
    assert first["cron_text"]


def test_runs_pagination_filters_and_limits(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    for index in range(3):
        env.store.enqueue(
            "sina_news", f"2026-01-01T1{index}:00:00+08:00", "schedule", 3, 1,
            "2026-01-01T09:00:00+08:00",
        )
    env.store.enqueue("omo", "2026-01-01T12:00:00+08:00", "schedule", 3, 1, "2026-01-01T09:00:00+08:00")

    payload = env.client.get("/api/runs", params={"page_size": 2}).json()
    assert payload["total"] == 4
    assert len(payload["items"]) == 2

    payload = env.client.get("/api/runs", params={"job_id": "omo"}).json()
    assert payload["total"] == 1

    payload = env.client.get("/api/runs", params={"page_size": 9999}).json()
    assert payload["page_size"] == 200

    assert env.client.get("/api/runs", params={"status": "unknown"}).status_code == 422


def test_run_detail_missing_returns_404(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    assert env.client.get("/api/runs/99999").status_code == 404


def test_manual_run_creates_one_record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = make_env(tmp_path)
    monkeypatch.setattr("admin.api.now_iso", lambda: "2026-01-02T09:00:00+08:00")

    first = env.client.post("/api/jobs/sina_news/run")
    second = env.client.post("/api/jobs/sina_news/run")

    assert first.status_code == 200
    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert env.runner.wake_count == 1

    total, rows = env.store.list_runs(job_id="sina_news")
    assert total == 1
    assert rows[0]["trigger_kind"] == "manual"
    assert rows[0]["status"] == "pending"


def test_manual_run_unknown_job_returns_404(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    assert env.client.post("/api/jobs/missing/run").status_code == 404


def test_retry_only_for_failed_records(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    run_id = _pending_run(env.store)
    claimed = env.store.claim_next("2099-01-01T00:00:00+08:00")
    assert claimed is not None
    env.store.mark_failure(claimed["id"], "boom", None, "2026-01-02T00:00:00+08:00")

    response = env.client.post(f"/api/runs/{run_id}/retry")
    assert response.status_code == 200
    assert env.store.get_run(run_id)["status"] == "pending"
    assert env.runner.wake_count == 1

    again = env.client.post(f"/api/runs/{run_id}/retry")
    assert again.status_code == 409


def test_cancel_rejects_running_records(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    pending_id = _pending_run(env.store)
    assert env.client.post(f"/api/runs/{pending_id}/cancel").status_code == 200
    assert env.store.get_run(pending_id)["status"] == "cancelled"

    _pending_run(env.store, job_id="omo", scheduled="2026-01-01T11:00:00+08:00")
    running = env.store.claim_next("2099-01-01T00:00:00+08:00")
    assert running is not None
    assert env.client.post(f"/api/runs/{running['id']}/cancel").status_code == 409


def test_cleanup_validates_days_and_removes_expired(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    run_id = _pending_run(env.store)
    env.store.mark_success(run_id, "2020-01-01T00:00:00+08:00")

    assert env.client.post("/api/runs/cleanup", json={"days": 0}).status_code == 422
    assert env.client.post("/api/runs/cleanup", json={"days": 99999}).status_code == 422

    payload = env.client.post("/api/runs/cleanup", json={"days": 30}).json()
    assert payload["ok"] is True
    assert payload["removed"] == 1


def test_logs_tail_truncates_and_handles_missing_file(tmp_path: Path) -> None:
    env = make_env(tmp_path)

    missing = env.client.get("/api/logs").json()
    assert missing["error"] is not None
    assert missing["count"] == 0

    env.log_path.write_text(
        "\n".join(f"line-{index}" for index in range(5000)) + "\n", encoding="utf-8"
    )
    payload = env.client.get("/api/logs", params={"lines": 99999}).json()
    assert payload["limit"] == 2000
    assert payload["count"] == 2000
    assert payload["truncated"] is True
    assert payload["lines"][-1] == "line-4999"

    small = env.client.get("/api/logs", params={"lines": 10}).json()
    assert small["count"] == 10
    assert small["lines"][0] == "line-4990"


def test_static_fallback_returns_503(tmp_path: Path) -> None:
    env = make_env(tmp_path)
    assert env.client.get("/api/health").status_code == 200
    response = env.client.get("/")
    assert response.status_code == 503
    assert "npm run build" in response.text


def test_static_index_is_served_when_built(tmp_path: Path) -> None:
    env = make_env(tmp_path, with_static=True)
    response = env.client.get("/")
    assert response.status_code == 200
    assert "admin-marker" in response.text
