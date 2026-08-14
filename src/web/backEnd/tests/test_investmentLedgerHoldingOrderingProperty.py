# Feature: investment-trade-ledger, Property 5: 持仓条目顺序遵循来源顺序或所选数值排序
# **Validates: Requirements 2.15, 2.19**
"""持仓来源顺序与稳定数值排序的 Property 5 属性测试。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from hypothesis import given, settings, strategies as st

from app.investmentLedger.service import groupByProductKey, sortHoldings


PRODUCT_KEYS = (
    ("WEALTH", "W-1"),
    ("WEALTH", "W-2"),
    ("FUND", "F-1"),
    ("FUND", "F-2"),
    ("STOCK", "S-1"),
    ("STOCK", "S-2"),
)


@dataclass(frozen=True)
class TransactionCase:
    """满足持仓分组最小只读接口的生成交易。"""

    id: int
    product_type: str
    product_name: str
    product_code: str
    trade_date: date


@dataclass(frozen=True)
class MetricCase:
    """满足持仓排序最小只读接口的生成指标。"""

    available: bool
    value: Decimal | None


@dataclass(frozen=True)
class HoldingCase:
    """携带产品键及两个独立可排序指标的生成持仓。"""

    key: tuple[str, str]
    position: MetricCase
    total_profit: MetricCase
metricValues = st.one_of(
    st.none(),
    st.sampled_from(
        (
            Decimal("-100.00"),
            Decimal("-1.00"),
            Decimal("0.00"),
            Decimal("1.00"),
            Decimal("10.00"),
            Decimal("100.00"),
        )
    ),
    st.decimals(
        min_value=Decimal("-1000.00"),
        max_value=Decimal("1000.00"),
        places=2,
        allow_nan=False,
        allow_infinity=False,
    ),
)
rawRows = st.lists(
    st.tuples(
        st.integers(min_value=0, max_value=len(PRODUCT_KEYS) - 1),
        st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31)),
    ),
    min_size=0,
    max_size=60,
)
metricVectors = st.lists(
    metricValues,
    min_size=len(PRODUCT_KEYS),
    max_size=len(PRODUCT_KEYS),
)


def metric(value: Decimal | None) -> MetricCase:
    """把可选精确数值转换为可用或不可用指标。"""
    return MetricCase(available=value is not None, value=value)


@given(
    generatedRows=rawRows,
    tradeDateOrder=st.sampled_from(("asc", "desc")),
    positionValues=metricVectors,
    totalProfitValues=metricVectors,
)
@settings(max_examples=100, deadline=None)
def testProperty5HoldingOrderFollowsSourceOrStableNumericSort(
    generatedRows: list[tuple[int, date]],
    tradeDateOrder: str,
    positionValues: list[Decimal | None],
    totalProfitValues: list[Decimal | None],
) -> None:
    """未排序保持首次分组顺序；数值排序稳定且不可用项恒在末尾。"""
    rows = [
        TransactionCase(
            id=index,
            product_type=PRODUCT_KEYS[keyIndex][0],
            product_name=f"产品-{keyIndex}",
            product_code=PRODUCT_KEYS[keyIndex][1],
            trade_date=tradeDate,
        )
        for index, (keyIndex, tradeDate) in enumerate(generatedRows, start=1)
    ]
    rows.sort(key=lambda row: row.trade_date, reverse=tradeDateOrder == "desc")
    expectedSourceKeys = list(
        dict.fromkeys((row.product_type, row.product_code) for row in rows)
    )
    groups = groupByProductKey(rows)
    holdings = [
        HoldingCase(
            key=group.key,
            position=metric(positionValues[PRODUCT_KEYS.index(group.key)]),
            total_profit=metric(totalProfitValues[PRODUCT_KEYS.index(group.key)]),
        )
        for group in groups
    ]

    assert [group.key for group in groups] == expectedSourceKeys
    assert [item.key for item in sortHoldings(holdings, None, None)] == expectedSourceKeys

    for sortField, attribute in (
        ("position", "position"),
        ("totalProfit", "total_profit"),
    ):
        for sortOrder in ("asc", "desc"):
            actual = sortHoldings(holdings, sortField, sortOrder)
            available = [
                item for item in holdings if getattr(item, attribute).available
            ]
            unavailable = [
                item for item in holdings if not getattr(item, attribute).available
            ]
            expectedAvailable = sorted(
                available,
                key=lambda item: getattr(item, attribute).value,
                reverse=sortOrder == "desc",
            )

            assert actual == expectedAvailable + unavailable
            assert all(
                getattr(item, attribute).available
                for item in actual[: len(available)]
            )
            assert all(
                not getattr(item, attribute).available
                for item in actual[len(available) :]
            )
            for value in {getattr(item, attribute).value for item in available}:
                sourceTies = [
                    item.key
                    for item in available
                    if getattr(item, attribute).value == value
                ]
                actualTies = [
                    item.key
                    for item in actual
                    if getattr(item, attribute).available
                    and getattr(item, attribute).value == value
                ]
                assert actualTies == sourceTies
