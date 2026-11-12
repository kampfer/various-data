"""数据库备份：用 SQLite 在线备份生成一致快照，再原子替换到目标文件。

由 Dagu 以独立进程执行：`python src/dagu/tasks/db_backup.py`。
"""

import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

# 允许以脚本方式直接运行：把 src/dagu 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging

from lib import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("dagu.db_backup")


def job() -> None:
    sourcePath = Path(config.DB_FILE_PATH)
    if not sourcePath.exists():
        raise FileNotFoundError(f"源数据库不存在: {sourcePath}")

    config.BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    dbName, _ = os.path.splitext(sourcePath.name)
    today = date.today().strftime("%Y%m%d")
    backupPath = config.BACKUP_DIR / f"{dbName}_{today}.db"
    tmpPath = backupPath.with_name(backupPath.name + ".tmp")

    if tmpPath.exists():
        tmpPath.unlink()

    # 以只读方式打开源库，避免意外创建空库
    sourceConnection = sqlite3.connect(f"file:{sourcePath}?mode=ro", uri=True)
    try:
        targetConnection = sqlite3.connect(tmpPath)
        try:
            sourceConnection.backup(targetConnection)
            status = targetConnection.execute("PRAGMA integrity_check").fetchone()[0]
            if status != "ok":
                raise RuntimeError(f"备份完整性检查失败: {status}")
        finally:
            targetConnection.close()
    except Exception:
        # 失败时清理半成品，避免被误认为有效备份
        if tmpPath.exists():
            tmpPath.unlink()
        raise
    finally:
        sourceConnection.close()

    os.replace(tmpPath, backupPath)
    logger.info("备份完成: %s", backupPath)


if __name__ == "__main__":
    job()
