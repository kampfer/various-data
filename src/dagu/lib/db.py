"""SQLite 连接、建表与入库语句。

表结构自本次迁移起由本文件定义，新增字段只在这里添加；Web 端的
`app/*/models.py` 冻结在迁移时的结构，不再承载新的字段定义。
"""

import sqlite3
from pathlib import Path
from typing import Optional, Sequence

from lib.config import DB_FILE_PATH

# 与 app/omo/models.py、app/sinaFinanceNews/models.py 迁移时的结构逐列一致。
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


def connect(dbPath: Optional[Path | str] = None) -> sqlite3.Connection:
    """打开数据库连接，设置 5 秒忙等超时并启用外键约束。"""
    connection = sqlite3.connect(str(dbPath or DB_FILE_PATH), timeout=5)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def ensureSchema(connection: sqlite3.Connection) -> None:
    """创建缺失的表；已存在的表不会被修改。"""
    connection.executescript(SCHEMA_SQL)
    connection.commit()


def upsertOmoRow(
    connection: sqlite3.Connection,
    table: str,
    columns: Sequence[str],
    values: Sequence[str],
    conflictColumns: Sequence[str],
) -> None:
    """按复合主键写入 OMO 记录，冲突则忽略（与旧实现一致）。"""
    columnsSql = ", ".join(columns)
    placeholders = ", ".join("?" for _ in columns)
    conflictSql = ", ".join(conflictColumns)
    connection.execute(
        f"INSERT INTO {table} ({columnsSql}) VALUES ({placeholders}) "
        f"ON CONFLICT ({conflictSql}) DO NOTHING",
        tuple(values),
    )


def upsertAppState(connection: sqlite3.Connection, name: str, value: str) -> None:
    """写入应用状态键值，存在则覆盖。"""
    connection.execute(
        "INSERT INTO app_state (name, value) VALUES (?, ?) "
        "ON CONFLICT (name) DO UPDATE SET value = excluded.value",
        (name, value),
    )


def getAppState(connection: sqlite3.Connection, name: str) -> Optional[str]:
    row = connection.execute(
        "SELECT value FROM app_state WHERE name = ?", (name,)
    ).fetchone()
    return row[0] if row else None


def insertNews(
    connection: sqlite3.Connection,
    sinaId: int,
    createTime: int,
    content: str,
    url: str,
    significance: int = 0,
) -> int:
    cursor = connection.execute(
        "INSERT INTO sf_news (sina_id, create_time, content, url, significance) "
        "VALUES (?, ?, ?, ?, ?)",
        (sinaId, createTime, content, url, significance),
    )
    return int(cursor.lastrowid)


def getOrCreateTag(
    connection: sqlite3.Connection,
    name: str,
    isSinaTag: bool,
    sinaId: str,
) -> int:
    """按名称复用标签，不存在则创建。"""
    row = connection.execute(
        "SELECT id FROM sf_tag WHERE name = ? LIMIT 1", (name,)
    ).fetchone()
    if row:
        return int(row[0])
    cursor = connection.execute(
        "INSERT INTO sf_tag (name, is_sina_tag, sina_id) VALUES (?, ?, ?)",
        (name, 1 if isSinaTag else 0, sinaId),
    )
    return int(cursor.lastrowid)


def linkNewsTag(
    connection: sqlite3.Connection, newsId: int, tagId: int
) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO sf_news_tag (left_id, right_id) VALUES (?, ?)",
        (newsId, tagId),
    )


def getLatestNewsSinaId(connection: sqlite3.Connection) -> Optional[int]:
    """取按发布时间最新的一条快讯的 sina_id，用于增量抓取。"""
    row = connection.execute(
        "SELECT sina_id FROM sf_news ORDER BY create_time DESC LIMIT 1"
    ).fetchone()
    return int(row[0]) if row else None
