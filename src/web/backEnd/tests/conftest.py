"""后端测试的公共夹具。

约束（来自设计文档「Testing Strategy」）：

- 集成测试只允许使用**临时 SQLite 文件**，禁止连接真实库
  ``various_data.db`` 与 ``various_data_dev.db``；
- 单次执行模式运行（``pytest -q``），不使用 watch 模式；
- 属性测试统一 ``@settings(max_examples=100, deadline=None)``（在各测试文件内声明）。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# ``app.*` 形式的导入依赖 backEnd 目录在 sys.path 中（与 uvicorn 的启动目录保持一致）
BACK_END_ROOT = Path(__file__).resolve().parents[1]
if str(BACK_END_ROOT) not in sys.path:
    sys.path.insert(0, str(BACK_END_ROOT))

# 禁止测试触达的真实数据库文件名
FORBIDDEN_DATABASE_FILE_NAMES = ("various_data.db", "various_data_dev.db")


def assertNotRealDatabase(databaseUrl: str) -> None:
    """断言给定连接串不指向任何真实业务库，用于夹具自检。"""
    normalizedUrl = databaseUrl.replace("\\", "/").lower()
    for forbiddenFileName in FORBIDDEN_DATABASE_FILE_NAMES:
        if forbiddenFileName in normalizedUrl:
            raise AssertionError(f"测试禁止连接真实数据库：{forbiddenFileName}")


def enableSqliteForeignKeys(dbapiConnection, _connectionRecord) -> None:
    """为测试 SQLite 连接启用外键约束，保持与生产数据库一致。"""
    cursor = dbapiConnection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
    finally:
        cursor.close()


@pytest.fixture()
def tempDatabasePath(tmp_path: Path) -> Path:
    """返回本次测试专用的临时 SQLite 文件路径（由 pytest 负责目录清理）。"""
    return tmp_path / "investment_ledger_test.db"


@pytest.fixture()
def tempEngine(tempDatabasePath: Path) -> Iterator[Engine]:
    """基于临时 SQLite 文件创建引擎；测试结束后释放连接池。"""
    databaseUrl = f"sqlite:///{tempDatabasePath}"
    assertNotRealDatabase(databaseUrl)
    engine = create_engine(databaseUrl, connect_args={"check_same_thread": False})
    event.listen(engine, "connect", enableSqliteForeignKeys)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture()
def dbSession(tempEngine: Engine) -> Iterator[Session]:
    """返回绑定到临时引擎的会话，语义与生产 ``SessionLocal`` 一致。"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=tempEngine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
