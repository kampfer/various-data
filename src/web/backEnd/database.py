import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 只有环境变量PRODUCTION被显式的赋值为'1'时才使用正式数据库
SQLALCHEMY_DATABASE_URL = (
    "sqlite:///various_data.db"
    if os.getenv("mode") == "pro"
    else "sqlite:///various_data_dev.db"
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
