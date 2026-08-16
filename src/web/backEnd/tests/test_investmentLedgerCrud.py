"""投资交易账本数据访问层的示例单元测试（任务 5.1、5.3）。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterator

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.investmentLedger.crud import (
    addTransaction,
    countTransactions,
    getLatestValuations,
    queryTransactions,
    removeTransaction,
)
from app.investmentLedger.models import Base, Transaction, Valuation
from app.investmentLedger.schemas import TransactionCreate, TransactionQuery
from app.investmentLedger.valuation_ingest.protocol import StandardValuation
from app.investmentLedger.valuation_ingest.repository import ValuationRepository


@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session) -> Iterator[Session]:
    """在临时 SQLite 中创建账本表，不触达真实业务数据库。"""
    Base.metadata.create_all(bind=tempEngine)
    yield dbSession


def buildTransaction(**overrides: object) -> Transaction:
    """构造交易记录；调用方仅覆盖当前用例关心的字段。"""
    values: dict[str, object] = {
        "product_type": "FUND",
        "product_name": "成长基金",
        "product_code": "F-001",
        "unit_price": Decimal("1.25"),
        "quantity": 10,
        "direction": "BUY",
        "trade_date": date(2024, 2, 29),
    }
    values.update(overrides)
    return Transaction(**values)


def persist(session: Session, *transactions: Transaction) -> None:
    """批量写入并提交测试交易。"""
    session.add_all(transactions)
    session.commit()


def testCountTransactionsReturnsZeroAndFullTableCount(
    ledgerSession: Session,
) -> None:
    """计数不受查询条件影响，空表为 0，写入后为全表行数（需求 2.2、2.3）。"""
    assert countTransactions(ledgerSession) == 0
    persist(ledgerSession, buildTransaction(), buildTransaction(product_code="S-002"))
    assert countTransactions(ledgerSession) == 2

def testQueryCombinesFiltersSearchesAndProductScopeWithAnd(
    ledgerSession: Session,
) -> None:
    """全部筛选、两个包含搜索与产品范围均下推并按逻辑与生效。"""
    target = buildTransaction(product_name="全球🚀成长基金", product_code="F-001")
    persist(
        ledgerSession,
        target,
        buildTransaction(product_type="STOCK", product_name="全球🚀成长基金"),
        buildTransaction(direction="SELL", product_name="全球🚀成长基金"),
        buildTransaction(trade_date=date(2024, 2, 28), product_name="全球🚀成长基金"),
        buildTransaction(trade_date=date(2024, 3, 2), product_name="全球🚀成长基金"),
        buildTransaction(product_name="价值基金"),
        buildTransaction(product_code="F-002", product_name="全球🚀成长基金"),
    )

    query = TransactionQuery(
        product_type="FUND",
        direction="BUY",
        start_date=date(2024, 2, 29),
        end_date=date(2024, 3, 1),
        product_name="🚀成长",
        product_code="-00",
        scope_product_type="FUND",
        scope_product_code="F-001",
    )

    assert queryTransactions(ledgerSession, query) == [target]


def testSearchTreatsLikeWildcardsAsLiteralCharacters(
    ledgerSession: Session,
) -> None:
    """LIKE 包含搜索会转义用户值中的百分号与下划线，保持“包含”语义。"""
    literalMatch = buildTransaction(product_name="收益_100%计划", product_code="A%_1")
    wildcardOnlyMatch = buildTransaction(product_name="收益X1000计划", product_code="AXY1")
    persist(ledgerSession, literalMatch, wildcardOnlyMatch)

    query = TransactionQuery(product_name="_100%", product_code="%_1")

    assert queryTransactions(ledgerSession, query) == [literalMatch]

@pytest.mark.parametrize(
    ("order", "expectedDates"),
    [
        ("asc", [date(2024, 1, 1), date(2024, 2, 1), date(2024, 2, 1)]),
        ("desc", [date(2024, 2, 1), date(2024, 2, 1), date(2024, 1, 1)]),
    ],
)
def testQueryOrdersByTradeDateAndUsesIdAsTieBreaker(
    ledgerSession: Session,
    order: str,
    expectedDates: list[date],
) -> None:
    """启用日期排序时按日期排列，同日记录维持 id 升序。"""
    first = buildTransaction(trade_date=date(2024, 2, 1), product_code="FIRST")
    second = buildTransaction(trade_date=date(2024, 1, 1), product_code="SECOND")
    third = buildTransaction(trade_date=date(2024, 2, 1), product_code="THIRD")
    persist(ledgerSession, first, second, third)

    rows = queryTransactions(ledgerSession, TransactionQuery(trade_date_order=order))

    assert [row.trade_date for row in rows] == expectedDates
    sameDateIds = [row.id for row in rows if row.trade_date == date(2024, 2, 1)]
    assert sameDateIds == [first.id, third.id]


def testQueryDefaultsToStableAscendingIdOrder(ledgerSession: Session) -> None:
    """未指定日期排序时忽略日期先后，稳定地按 id 升序返回全部交易。"""
    first = buildTransaction(trade_date=date(2024, 3, 1), product_code="FIRST")
    second = buildTransaction(trade_date=date(2024, 1, 1), product_code="SECOND")
    third = buildTransaction(trade_date=date(2024, 2, 1), product_code="THIRD")
    persist(ledgerSession, first, second, third)

    rows = queryTransactions(ledgerSession, TransactionQuery())

    assert [row.id for row in rows] == [first.id, second.id, third.id]


def buildTransactionPayload(**overrides: object) -> TransactionCreate:
    """构造已通过契约校验的交易写入参数。"""
    values: dict[str, object] = {
        "product_type": "FUND",
        "product_name": "成长基金",
        "product_code": "F-001",
        "unit_price": "1.25",
        "quantity": 10,
        "direction": "BUY",
        "trade_date": date(2024, 2, 29),
    }
    values.update(overrides)
    return TransactionCreate(**values)


def testAddAndRemoveTransactionPersistExpectedRows(
    ledgerSession: Session,
) -> None:
    """新增交易可检索，删除目标行不影响其他行，不存在主键返回 None。"""
    first = addTransaction(ledgerSession, buildTransactionPayload())
    second = addTransaction(
        ledgerSession,
        buildTransactionPayload(product_code="F-002", product_name="价值基金"),
    )

    assert first.id is not None
    assert ledgerSession.get(Transaction, first.id) is first
    assert removeTransaction(ledgerSession, 999999) is None
    assert removeTransaction(ledgerSession, first.id) is first
    assert ledgerSession.get(Transaction, first.id) is None
    assert ledgerSession.get(Transaction, second.id) is not None


def testAddTransactionRollsBackWhenCommitFails(
    ledgerSession: Session,
) -> None:
    """真实约束异常会回滚整个写事务，会话随后仍可继续使用。"""
    duplicateValues = {
        "product_type": "FUND",
        "product_code": "DUPLICATE",
        "valuation_date": date(2024, 3, 1),
        "unit_price": Decimal("1.00"),
    }
    ledgerSession.add_all(
        [Valuation(**duplicateValues), Valuation(**duplicateValues)]
    )

    with pytest.raises(IntegrityError):
        addTransaction(ledgerSession, buildTransactionPayload())

    assert countTransactions(ledgerSession) == 0
    recovered = addTransaction(ledgerSession, buildTransactionPayload())
    assert recovered.id is not None


def testGetLatestValuationsReturnsMaximumDatePerRequestedProduct(
    ledgerSession: Session,
) -> None:
    """每个请求产品仅返回最大估值日期记录，缺失产品和未请求产品均不返回。"""
    persist(
        ledgerSession,
        Valuation(
            product_type="FUND",
            product_code="F-001",
            valuation_date=date(2024, 1, 1),
            unit_price=Decimal("1.10"),
        ),
        Valuation(
            product_type="FUND",
            product_code="F-001",
            valuation_date=date(2024, 3, 1),
            unit_price=Decimal("1.30"),
        ),
        Valuation(
            product_type="STOCK",
            product_code="S-001",
            valuation_date=date(2024, 2, 1),
            unit_price=Decimal("12.00"),
        ),
        Valuation(
            product_type="WEALTH",
            product_code="W-UNREQUESTED",
            valuation_date=date(2024, 4, 1),
            unit_price=Decimal("2.00"),
        ),
    )

    valuations = getLatestValuations(
        ledgerSession,
        [("FUND", "F-001"), ("STOCK", "S-001"), ("FUND", "MISSING")],
    )

    assert set(valuations) == {("FUND", "F-001"), ("STOCK", "S-001")}
    assert valuations[("FUND", "F-001")].valuation_date == date(2024, 3, 1)
    assert valuations[("FUND", "F-001")].unit_price == Decimal("1.30")
    assert getLatestValuations(ledgerSession, []) == {}


def testGetLatestValuationsUsesSourcePriorityOnlyAmongLatestDateCandidates(
    ledgerSession: Session,
) -> None:
    """先按最大日期取候选，再只在同日按来源优先级选择，且不写入数据。"""
    persist(
        ledgerSession,
        Valuation(
            product_type="FUND",
            product_code="F-PRIORITY",
            valuation_date=date(2024, 3, 1),
            unit_price=Decimal("1.10"),
            source_id="preferred",
        ),
        Valuation(
            product_type="FUND",
            product_code="F-PRIORITY",
            valuation_date=date(2024, 3, 1),
            unit_price=Decimal("1.20"),
            source_id="fallback",
        ),
        Valuation(
            product_type="FUND",
            product_code="F-PRIORITY",
            valuation_date=date(2024, 4, 1),
            unit_price=Decimal("1.30"),
            source_id="preferred",
        ),
        Valuation(
            product_type="FUND",
            product_code="F-PRIORITY",
            valuation_date=date(2024, 4, 1),
            unit_price=Decimal("1.40"),
            source_id="unconfigured",
        ),
        Valuation(
            product_type="STOCK",
            product_code="S-LATEST",
            valuation_date=date(2024, 3, 1),
            unit_price=Decimal("12.00"),
            source_id="preferred",
        ),
        Valuation(
            product_type="STOCK",
            product_code="S-LATEST",
            valuation_date=date(2024, 4, 1),
            unit_price=Decimal("13.00"),
            source_id="unconfigured",
        ),
    )

    valuations = getLatestValuations(
        ledgerSession,
        [("FUND", "F-PRIORITY"), ("STOCK", "S-LATEST")],
        {"preferred": 1, "fallback": 2},
    )

    selectedPriority = valuations[("FUND", "F-PRIORITY")]
    assert selectedPriority.valuation_date == date(2024, 4, 1)
    assert selectedPriority.source_id == "preferred"
    assert selectedPriority.unit_price == Decimal("1.30")
    selectedLatest = valuations[("STOCK", "S-LATEST")]
    assert selectedLatest.valuation_date == date(2024, 4, 1)
    assert selectedLatest.source_id == "unconfigured"
    assert len(ledgerSession.scalars(select(Valuation)).all()) == 6


def testGetLatestValuationsSelectsUnconfiguredSourcesDeterministically(
    ledgerSession: Session,
) -> None:
    """同日来源均未配置时按 source_id 决胜，不依赖插入或数据库返回顺序。"""
    persist(
        ledgerSession,
        Valuation(
            product_type="STOCK",
            product_code="S-UNCONFIGURED",
            valuation_date=date(2024, 3, 1),
            unit_price=Decimal("12.00"),
            source_id="zeta",
        ),
        Valuation(
            product_type="STOCK",
            product_code="S-UNCONFIGURED",
            valuation_date=date(2024, 3, 1),
            unit_price=Decimal("11.00"),
            source_id="alpha",
        ),
    )

    valuations = getLatestValuations(
        ledgerSession,
        [("STOCK", "S-UNCONFIGURED"), ("STOCK", "MISSING")],
        {},
    )

    selected = valuations[("STOCK", "S-UNCONFIGURED")]
    assert selected.source_id == "alpha"
    assert selected.unit_price == Decimal("11.00")
    assert ("STOCK", "MISSING") not in valuations
