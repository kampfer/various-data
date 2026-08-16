"""交易十进制持久化的定向测试。"""
from datetime import date
from decimal import Decimal
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
import pytest
from app.investmentLedger.models import Base, Transaction
from app.investmentLedger.types import DecimalText

@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session):
    Base.metadata.create_all(bind=tempEngine)
    yield dbSession

def testTransactionDecimalsRoundTripWithoutPaddingTruncationOrRounding(ledgerSession: Session):
    transaction = Transaction(product_type='FUND', product_name='基金', product_code='F001', transaction_price=Decimal('1.230000000000000001'), transaction_quantity=Decimal('2.500000000000000003'), direction='BUY', trade_date=date(2024, 1, 1))
    ledgerSession.add(transaction); ledgerSession.commit(); transaction_id = transaction.id; ledgerSession.expunge_all()
    loaded = ledgerSession.get(Transaction, transaction_id)
    assert loaded is not None
    assert str(loaded.transaction_price) == '1.230000000000000001'
    assert str(loaded.transaction_quantity) == '2.500000000000000003'
    raw = ledgerSession.execute(text('SELECT transaction_price, transaction_quantity FROM il_transaction WHERE id = :id'), {'id': transaction.id}).one()
    assert raw == ('1.230000000000000001', '2.500000000000000003')

def testDecimalTextRejectsFloatAndNonfiniteValues():
    column = DecimalText()
    with pytest.raises(TypeError): column.process_bind_param(0.1, None)
    with pytest.raises(TypeError): column.process_bind_param(Decimal('NaN'), None)
