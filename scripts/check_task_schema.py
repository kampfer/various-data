"""对比冻结模型与新 DDL 建出的表结构。

冻结模型：``src/web/backEnd/app/omo/models.py``、
``src/web/backEnd/app/sinaFinanceNews/models.py``
新 DDL：``src/scheduler/lib/db.py``

用法：``uv run python scripts/check_task_schema.py``；差异为空时退出码为 0。
"""

from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT / "src" / "web" / "backEnd"))

from sqlalchemy import create_engine  # noqa: E402

from app.omo import models as omo_models  # noqa: E402
from app.sinaFinanceNews import models as sina_models  # noqa: E402
from scheduler.lib import db as new_db  # noqa: E402


def describe(conn: sqlite3.Connection) -> dict:
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
    ]
    result = {}
    for table in tables:
        columns = [
            tuple(row) for row in conn.execute(f"PRAGMA table_info('{table}')")
        ]
        foreign_keys = sorted(
            tuple(row) for row in conn.execute(f"PRAGMA foreign_key_list('{table}')")
        )
        result[table] = {"columns": columns, "foreign_keys": foreign_keys}
    return result


def build_frozen(path: Path) -> None:
    engine = create_engine(f"sqlite:///{path}")
    try:
        omo_models.Base.metadata.create_all(bind=engine)
        sina_models.Base.metadata.create_all(bind=engine)
    finally:
        engine.dispose()


def build_new(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        new_db.ensure_schema(conn)
        conn.commit()
    finally:
        conn.close()


def main() -> int:
    with tempfile.TemporaryDirectory() as temp_dir:
        frozen_path = Path(temp_dir) / "frozen.db"
        new_path = Path(temp_dir) / "new.db"
        build_frozen(frozen_path)
        build_new(new_path)

        frozen_conn = sqlite3.connect(frozen_path)
        new_conn = sqlite3.connect(new_path)
        try:
            frozen = describe(frozen_conn)
            new = describe(new_conn)
        finally:
            frozen_conn.close()
            new_conn.close()

    problems: list[str] = []
    for table in sorted(set(frozen) | set(new)):
        if table not in frozen:
            problems.append(f"新 DDL 多出表: {table}")
            continue
        if table not in new:
            problems.append(f"新 DDL 缺少表: {table}")
            continue
        for key, label in (("columns", "字段"), ("foreign_keys", "外键")):
            if frozen[table][key] != new[table][key]:
                problems.append(
                    f"表 {table} 的{label}不一致:\n"
                    f"  冻结模型: {frozen[table][key]!r}\n"
                    f"  新 DDL:   {new[table][key]!r}"
                )

    if problems:
        print(f"表结构存在 {len(problems)} 处差异:")
        for problem in problems:
            print(problem)
        return 1

    print(f"表结构一致: 共比对 {len(frozen)} 张表，PRAGMA 差异为空")
    return 0


if __name__ == "__main__":
    sys.exit(main())
