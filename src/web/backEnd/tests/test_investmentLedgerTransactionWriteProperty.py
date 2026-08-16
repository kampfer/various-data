# Feature: investment-trade-ledger, Property 10: 交易写入语义
# **Validates: Requirements 1.3, 1.5**
"""canonical 交易写入、检索和删除隔离属性测试。"""
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.investmentLedger.crud import addTransaction, queryTransactions, removeTransaction
from app.investmentLedger.models import Base
from app.investmentLedger.schemas import TransactionCreate, TransactionQuery

@st.composite
def transactions(draw):
    codes = draw(st.lists(st.text('ABC012', min_size=1, max_size=8), min_size=2, max_size=6, unique=True))
    rows = []
    for code in codes:
        product_type = draw(st.sampled_from(('WEALTH', 'FUND', 'STOCK')))
        quantity = str(draw(st.integers(min_value=1, max_value=10**20))) if product_type == 'STOCK' else f"{draw(st.integers(min_value=1, max_value=10**20))}.{draw(st.integers(min_value=0, max_value=10**12)):012d}"
        rows.append(TransactionCreate(product_type=product_type, product_name='产品', product_code=code, transaction_price=f"{draw(st.integers(min_value=1, max_value=10**20))}.{draw(st.integers(min_value=0, max_value=10**12)):012d}", transaction_quantity=quantity, direction='BUY', trade_date=draw(st.dates(date(2000, 1, 1), date(2100, 1, 1)))))
    return rows, draw(st.sets(st.integers(min_value=0, max_value=len(rows)-1)))

@given(case=transactions())
@settings(max_examples=100, deadline=None)
def testCanonicalTransactionsAreRetrievableAndSubsetDeletionIsIsolated(case):
    rows, deleted_indexes = case
    with TemporaryDirectory() as directory:
        engine = create_engine(f"sqlite+pysqlite:///{Path(directory, 'ledger.db').as_posix()}")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            created = [addTransaction(session, row) for row in rows]
            assert [(row.transaction_price, row.transaction_quantity) for row in queryTransactions(session, TransactionQuery(page_size=100))] == [(row.transaction_price, row.transaction_quantity) for row in rows]
            deleted_ids = {created[index].id for index in deleted_indexes}
            for transaction_id in deleted_ids: assert removeTransaction(session, transaction_id) is not None
            assert {row.id for row in queryTransactions(session, TransactionQuery(page_size=100))} == {row.id for row in created} - deleted_ids
        engine.dispose()
