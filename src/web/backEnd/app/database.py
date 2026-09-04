import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.logger import logger

# 只有环境变量PRODUCTION被显式的赋值为'1'时才使用正式数据库
DB_FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../../../",
    "various_data.db" if os.getenv("mode") == "pro" else "various_data_dev.db",
)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"


def enableSqliteForeignKeys(dbapiConnection, _connectionRecord) -> None:
    """为每个 SQLite 连接启用外键约束，确保删除策略在运行时生效。"""
    cursor = dbapiConnection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys = ON")
    finally:
        cursor.close()


engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=os.getenv("mode") != "pro",
)
event.listen(engine, "connect", enableSqliteForeignKeys)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger.info(
    "database_initialized mode=%s database_file=%s",
    os.getenv("mode", "dev"),
    os.path.basename(DB_FILE_PATH),
)
