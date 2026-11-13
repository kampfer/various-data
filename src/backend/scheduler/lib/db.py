"""业务库建表与写入语句。

表结构与冻结模型（``src/web/backEnd/app/omo/models.py`` 与
``app/sinaFinanceNews/models.py``）保持一致，由 ``scripts/check_task_schema.py``
做基线校验；此后新增字段只在本文件演进。
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS app_state (
    name VARCHAR NOT NULL,
    value VARCHAR NOT NULL,
    PRIMARY KEY (name)
);

CREATE TABLE IF NOT EXISTS omo_repo (
    time VARCHAR NOT NULL,
    period VARCHAR NOT NULL,
    amount VARCHAR NOT NULL,
    rate VARCHAR NOT NULL,
    PRIMARY KEY (time, period)
);

CREATE TABLE IF NOT EXISTS omo_rrp (
    time VARCHAR NOT NULL,
    period VARCHAR NOT NULL,
    amount VARCHAR NOT NULL,
    rate VARCHAR NOT NULL,
    PRIMARY KEY (time, period)
);

CREATE TABLE IF NOT EXISTS omo_mlf (
    time VARCHAR NOT NULL,
    period VARCHAR NOT NULL,
    amount VARCHAR NOT NULL,
    rate VARCHAR NOT NULL,
    PRIMARY KEY (time, period)
);

CREATE TABLE IF NOT EXISTS omo_tmlf (
    time VARCHAR NOT NULL,
    period VARCHAR NOT NULL,
    amount VARCHAR NOT NULL,
    rate VARCHAR NOT NULL,
    PRIMARY KEY (time, period)
);

CREATE TABLE IF NOT EXISTS omo_nb (
    time VARCHAR NOT NULL,
    period VARCHAR NOT NULL,
    amount VARCHAR NOT NULL,
    price VARCHAR NOT NULL,
    PRIMARY KEY (time, period)
);

CREATE TABLE IF NOT EXISTS omo_cb (
    time VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    amount VARCHAR NOT NULL,
    period VARCHAR NOT NULL,
    price VARCHAR,
    rate VARCHAR NOT NULL,
    PRIMARY KEY (time, name)
);

CREATE TABLE IF NOT EXISTS sf_news (
    id INTEGER NOT NULL,
    sina_id INTEGER NOT NULL,
    create_time INTEGER NOT NULL,
    content VARCHAR NOT NULL,
    url VARCHAR NOT NULL,
    significance INTEGER NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS sf_tag (
    id INTEGER NOT NULL,
    name VARCHAR NOT NULL,
    is_sina_tag BOOLEAN NOT NULL,
    sina_id VARCHAR NOT NULL,
    PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS sf_news_tag (
    left_id INTEGER NOT NULL,
    right_id INTEGER NOT NULL,
    PRIMARY KEY (left_id, right_id),
    FOREIGN KEY(left_id) REFERENCES sf_news (id),
    FOREIGN KEY(right_id) REFERENCES sf_tag (id)
);
"""

LATEST_OMO_DOC = "latest_omo_doc"


def connect_business_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """只在表缺失时创建，不修改已存在的表结构。"""

    conn.executescript(SCHEMA_SQL)


# ---------------------------------------------------------------- app_state


def get_app_state(conn: sqlite3.Connection, name: str) -> str | None:
    row = conn.execute("SELECT value FROM app_state WHERE name = ?", (name,)).fetchone()
    return row["value"] if row is not None else None


def set_app_state(conn: sqlite3.Connection, name: str, value: str) -> None:
    conn.execute(
        """
        INSERT INTO app_state (name, value) VALUES (?, ?)
        ON CONFLICT(name) DO UPDATE SET value = excluded.value
        """,
        (name, value),
    )


# --------------------------------------------------------------- 新浪快讯


def get_latest_sina_id(conn: sqlite3.Connection) -> int | None:
    row = conn.execute("SELECT MAX(sina_id) AS max_id FROM sf_news").fetchone()
    return row["max_id"] if row is not None else None


