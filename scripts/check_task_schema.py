"""一次性基线校验：对比既有 SQLAlchemy 模型与 src/dagu/lib/db.py 建出的表结构。

只用于证明迁移时两者兼容，不是长期同步义务。
用法（仓库根）：pipenv run python scripts/check_task_schema.py
"""

import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src" / "web" / "backEnd"))
sys.path.insert(0, str(REPO_ROOT / "src" / "dagu"))

from sqlalchemy import create_engine  # noqa: E402

from app.omo.models import Base as OMOBase  # noqa: E402
from app.sinaFinanceNews.models import Base as SinaBase  # noqa: E402
from lib import db as taskDb  # noqa: E402

TABLES = [
    "app_state",
    "omo_repo",
    "omo_rrp",
    "omo_mlf",
    "omo_tmlf",
    "omo_nb",
    "omo_cb",
    "sf_news",
    "sf_tag",
    "sf_news_tag",
]


def describe(connection: sqlite3.Connection, table: str):
    """返回与顺序无关的表结构描述：列信息 + 外键。"""
    columns = [
        (row[1], (row[2] or "").upper(), row[3], row[5])
        for row in connection.execute(f"PRAGMA table_info({table})")
    ]
    foreignKeys = [
        (row[2], row[3], row[4])
        for row in connection.execute(f"PRAGMA foreign_key_list({table})")
    ]
    return sorted(columns), sorted(foreignKeys)


def main() -> int:
    differences = []
    with tempfile.TemporaryDirectory() as tmpDir:
        modelDbPath = Path(tmpDir) / "models.db"
        taskDbPath = Path(tmpDir) / "tasks.db"

        engine = create_engine(f"sqlite:///{modelDbPath}")
        OMOBase.metadata.create_all(bind=engine)
        SinaBase.metadata.create_all(bind=engine)
        engine.dispose()

        taskConnection = sqlite3.connect(taskDbPath)
        try:
            taskDb.ensureSchema(taskConnection)
        finally:
            taskConnection.close()

        modelConnection = sqlite3.connect(modelDbPath)
        taskConnection = sqlite3.connect(taskDbPath)
        try:
            for table in TABLES:
                modelShape = describe(modelConnection, table)
                taskShape = describe(taskConnection, table)
                if modelShape != taskShape:
                    differences.append((table, modelShape, taskShape))
        finally:
            modelConnection.close()
            taskConnection.close()

    if not differences:
        print(f"OK: {len(TABLES)} 张表的列与外键完全一致")
        return 0

    for table, modelShape, taskShape in differences:
        print(f"MISMATCH: {table}")
        print(f"  模型: {modelShape}")
        print(f"  新库: {taskShape}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
