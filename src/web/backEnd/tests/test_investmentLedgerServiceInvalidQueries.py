"""服务层无效查询输入的示例测试（任务 6.7）。

测试通过 ``model_construct`` 模拟契约层之外的服务调用方，使无效值到达
服务边界；正常 HTTP 入口的 Pydantic schemas 仍保持原有严格校验。
所有数据库断言均使用 pytest 提供的临时 SQLite 文件。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.investmentLedger.exceptions import (
    InvalidDateRange,
    InvalidPageSize,
    InvalidSearchValue,
    PageOutOfRange,
)
from app.investmentLedger.models import Base, Transaction, Valuation
from app.investmentLedger.schemas import HoldingQuery, TransactionQuery
from app.investmentLedger.service import HoldingService, TransactionService


SERVICE_BOUNDARIES = (
    (TransactionService, TransactionQuery, "listTransactions"),
    (HoldingService, HoldingQuery, "listHoldings"),
)


@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session) -> Iterator[Session]:
    """创建账本表并写入一条基线交易，确保总页数为 1。"""
    Base.metadata.create_all(bind=tempEngine)
    dbSession.add(
        Transaction(
            product_type="FUND",
            product_name="成长基金",
            product_code="F-001",
            unit_price=Decimal("1.25"),
            quantity=10,
            direction="BUY",
            trade_date=date(2024, 2, 29),
        )
    )
    dbSession.commit()
    yield dbSession


def databaseSnapshot(session: Session) -> tuple[tuple[tuple[Any, ...], ...], ...]:
    """读取两张账本表的完整列快照，用于证明异常路径没有写副作用。"""
    snapshots: list[tuple[tuple[Any, ...], ...]] = []
    for model in (Transaction, Valuation):
        rows = session.scalars(select(model).order_by(model.id)).all()
        snapshots.append(
            tuple(
                tuple(getattr(row, column.name) for column in model.__table__.columns)
                for row in rows
            )
        )
    return tuple(snapshots)


def invokeBoundary(
    session: Session,
    serviceType: type[Any],
    queryType: type[Any],
    methodName: str,
    **invalidValues: object,
) -> None:
    """绕过 schema 构造校验，直接从指定服务查询边界调用无效输入。"""
    query = queryType.model_construct(**invalidValues)
    method = getattr(serviceType(session), methodName)
    method(query)


def assertNoWriteSideEffects(
    session: Session, before: tuple[tuple[tuple[Any, ...], ...], ...]
) -> None:
    """断言持久化内容和会话写集合在异常前后均未变化。"""
    assert databaseSnapshot(session) == before
    assert not session.new
    assert not session.dirty
    assert not session.deleted


@pytest.mark.parametrize(("serviceType", "queryType", "methodName"), SERVICE_BOUNDARIES)
@pytest.mark.parametrize("invalidPage", [0, 2])
def testOutOfRangePageRaisesWithValidRangeAndDoesNotWrite(
    ledgerSession: Session,
    serviceType: type[Any],
    queryType: type[Any],
    methodName: str,
    invalidPage: int,
) -> None:
    """页码小于 1 或大于总页数时报告 1 至 1，且数据库不变（需求 2.30）。"""
    before = databaseSnapshot(ledgerSession)

    with pytest.raises(PageOutOfRange) as caught:
        invokeBoundary(
            ledgerSession,
            serviceType,
            queryType,
            methodName,
            page=invalidPage,
            page_size=1,
        )

    assert "有效页码为 1 至 1" in caught.value.msg
    assertNoWriteSideEffects(ledgerSession, before)


INVALID_QUERY_CASES = (
    ({"page_size": 0}, InvalidPageSize, "pageSize"),
    ({"page_size": 101}, InvalidPageSize, "pageSize"),
    ({"start_date": date(2024, 1, 1), "end_date": None}, InvalidDateRange, "startDate"),
    ({"start_date": None, "end_date": date(2024, 1, 31)}, InvalidDateRange, "startDate"),
    (
        {"start_date": date(2024, 2, 1), "end_date": date(2024, 1, 31)},
        InvalidDateRange,
        "startDate",
    ),
    (
        {"start_date": "2024-02-30", "end_date": "2024-03-01"},
        InvalidDateRange,
        "startDate",
    ),
    ({"product_name": ""}, InvalidSearchValue, "productName"),
    ({"product_name": "名" * 101}, InvalidSearchValue, "productName"),
    ({"product_code": "码" * 101}, InvalidSearchValue, "productCode"),
)


@pytest.mark.parametrize(("serviceType", "queryType", "methodName"), SERVICE_BOUNDARIES)
@pytest.mark.parametrize(("invalidValues", "expectedError", "expectedField"), INVALID_QUERY_CASES)
def testInvalidStaticQueryInputRaisesDomainErrorAndDoesNotWrite(
    ledgerSession: Session,
    serviceType: type[Any],
    queryType: type[Any],
    methodName: str,
    invalidValues: dict[str, object],
    expectedError: type[Exception],
    expectedField: str,
) -> None:
    """页大小、日期及搜索无效时转为对应领域异常且无写库副作用。"""
    before = databaseSnapshot(ledgerSession)

    with pytest.raises(expectedError) as caught:
        invokeBoundary(
            ledgerSession,
            serviceType,
            queryType,
            methodName,
            **invalidValues,
        )

    fieldErrors = caught.value.fieldErrors
    assert [item.field for item in fieldErrors] == [expectedField]
    assertNoWriteSideEffects(ledgerSession, before)
