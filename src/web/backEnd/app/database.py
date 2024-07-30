import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.logger import logger

# 只有环境变量PRODUCTION被显式的赋值为'1'时才使用正式数据库
DB_FILE_PATH = os.path.join(
    os.path.dirname(__file__),
    "../../../../",
    "various_data.db" if os.getenv("mode") == "pro" else "various_data_dev.db",
)
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_FILE_PATH}"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger.info(f"使用数据库：{SQLALCHEMY_DATABASE_URL}")
