# Feature: investment-trade-ledger, Property 11: 交易写入语义（创建可检索、删除即消失且互不影响）
# **Validates: Requirements 1.3, 1.5**
"""交易创建、检索与删除语义的 Property 11 属性测试。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.investmentLedger.constants import ProductType, TradeDirection
from app.investmentLedger.crud import (
    addTransaction,
    countTransactions,
    queryTransactions,
    removeTransaction,
)
from app.investmentLedger.models import Base, Transaction
from app.investmentLedger.schemas import TransactionCreate, TransactionQuery


@dataclass(frozen=True)
class TransactionSpec:
    """一笔字段完全合法且产品键唯一的交易输入。"""

    product_type: ProductType
    product_name: str
    product_code: str
    unit_price: Decimal
    quantity: int
    direction: TradeDirection
    trade_date: date

    def toPayload(self) -> TransactionCreate:
        """转换为生产 CRUD 接收的真实创建契约。"""
        return TransactionCreate(**self.__dict__)


PRODUCT_TYPES = tuple(ProductType)
DIRECTIONS = tuple(TradeDirection)
NAME_ALPHABET = tuple("基金股票理财成长价值全球中国计划🚀0123456789")
CODE_ALPHABET = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")

@st.composite
def transactionCases(
    draw: st.DrawFn,
) -> tuple[list[TransactionSpec], frozenset[int]]:
    """生成至少两笔产品代码唯一的合法交易及待删除的任意索引子集。"""
    productCodes = draw(
        st.lists(
            st.text(CODE_ALPHABET, min_size=1, max_size=12),
            min_size=2,
            max_size=8,
            unique=True,
        )
    )
    records = [
        TransactionSpec(
            product_type=draw(st.sampled_from(PRODUCT_TYPES)),
            product_name=draw(st.text(NAME_ALPHABET, min_size=1, max_size=30)),
            product_code=productCode,
            unit_price=Decimal(draw(st.integers(1, 99_999_999))).scaleb(-2),
            quantity=draw(st.integers(min_value=1, max_value=1_000_000)),
            direction=draw(st.sampled_from(DIRECTIONS)),
            trade_date=draw(st.dates(date(2000, 1, 1), date(2100, 12, 31))),
        )
        for productCode in productCodes
    ]
    deletedIndexes = draw(
        st.sets(st.integers(min_value=0, max_value=len(records) - 1))
    )
    return records, frozenset(deletedIndexes)


def submittedSnapshot(spec: TransactionSpec) -> tuple[object, ...]:
    """提取提交字段，作为与持久化结果比较的独立参考值。"""
    return (
        spec.product_type.value,
        spec.product_name,
        spec.product_code,
        spec.unit_price,
        spec.quantity,
        spec.direction.value,
        spec.trade_date,
    )


def persistedSnapshot(transaction: Transaction) -> tuple[object, ...]:
    """提取全部业务字段，忽略仅由数据库生成的主键和创建时间。"""
    return (
        transaction.product_type,
        transaction.product_name,
        transaction.product_code,
        transaction.unit_price,
        transaction.quantity,
        transaction.direction,
        transaction.trade_date,
    )


def completeSnapshot(transaction: Transaction) -> tuple[object, ...]:
    """提取整行字段，用于证明删除不会改变其余交易。"""
    return (transaction.id, *persistedSnapshot(transaction), transaction.created_at)

@given(case=transactionCases())
@settings(max_examples=100, deadline=None)
def testCreatedTransactionsAreRetrievableAndSubsetDeletionIsIsolated(
    case: tuple[list[TransactionSpec], frozenset[int]],
) -> None:
    """创建均可检索；删除任意子集后仅该子集消失，其余整行不变。"""
    records, deletedIndexes = case

    with TemporaryDirectory(prefix="investment-ledger-property-11-") as tempDirectory:
        databasePath = Path(tempDirectory) / "ledger.db"
        engine = create_engine(f"sqlite+pysqlite:///{databasePath.as_posix()}")
        Base.metadata.create_all(bind=engine)

        try:
            with Session(engine) as session:
                created = [addTransaction(session, spec.toPayload()) for spec in records]

                assert countTransactions(session) == len(records)
                assert len(queryTransactions(session, TransactionQuery(page_size=100))) == len(records)

                for spec, transaction in zip(records, created, strict=True):
                    matches = queryTransactions(
                        session,
                        TransactionQuery(
                            scope_product_type=spec.product_type,
                            scope_product_code=spec.product_code,
                            page_size=100,
                        ),
                    )
                    assert len(matches) == 1
                    assert matches[0].id == transaction.id
                    assert persistedSnapshot(matches[0]) == submittedSnapshot(spec)

                beforeById = {
                    transaction.id: completeSnapshot(transaction)
                    for transaction in queryTransactions(
                        session, TransactionQuery(page_size=100)
                    )
                }
                deletedIds = {created[index].id for index in deletedIndexes}

                for transactionId in deletedIds:
                    assert removeTransaction(session, transactionId) is not None

                remaining = queryTransactions(session, TransactionQuery(page_size=100))
                remainingById = {
                    transaction.id: completeSnapshot(transaction)
                    for transaction in remaining
                }
                expectedRemainingIds = set(beforeById) - deletedIds

                assert countTransactions(session) == len(records) - len(deletedIds)
                assert set(remainingById) == expectedRemainingIds
                assert all(transactionId not in remainingById for transactionId in deletedIds)
                assert {
                    transactionId: beforeById[transactionId]
                    for transactionId in expectedRemainingIds
                } == remainingById

                for index in deletedIndexes:
                    deletedSpec = records[index]
                    assert queryTransactions(
                        session,
                        TransactionQuery(
                            scope_product_type=deletedSpec.product_type,
                            scope_product_code=deletedSpec.product_code,
                            page_size=100,
                        ),
                    ) == []
        finally:
            engine.dispose()
