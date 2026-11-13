"""运行账本：job_run 与 job_state 的建表、状态流转与清理。"""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_SUCCESS = "success"
STATUS_FAILED = "failed"
STATUS_LOST = "lost"
STATUS_INTERRUPTED = "interrupted"
STATUS_CANCELLED = "cancelled"

ALL_STATUSES = (
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    STATUS_FAILED,
    STATUS_LOST,
    STATUS_INTERRUPTED,
    STATUS_CANCELLED,
)
# 可被消费者领取、可被取消的状态；cancelled 是终态，不再参与执行。
ACTIVE_STATUSES = (STATUS_PENDING, STATUS_INTERRUPTED)

TRIGGER_SCHEDULE = "schedule"
TRIGGER_CATCHUP = "catchup"
TRIGGER_MANUAL = "manual"
TRIGGER_RETRY = "retry"

MANUAL_CANCEL_REASON = "手动取消"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS job_run (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id        TEXT    NOT NULL,
  scheduled_at  TEXT    NOT NULL,
  trigger_kind  TEXT    NOT NULL,
  status        TEXT    NOT NULL,
  attempt       INTEGER NOT NULL DEFAULT 0,
  max_attempts  INTEGER NOT NULL,
  missed_count  INTEGER NOT NULL DEFAULT 1,
  next_retry_at TEXT,
  started_at    TEXT,
  finished_at   TEXT,
  error         TEXT,
  alerted_at    TEXT,
  alert_error   TEXT,
  created_at    TEXT    NOT NULL,
  UNIQUE (job_id, scheduled_at)
);

CREATE INDEX IF NOT EXISTS idx_job_run_status
  ON job_run (status, next_retry_at);

CREATE INDEX IF NOT EXISTS idx_job_run_scheduled
  ON job_run (scheduled_at);