def get_existing_sina_ids(
    conn: sqlite3.Connection, sina_ids: list[int]
) -> set[int]:
    """分批查询已存在的 sina_id，避免 IN 列表超过 SQLite 变量上限。"""

    if not sina_ids:
        return set()

    existing: set[int] = set()
    chunk_size = 500
    for start in range(0, len(sina_ids), chunk_size):
        chunk = sina_ids[start : start + chunk_size]
        placeholders = ",".join("?" for _ in chunk)
        rows = conn.execute(
            f"SELECT sina_id FROM sf_news WHERE sina_id IN ({placeholders})", chunk
        ).fetchall()
        existing.update(int(row["sina_id"]) for row in rows)
    return existing


def insert_news(
    conn: sqlite3.Connection,
    sina_id: int,
    create_time: int,
    content: str,
    url: str,
    significance: int = 0,
) -> int:
    cursor = conn.execute(
        """
        INSERT INTO sf_news (sina_id, create_time, content, url, significance)
        VALUES (?, ?, ?, ?, ?)
        """,
        (sina_id, create_time, content, url, significance),
    )
    return int(cursor.lastrowid)


def get_tag_id_by_name(conn: sqlite3.Connection, name: str) -> int | None:
    row = conn.execute("SELECT id FROM sf_tag WHERE name = ?", (name,)).fetchone()
    return int(row["id"]) if row is not None else None


def insert_tag(
    conn: sqlite3.Connection, name: str, is_sina_tag: bool, sina_id: str
) -> int:
    cursor = conn.execute(
        "INSERT INTO sf_tag (name, is_sina_tag, sina_id) VALUES (?, ?, ?)",
        (name, 1 if is_sina_tag else 0, sina_id),
    )
    return int(cursor.lastrowid)


def link_news_tag(conn: sqlite3.Connection, news_id: int, tag_id: int) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO sf_news_tag (left_id, right_id) VALUES (?, ?)",
        (news_id, tag_id),
    )


# ------------------------------------------------------------------- OMO


def insert_omo_deal(conn: sqlite3.Connection, deal: dict) -> bool:
    """按交易类型写入六类交易表，主键冲突时忽略；返回是否新增。"""

    deal_type = deal["type"]
    time = deal["time"]

    if deal_type == "正回购":
        sql = (
            "INSERT OR IGNORE INTO omo_repo (time, period, amount, rate) "
            "VALUES (?, ?, ?, ?)"
        )
        params = (time, deal["period"], deal["amount"], deal["rate"])
    elif deal_type == "逆回购":
        sql = (
            "INSERT OR IGNORE INTO omo_rrp (time, period, amount, rate) "
            "VALUES (?, ?, ?, ?)"
        )
        params = (time, deal["period"], deal["amount"], deal["rate"])
    elif deal_type == "MLF":
        sql = (
            "INSERT OR IGNORE INTO omo_mlf (time, period, amount, rate) "
            "VALUES (?, ?, ?, ?)"
        )
        params = (time, deal["period"], deal["amount"], deal["rate"])
    elif deal_type == "TMLF":
        sql = (
            "INSERT OR IGNORE INTO omo_tmlf (time, period, amount, rate) "
            "VALUES (?, ?, ?, ?)"
        )
        params = (time, deal["period"], deal["amount"], deal["rate"])
    elif deal_type == "央行票据":
        sql = (
            "INSERT OR IGNORE INTO omo_cb "
            "(time, name, amount, period, price, rate) VALUES (?, ?, ?, ?, ?, ?)"
        )
        params = (
            time,
            deal["name"],
            deal["amount"],
            deal["period"],
            deal.get("price"),
            deal["rate"],
        )
    elif deal_type == "国债":
        sql = (
            "INSERT OR IGNORE INTO omo_nb (time, period, amount, price) "
            "VALUES (?, ?, ?, ?)"
        )
        params = (time, deal["period"], deal["amount"], deal["price"])
    else:
        raise ValueError(f"未知的交易类型: {deal_type}")

    cursor = conn.execute(sql, params)
    return cursor.rowcount > 0
