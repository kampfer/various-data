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

def create(code: str, quantity: str = '2.125') -> TransactionCreate:
    return TransactionCreate(product_type='FUND', product_name='成长基金', product_code=code, transaction_price='1.234567890123456789', transaction_quantity=quantity, direction='BUY', trade_date=date(2024, 2, 29))

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
