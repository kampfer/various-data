from app.database import engine
from app.sinaFinanceNews.models import Base as SinaNewsBase
from app.omo.models import Base as OMOBase


def initAppModels() -> None:
    """创建各模块尚不存在的表。"""
    SinaNewsBase.metadata.create_all(bind=engine)
    OMOBase.metadata.create_all(bind=engine)
