"""运行账本后台管理能力的单元测试。"""

from __future__ import annotations

from contextlib import closing
from pathlib import Path

from scheduler.store import MANUAL_CANCEL_REASON, Store, connect

NOW = "2026-01-02T09:00:00+08:00"
LATER = "2099-01-01T00:00:00+08:00"


def make_store(tmp_path: Path) -> Store:
    return Store(tmp_path / "ledger.db")


def _update(store: Store, run_id: int, **fields: object) -> None:
    assignments = ", ".join(f"{key} = ?" for key in fields)
    with closing(connect(store.path)) as conn:
        conn.execute(
            f"UPDATE job_run SET {assignments} WHERE id = ?",
            (*fields.values(), run_id),
        )
        conn.commit()


def test_list_runs_paginates_and_filters(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.enqueue("sina_news", "2026-01-01T10:00:00+08:00", "schedule", 3, 1, NOW)
    store.enqueue("sina_news", "2026-01-01T11:00:00+08:00", "schedule", 3, 1, NOW)
    store.enqueue("omo", "2026-01-01T12:00:00+08:00", "schedule", 3, 1, NOW)

    total, rows = store.list_runs(page=1, page_size=2)
    assert total == 3
    assert len(rows) == 2
    assert rows[0]["job_id"] == "omo"

    total, rows = store.list_runs(job_id="sina_news")
    assert total == 2
    assert all(row["job_id"] == "sina_news" for row in rows)

    total, _ = store.list_runs(status="pending")
    assert total == 3

    total, _ = store.list_runs(status="success")
    assert total == 0

    total, rows = store.list_runs(page=2, page_size=2)
    assert total == 3
    assert len(rows) == 1


def test_get_run_and_last_run(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.enqueue("sina_news", "2026-01-01T10:00:00+08:00", "schedule", 3, 1, NOW)
    store.enqueue("sina_news", "2026-01-01T11:00:00+08:00", "schedule", 3, 1, NOW)

    _, rows = store.list_runs()
    newest = rows[0]
    assert store.get_run(int(newest["id"])) == newest
    assert store.get_run(999999) is None
    assert store.last_run("sina_news") == newest
    assert store.last_run("missing") is None


def test_overview_stats(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.enqueue("a", "2026-01-01T10:00:00+08:00", "schedule", 3, 1, NOW)
    store.enqueue("b", "2026-01-01T11:00:00+08:00", "schedule", 3, 1, NOW)
    store.enqueue("c", "2026-01-01T12:00:00+08:00", "schedule", 3, 1, NOW)

    first = store.claim_next(LATER)
    assert first is not None
    store.mark_success(first["id"], "2026-01-02T01:00:00+08:00")

    second = store.claim_next(LATER)
    assert second is not None
    store.mark_failure(
        second["id"], "boom", "2026-01-02T03:00:00+08:00", "2026-01-02T02:00:00+08:00"
    )

    stats = store.overview_stats("2026-01-02T00:00:00+08:00")
    assert stats["pending"] == 1
    assert stats["running"] == 0
    assert stats["retrying"] == 1
    assert stats["success_today"] == 1
    assert stats["failed_today"] == 1


def test_enqueue_manual_dedupes_and_keeps_watermark(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.advance_state("omo", "2026-01-01T12:00:00+08:00", NOW)

    created, run_id = store.enqueue_manual("omo", NOW, 3, NOW)
    created_again, same_id = store.enqueue_manual("omo", NOW, 3, NOW)

    assert created is True
    assert created_again is False
    assert run_id == same_id

    run = store.get_run(int(run_id))
    assert run is not None
    assert run["trigger_kind"] == "manual"
    assert run["status"] == "pending"
    assert run["attempt"] == 0
    assert store.get_state("omo") == "2026-01-01T12:00:00+08:00"


def test_requeue_failed_only_grants_one_attempt(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.enqueue("sina_news", "2026-01-01T10:00:00+08:00", "schedule", 3, 1, NOW)

    first = store.claim_next(LATER)
    assert first is not None
    store.mark_failure(first["id"], "boom", None, "2026-01-02T00:00:00+08:00")

    assert store.requeue_failed(first["id"]) is True
    requeued = store.get_run(first["id"])
    assert requeued is not None
    assert requeued["status"] == "pending"
    assert requeued["attempt"] == 2
    assert requeued["error"] is None
    assert requeued["next_retry_at"] is None

    second = store.claim_next(LATER)
    assert second is not None
    assert second["attempt"] == 3
    assert store.requeue_failed(second["id"]) is False


def test_cancel_pending_only_for_active_status(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    store.enqueue("sina_news", "2026-01-01T10:00:00+08:00", "schedule", 3, 1, NOW)
    store.enqueue("omo", "2026-01-01T11:00:00+08:00", "schedule", 3, 1, NOW)

    _, rows = store.list_runs()
    pending_id = int(rows[0]["id"])
    assert store.cancel_pending(pending_id, NOW) is True
    cancelled = store.get_run(pending_id)
    assert cancelled is not None
    assert cancelled["status"] == "cancelled"
    assert cancelled["finished_at"] == NOW
    assert cancelled["error"] == MANUAL_CANCEL_REASON

    running = store.claim_next(LATER)
    assert running is not None
    assert store.cancel_pending(running["id"], NOW) is False
    assert store.get_run(running["id"])["status"] == "running"


def test_cleanup_removes_cancelled_and_protects_unfinished(tmp_path: Path) -> None:
    store = make_store(tmp_path)
    old = "2026-01-01T00:00:00+08:00"
    cutoff = "2026-02-01T00:00:00+08:00"

    cases = [
        ("success", None),
        ("cancelled", None),
        ("failed", None),
        ("failed", "2026-03-01T00:00:00+08:00"),
        ("pending", None),
        ("interrupted", None),
        ("lost", None),
    ]
    for index, (status, next_retry_at) in enumerate(cases):
        store.enqueue(
            f"job_{index}", f"2026-01-01T00:00:{index:02d}+08:00", "schedule", 3, 1, NOW
        )
    _, rows = store.list_runs()
    for row in rows:
        index = int(str(row["job_id"]).split("_")[1])
        status, next_retry_at = cases[index]
        _update(store, int(row["id"]), status=status, next_retry_at=next_retry_at)

    removed = store.cleanup(cutoff, NOW)

    assert removed == 4
    _, remaining = store.list_runs()
    assert {row["job_id"] for row in remaining} == {"job_3", "job_4", "job_5"}
