from app.database import engine
from app.sinaFinanceNews.models import Base as SinaNewsBase
from app.omo.models import Base as OMOBase
from app.investmentLedger.models import Base as LedgerBase


def initAppModels() -> None:
    """创建各模块尚不存在的表，不负责迁移或删除已有表。

    开发阶段发生不兼容的账本 schema 变更时，必须通过显式管理操作重建
    ``LedgerBase`` 所属表；正常应用启动不得调用 ``drop_all``。
    """
    SinaNewsBase.metadata.create_all(bind=engine)
    OMOBase.metadata.create_all(bind=engine)
    LedgerBase.metadata.create_all(bind=engine)
