# Feature: investment-trade-ledger, Property 3: 查询结果恰好是满足全部已启用谓词的交易集合
# **Validates: Requirements 2.10, 2.16, 2.17, 2.18**
"""交易查询谓词的 Property 3 属性测试。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from hypothesis import given, settings, strategies as st
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.investmentLedger.constants import ProductType, TradeDirection
from app.investmentLedger.crud import queryTransactions
from app.investmentLedger.models import Base, Transaction
from app.investmentLedger.schemas import TransactionQuery


@dataclass(frozen=True)
class TransactionSpec:
    """不依赖 ORM 的交易输入，供参考谓词与数据库写入共同使用。"""

    product_type: str
    product_name: str
    product_code: str
    direction: str
    trade_date: date


NAME_ALPHABET = tuple("基金股票理财成长价值全球中国跨年计划🚀🎉🌟_%0123456789")
CODE_ALPHABET = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_中🚀%")
PRODUCT_TYPES = tuple(item.value for item in ProductType)
DIRECTIONS = tuple(item.value for item in TradeDirection)
SPECIAL_DATES = (
    date(2023, 12, 31),
    date(2024, 1, 1),
    date(2024, 2, 29),
    date(2025, 1, 1),
)
PREDICATES = (
    "product_type",
    "direction",
    "date_range",
    "product_name",
    "product_code",
    "scope",
)

@st.composite
def transactionSpec(draw: st.DrawFn) -> TransactionSpec:
    """生成字段有效且包含中文、emoji、LIKE 通配符字面的交易。"""
    return TransactionSpec(
        product_type=draw(st.sampled_from(PRODUCT_TYPES)),
        product_name=draw(st.text(NAME_ALPHABET, min_size=1, max_size=30)),
        product_code=draw(st.text(CODE_ALPHABET, min_size=1, max_size=12)),
        direction=draw(st.sampled_from(DIRECTIONS)),
        trade_date=draw(
            st.one_of(
                st.sampled_from(SPECIAL_DATES),
                st.dates(min_value=date(2023, 1, 1), max_value=date(2025, 12, 31)),
            )
        ),
    )


@st.composite
def transactionCollections(draw: st.DrawFn) -> list[TransactionSpec]:
    """偏置同代码异类型、中文/emoji 名称、闰日与跨年边界，同时覆盖空集。"""
    extras = draw(st.lists(transactionSpec(), min_size=0, max_size=8))
    scenario = draw(st.integers(min_value=0, max_value=5))
    if scenario == 0:
        return []
    if scenario == 1:
        return extras

    sharedCode = draw(st.text(CODE_ALPHABET, min_size=1, max_size=12))
    biased = [
        TransactionSpec("FUND", "全球🚀成长基金", sharedCode, "BUY", date(2024, 2, 29)),
        TransactionSpec("STOCK", "中国🌟同码股票", sharedCode, "SELL", date(2023, 12, 31)),
        TransactionSpec("WEALTH", "跨年🎉理财", "YEAR-2024", "BUY", date(2024, 1, 1)),
    ]
    return biased + extras


def drawSubstringOrText(
    draw: st.DrawFn, values: list[str], alphabet: tuple[str, ...]
) -> str:
    """优先从现有字段取非空子串，也生成无匹配搜索值。"""
    if values and draw(st.booleans()):
        value = draw(st.sampled_from(values))
        start = draw(st.integers(min_value=0, max_value=len(value) - 1))
        end = draw(st.integers(min_value=start + 1, max_value=len(value)))
        return value[start:end]
    return draw(st.text(alphabet, min_size=1, max_size=12))


@st.composite
def queryCases(
    draw: st.DrawFn,
) -> tuple[list[TransactionSpec], dict[str, object]]:
    """为六类谓词生成任意启用子集及有效查询值。"""
    records = draw(transactionCollections())
    enabled = draw(st.sets(st.sampled_from(PREDICATES)))
    arguments: dict[str, object] = {}

    if "product_type" in enabled:
        arguments["product_type"] = draw(st.sampled_from(PRODUCT_TYPES))
    if "direction" in enabled:
        arguments["direction"] = draw(st.sampled_from(DIRECTIONS))
    if "date_range" in enabled:
        startDate, endDate = draw(
            st.one_of(
                st.just((date(2024, 2, 29), date(2024, 2, 29))),
                st.just((date(2023, 12, 31), date(2024, 1, 1))),
                st.tuples(
                    st.dates(date(2023, 1, 1), date(2025, 12, 31)),
                    st.dates(date(2023, 1, 1), date(2025, 12, 31)),
                ).map(lambda dates: tuple(sorted(dates))),
            )
        )
        arguments.update(start_date=startDate, end_date=endDate)

    if "product_name" in enabled:
        arguments["product_name"] = drawSubstringOrText(
            draw, [record.product_name for record in records], NAME_ALPHABET
        )
    if "product_code" in enabled:
        arguments["product_code"] = drawSubstringOrText(
            draw, [record.product_code for record in records], CODE_ALPHABET
        )
    if "scope" in enabled:
        if records and draw(st.booleans()):
            scopedRecord = draw(st.sampled_from(records))
            scopeCode = scopedRecord.product_code
        else:
            scopeCode = draw(st.text(CODE_ALPHABET, min_size=1, max_size=12))
        arguments.update(
            scope_product_code=scopeCode,
        )

    return records, arguments


def satisfiesAllPredicates(
    record: TransactionSpec, query: TransactionQuery
) -> bool:
    """以直白 Python 条件表达 Property 3 的独立参考谓词。"""
    return all(
        (
            query.product_type is None or record.product_type == query.product_type.value,
            query.direction is None or record.direction == query.direction.value,
            query.start_date is None or record.trade_date >= query.start_date,
            query.end_date is None or record.trade_date <= query.end_date,
            query.product_name is None or query.product_name in record.product_name,
            query.product_code is None or query.product_code in record.product_code,
            query.scope_product_code is None
            or record.product_code == query.scope_product_code,
        )
    )


def toModel(spec: TransactionSpec) -> Transaction:
    """把生成输入转换为真实 SQLAlchemy 交易模型。"""
    return Transaction(
        product_type=spec.product_type,
        product_name=spec.product_name,
        product_code=spec.product_code,
        unit_price=Decimal("1.00"),
        quantity=1,
        direction=spec.direction,
        trade_date=spec.trade_date,
    )


@given(case=queryCases())
@settings(max_examples=100, deadline=None)
def testQueryResultIsExactlyTransactionsSatisfyingEveryEnabledPredicate(
    case: tuple[list[TransactionSpec], dict[str, object]],
) -> None:
    """任意谓词子集的 SQL 查询结果相对参考谓词同时健全且完备。"""
    records, arguments = case
    query = TransactionQuery(**arguments)
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(bind=engine)

    try:
        with Session(engine) as session:
            models = [toModel(record) for record in records]
            session.add_all(models)
            session.flush()

            resultIds = {row.id for row in queryTransactions(session, query)}
            expectedIds = {
                model.id
                for record, model in zip(records, models, strict=True)
                if satisfiesAllPredicates(record, query)
            }

            assert resultIds <= expectedIds  # 健全性：查询不会返回不满足谓词的交易
            assert expectedIds <= resultIds  # 完备性：所有满足谓词的交易都被查询返回
    finally:
        engine.dispose()
