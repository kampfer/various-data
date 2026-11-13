"""数据库备份任务：在线快照 + 临时文件 + 原子替换 + 完整性自检。"""

from __future__ import annotations

import logging
import os
import sqlite3

from scheduler.config import Config, now

logger = logging.getLogger("scheduler")


def _integrity_check(path) -> str:
    conn = sqlite3.connect(str(path))
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
    finally:
        conn.close()
    return str(row[0]) if row else "no result"


def run(config: Config) -> None:
    source = config.db_path
    if not source.exists():
        raise FileNotFoundError(f"待备份数据库不存在: {source}")

    backup_dir = config.backup_dir
    backup_dir.mkdir(parents=True, exist_ok=True)

    target = backup_dir / f"{source.stem}_{now().strftime('%Y%m%d')}.db"
    temp = target.with_name(f"{target.name}.tmp")
    if temp.exists():
        temp.unlink()

    try:
        source_conn = sqlite3.connect(str(source), timeout=30)
        temp_conn = sqlite3.connect(str(temp))
        try:
            source_conn.backup(temp_conn)
        finally:
            temp_conn.close()
            source_conn.close()

        result = _integrity_check(temp)
        if result != "ok":
            raise RuntimeError(f"备份文件完整性检查未通过: {result}")

        os.replace(temp, target)
    except BaseException:
        if temp.exists():
            temp.unlink()
        raise

    logger.info("数据库备份完成: 源=%s 目标=%s 完整性检查=%s", source, target, result)
