from app.database import engine
from app.sinaFinanceNews.models import Base as SinaNewsBase
from app.omo.models import Base as OMOBase
from app.investmentLedger.models import Base as LedgerBase
from app.investmentLedger.schema import AccountSchemaManager


def initAppModels() -> None:
    """升级投资台账账户结构后创建各模块尚不存在的表。"""
    AccountSchemaManager(engine).upgradeAccountSchema()
    SinaNewsBase.metadata.create_all(bind=engine)
    OMOBase.metadata.create_all(bind=engine)
    LedgerBase.metadata.create_all(bind=engine)
