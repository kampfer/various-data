from app.database import engine
from app.sinaFinanceNews.models import Base as SinaNewsBase
from app.omo.models import Base as OMOBase
from app.investmentLedger.models import Base as LedgerBase


def initAppModels():
    SinaNewsBase.metadata.create_all(bind=engine)
    OMOBase.metadata.create_all(bind=engine)
    LedgerBase.metadata.create_all(bind=engine)
