"""估值摄取仓储的事务、幂等与来源优先级单元测试。"""

from datetime import date, datetime, timezone
from decimal import Decimal
import logging

import pytest
from sqlalchemy import select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.investmentLedger.models import Base, Valuation
from app.investmentLedger.valuation_ingest.protocol import StandardValuation
from app.investmentLedger.valuation_ingest.repository import ValuationRepository


@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session) -> Session:
    """为每个仓储用例创建独立的临时 SQLite 账本表。"""
    Base.metadata.create_all(bind=tempEngine)
    return dbSession


def buildValuation(sourceId: str, price: str) -> StandardValuation:
    """构造已标准化的固定产品、日期估值，用于验证仓储行为。"""
    return StandardValuation(
        product_type="FUND",
        product_code="F-REPOSITORY",
        valuation_date=date(2024, 6, 30),
        unit_price=Decimal(price),
        source_id=sourceId,
        collected_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
        source_reference=f"test://{sourceId}",
    )


def testRepositoryIdempotentlyUpsertsOnlyStandardValuations(
    ledgerSession: Session,
) -> None:
    """同来源重复批次更新同一行；混入非标准对象时整个批次不会部分落库。"""
    repository = ValuationRepository(ledgerSession)
    first = buildValuation("source-a", "12.30")

    assert repository.ingestBatch([first]).accepted == 1
    assert repository.ingestBatch([first]).accepted == 1
    assert len(ledgerSession.scalars(select(Valuation)).all()) == 1

    with pytest.raises(TypeError, match="StandardValuation"):
        repository.ingestBatch([buildValuation("source-b", "9.99"), object()])
    assert len(ledgerSession.scalars(select(Valuation)).all()) == 1


def testRepositoryPreservesExistingSamePriorityValueAndLogsConflict(
    ledgerSession: Session,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """同日平级来源单价冲突时保留先入记录并产生结构化冲突日志。"""
    repository = ValuationRepository(ledgerSession)
    priority = {"winner": 1, "same-tier": 1, "fallback": 2}

    assert repository.ingestBatch([buildValuation("winner", "12.30")], priority).accepted == 1
    with caplog.at_level(logging.WARNING):
        report = repository.ingestBatch([buildValuation("same-tier", "10.00")], priority)
    assert report.accepted == 0
    assert report.skipped == 1
    assert report.conflicts == 1
    assert "valuation_priority_conflict" in caplog.text
    assert "source_id=same-tier" in caplog.text

    assert repository.ingestBatch([buildValuation("fallback", "10.00")], priority).accepted == 1
    rows = ledgerSession.scalars(select(Valuation).order_by(Valuation.source_id)).all()
    assert [(row.source_id, row.unit_price) for row in rows] == [
        ("fallback", Decimal("10.00")),
        ("winner", Decimal("12.30")),
    ]
