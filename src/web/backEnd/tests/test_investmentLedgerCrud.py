"""交易仓储 canonical 字段映射测试。"""
from datetime import date
from decimal import Decimal
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import pytest
from app.investmentLedger.crud import addTransaction, queryTransactions, removeTransaction
from app.investmentLedger.models import Base, Transaction
from app.investmentLedger.schemas import TransactionCreate, TransactionQuery

@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session):
    Base.metadata.create_all(bind=tempEngine)
    yield dbSession

def create(code: str, quantity: str = '2.125', fee: Decimal | None = None) -> TransactionCreate:
    """构造创建入参；fee 默认 None 以验证服务层归一路径（需求 6.2、6.4）。"""
    return TransactionCreate(product_type='FUND', product_name='成长基金', product_code=code, transaction_price='1.234567890123456789', transaction_quantity=quantity, fee=fee, direction='BUY', trade_date=date(2024, 2, 29))

def testCrudMapsCanonicalPayloadToCanonicalOrmColumnsAndDeletionIsIsolated(ledgerSession: Session):
    first = addTransaction(ledgerSession, create('F001'))
    second = addTransaction(ledgerSession, create('F002'))
    assert first.transaction_price == Decimal('1.234567890123456789')
    assert first.transaction_quantity == Decimal('2.125')
    assert [row.product_code for row in queryTransactions(ledgerSession, TransactionQuery(page_size=100))] == ['F001', 'F002']
    assert removeTransaction(ledgerSession, first.id) is first
    assert ledgerSession.get(Transaction, first.id) is None
    survivor = ledgerSession.get(Transaction, second.id)
    assert survivor is not None and survivor.transaction_quantity == Decimal('2.125')


def testCrudPersistsProvidedFeeAndPreservesDecimalPrecision(ledgerSession: Session):
    """提供 fee 时按原字面量精度落库（需求 6.4）。"""
    row = addTransaction(ledgerSession, create('F010', fee=Decimal('5.00')))
    assert row.fee == Decimal('5.00')
    reloaded = ledgerSession.get(Transaction, row.id)
    assert reloaded is not None and reloaded.fee == Decimal('5.00')


def testCrudPersistsZeroFeeWhenServiceLayerNormalizedToNone(ledgerSession: Session):
    """服务层把 None 归一为 Decimal(0) 后落库；crud 层不负责归一（需求 6.2、6.4）。"""
    row = addTransaction(ledgerSession, create('F011', fee=Decimal('0')))
    assert row.fee == Decimal('0')