CREATE TABLE IF NOT EXISTS job_state (
  job_id          TEXT PRIMARY KEY,
  last_trigger_at TEXT NOT NULL,
  updated_at      TEXT NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    """打开账本连接；单次操作一个连接，避免跨线程共享。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


class Store:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.init_schema()

    def init_schema(self) -> None:
        with closing(connect(self.path)) as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    # ------------------------------------------------------------------ 入账

    def enqueue(
        self,
        job_id: str,
        scheduled_at: str,
        trigger_kind: str,
        max_attempts: int,
        missed_count: int,
        created_at: str,
    ) -> bool:
        """写入一条待执行记录；同一 job_id + scheduled_at 已存在时忽略。"""

        with closing(connect(self.path)) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO job_run
                  (job_id, scheduled_at, trigger_kind, status, attempt,
                   max_attempts, missed_count, created_at)
                VALUES (?, ?, ?, 'pending', 0, ?, ?, ?)
                """,
                (job_id, scheduled_at, trigger_kind, max_attempts, missed_count, created_at),
            )
            conn.commit()
            return cursor.rowcount > 0

    def insert_lost(
        self,
        job_id: str,
        scheduled_at: str,
        missed_count: int,
        max_attempts: int,
        error: str,
        created_at: str,
    ) -> int | None:
        """写入一条丢失记录；返回新记录 id，已存在时返回 None。"""

        with closing(connect(self.path)) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO job_run
                  (job_id, scheduled_at, trigger_kind, status, attempt,
                   max_attempts, missed_count, error, finished_at, created_at)
                VALUES (?, ?, 'catchup', 'lost', 0, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    scheduled_at,
                    max_attempts,
                    missed_count,
                    error,
                    created_at,
                    created_at,
                ),
            )
            conn.commit()
            return cursor.lastrowid if cursor.rowcount > 0 else None

    # ------------------------------------------------------------------ 取出

    def claim_next(self, at: str) -> dict | None:
        """取出最早到期的一条待执行/待重试记录并置为 running。"""

        with closing(connect(self.path)) as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                """
                SELECT * FROM job_run
                WHERE (status IN ('pending', 'interrupted')
                       AND (next_retry_at IS NULL OR next_retry_at <= ?))
                   OR (status = 'failed'
                       AND next_retry_at IS NOT NULL AND next_retry_at <= ?)
                ORDER BY scheduled_at ASC, id ASC
                LIMIT 1
                """,
                (at, at),
            ).fetchone()
            if row is None:
                conn.commit()
                return None

            conn.execute(
                """
                UPDATE job_run
                SET status = 'running',
                    attempt = attempt + 1,
                    started_at = ?,
                    finished_at = NULL,
                    next_retry_at = NULL
                WHERE id = ?
                """,
                (at, row["id"]),
            )
            conn.commit()
            updated = conn.execute(
                "SELECT * FROM job_run WHERE id = ?", (row["id"],)
            ).fetchone()
            return dict(updated) if updated is not None else None

    # ------------------------------------------------------------------ 终态

    def mark_success(self, run_id: int, at: str) -> None:
        with closing(connect(self.path)) as conn:
            conn.execute(
                """
                UPDATE job_run
                SET status = 'success', finished_at = ?, next_retry_at = NULL
                WHERE id = ?
                """,
                (at, run_id),
            )
            conn.commit()

    def mark_failure(
        self, run_id: int, error: str, next_retry_at: str | None, at: str
    ) -> None:
        with closing(connect(self.path)) as conn:
            conn.execute(
                """
                UPDATE job_run
                SET status = 'failed', error = ?, next_retry_at = ?, finished_at = ?
                WHERE id = ?
                """,
                (error, next_retry_at, at, run_id),
            )
            conn.commit()

    def mark_alerted(self, run_id: int, at: str) -> None:
        with closing(connect(self.path)) as conn:
            conn.execute(
                "UPDATE job_run SET alerted_at = ?, alert_error = NULL WHERE id = ?",
                (at, run_id),
            )
            conn.commit()

    def mark_alert_failed(self, run_id: int, error: str) -> None:
        with closing(connect(self.path)) as conn:
            conn.execute(
                "UPDATE job_run SET alert_error = ? WHERE id = ?", (error, run_id)
            )
            conn.commit()

    # ------------------------------------------------------------------ 水位

    def get_state(self, job_id: str) -> str | None:
        with closing(connect(self.path)) as conn:
            row = conn.execute(
                "SELECT last_trigger_at FROM job_state WHERE job_id = ?", (job_id,)
            ).fetchone()
            return row["last_trigger_at"] if row is not None else None

    def advance_state(self, job_id: str, trigger_at: str, at: str) -> None:
        """水位只前进不后退，避免并发入账把水位写回旧值。"""

        with closing(connect(self.path)) as conn:
            conn.execute(
                """
                INSERT INTO job_state (job_id, last_trigger_at, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                  last_trigger_at = CASE
                    WHEN excluded.last_trigger_at > job_state.last_trigger_at
                    THEN excluded.last_trigger_at
                    ELSE job_state.last_trigger_at
                  END,
                  updated_at = excluded.updated_at
                """,
                (job_id, trigger_at, at),
            )
            conn.commit()

    # ------------------------------------------------------------------ 维护

    def recover_interrupted(self, at: str, error: str) -> tuple[int, int]:
        """把遗留的 running 置为 interrupted 并按剩余次数重新排队。

        返回 (重新排队数, 判为终态失败数)。
        """

        requeued = 0
        terminal = 0
        with closing(connect(self.path)) as conn:
            rows = conn.execute(
                "SELECT id, attempt, max_attempts FROM job_run WHERE status = 'running'"
            ).fetchall()
            for row in rows:
                if row["attempt"] < row["max_attempts"]:
                    conn.execute(
                        """
                        UPDATE job_run
                        SET status = 'interrupted',
                            finished_at = ?,
                            next_retry_at = ?,
                            error = COALESCE(error, ?)
                        WHERE id = ?
                        """,
                        (at, at, error, row["id"]),
                    )
                    requeued += 1
                else:
                    conn.execute(
                        """
                        UPDATE job_run
                        SET status = 'failed',
                            finished_at = ?,
                            next_retry_at = NULL,
                            error = COALESCE(error, ?)
                        WHERE id = ?
                        """,
                        (at, error + "（重试次数已用尽）", row["id"]),
                    )
                    terminal += 1
            conn.commit()
        return requeued, terminal

    def cleanup(self, cutoff: str, at: str) -> int:
        """删除 cutoff 之前的已完成记录，返回删除条数。

        待重试（failed 且 next_retry_at 非空）与 interrupted 记录仍会被消费者处理，
        不在此清理，避免丢掉尚未完成的执行。
        """

        with closing(connect(self.path)) as conn:
            cursor = conn.execute(
                """
                DELETE FROM job_run
                WHERE scheduled_at < ?
                  AND (status IN ('success', 'lost', 'cancelled')
                       OR (status = 'failed' AND next_retry_at IS NULL))
                """,
                (cutoff,),
            )
            conn.commit()
            return cursor.rowcount

    def next_wakeup(self) -> str | None:
        """返回最近一次待重试时间；没有待重试记录时返回 None。"""

        with closing(connect(self.path)) as conn:
            row = conn.execute(
                """
                SELECT MIN(next_retry_at) AS wake FROM job_run
                WHERE status IN ('pending', 'interrupted', 'failed')
                  AND next_retry_at IS NOT NULL
                """
            ).fetchone()
            return row["wake"] if row is not None else None

    def count_pending_retries(self) -> int:
        with closing(connect(self.path)) as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS total FROM job_run
                WHERE status IN ('pending', 'interrupted')
                   OR (status = 'failed' AND next_retry_at IS NOT NULL)
                """
            ).fetchone()
            return int(row["total"]) if row is not None else 0

    # ------------------------------------------------------------ 后台管理查询

    def list_runs(
        self,
        job_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[int, list[dict]]:
        """按筛选条件分页返回运行记录，最新的排在前面。"""

        clauses: list[str] = []
        params: list[object] = []
        if job_id:
            clauses.append("job_id = ?")
            params.append(job_id)
        if status:
            clauses.append("status = ?")
            params.append(status)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        offset = (page - 1) * page_size
        with closing(connect(self.path)) as conn:
            total_row = conn.execute(
                f"SELECT COUNT(*) AS total FROM job_run {where}", params
            ).fetchone()
            rows = conn.execute(
                f"""
                SELECT * FROM job_run {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                (*params, page_size, offset),
            ).fetchall()
        total = int(total_row["total"]) if total_row is not None else 0
        return total, [dict(row) for row in rows]

    def get_run(self, run_id: int) -> dict | None:
        with closing(connect(self.path)) as conn:
            row = conn.execute("SELECT * FROM job_run WHERE id = ?", (run_id,)).fetchone()
            return dict(row) if row is not None else None

    def last_run(self, job_id: str) -> dict | None:
        with closing(connect(self.path)) as conn:
            row = conn.execute(
                "SELECT * FROM job_run WHERE job_id = ? ORDER BY id DESC LIMIT 1",
                (job_id,),
            ).fetchone()
            return dict(row) if row is not None else None

    def overview_stats(self, today_start: str) -> dict:
        """待执行、待重试、运行中与当日成败计数。"""

        with closing(connect(self.path)) as conn:
            row = conn.execute(
                """
                SELECT
                  COALESCE(SUM(CASE WHEN status IN ('pending', 'interrupted')
                                    THEN 1 ELSE 0 END), 0) AS pending,
                  COALESCE(SUM(CASE WHEN status = 'running'
                                    THEN 1 ELSE 0 END), 0) AS running,
                  COALESCE(SUM(CASE WHEN status = 'failed'
                                     AND next_retry_at IS NOT NULL
                                    THEN 1 ELSE 0 END), 0) AS retrying,
                  COALESCE(SUM(CASE WHEN status = 'success'
                                     AND finished_at >= ?
                                    THEN 1 ELSE 0 END), 0) AS success_today,
                  COALESCE(SUM(CASE WHEN status = 'failed'
                                     AND finished_at >= ?
                                    THEN 1 ELSE 0 END), 0) AS failed_today
                FROM job_run
                """,
                (today_start, today_start),
            ).fetchone()
        return {
            "pending": int(row["pending"]),
            "running": int(row["running"]),
            "retrying": int(row["retrying"]),
            "success_today": int(row["success_today"]),
            "failed_today": int(row["failed_today"]),
        }

    # ------------------------------------------------------------ 后台管理操作

    def enqueue_manual(
        self, job_id: str, scheduled_at: str, max_attempts: int, created_at: str
    ) -> tuple[bool, int | None]:
        """写入一条手动触发的待执行记录，返回 (是否新建, 记录 id)。"""

        with closing(connect(self.path)) as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO job_run
                  (job_id, scheduled_at, trigger_kind, status, attempt,
                   max_attempts, missed_count, created_at)
                VALUES (?, ?, ?, 'pending', 0, ?, 1, ?)
                """,
                (job_id, scheduled_at, TRIGGER_MANUAL, max_attempts, created_at),
            )
            conn.commit()
            if cursor.rowcount > 0:
                return True, cursor.lastrowid
            row = conn.execute(
                "SELECT id FROM job_run WHERE job_id = ? AND scheduled_at = ?",
                (job_id, scheduled_at),
            ).fetchone()
            return False, int(row["id"]) if row is not None else None

    def requeue_failed(self, run_id: int) -> bool:
        """把终态失败记录重新置为待执行，并只额外授予一次尝试机会。"""

        with closing(connect(self.path)) as conn:
            cursor = conn.execute(
                """
                UPDATE job_run
                SET status = 'pending',
                    next_retry_at = NULL,
                    finished_at = NULL,
                    error = NULL,
                    attempt = CASE
                      WHEN max_attempts > 1 THEN max_attempts - 1
                      ELSE 0
                    END
                WHERE id = ? AND status = 'failed'
                """,
                (run_id,),
            )
            conn.commit()
            return cursor.rowcount > 0

    def cancel_pending(self, run_id: int, at: str) -> bool:
        """取消待执行或中断待恢复的记录，进入 cancelled 终态。"""

        with closing(connect(self.path)) as conn:
            cursor = conn.execute(
                """
                UPDATE job_run
                SET status = 'cancelled',
                    next_retry_at = NULL,
                    finished_at = ?,
                    error = CASE
                      WHEN error IS NULL OR error = '' THEN ?
                      ELSE error
                    END
                WHERE id = ? AND status IN ('pending', 'interrupted')
                """,
                (at, MANUAL_CANCEL_REASON, run_id),
            )
            conn.commit()
            return cursor.rowcount > 0
