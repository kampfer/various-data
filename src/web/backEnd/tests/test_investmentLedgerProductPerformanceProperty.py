# Feature: investment-trade-ledger, Property 8: 产品统计精确计算并显式标记不可用指标
# **Validates: Requirements 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**
"""产品统计 Property 8 的模型对比属性测试。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, localcontext

from hypothesis import given, settings, strategies as st

from app.investmentLedger.calculators import Metric, ProductPerformanceCalculator
from app.investmentLedger.constants import ANNUALIZATION_DAYS, TradeDirection


@dataclass(frozen=True, slots=True)
class TransactionCase:
    """计算器协议所需的最小交易输入。"""

    unit_price: Decimal
    quantity: int
    direction: str
    trade_date: date


@dataclass(frozen=True, slots=True)
class ValuationCase:
    """计算器协议所需的最小估值输入。"""

    unit_price: Decimal
    valuation_date: date


@dataclass(frozen=True, slots=True)
class ProductCase:
    """一组交易及估值日期唯一的估值记录。"""

    txns: tuple[TransactionCase, ...]
    valuations: tuple[ValuationCase, ...]


@dataclass(frozen=True, slots=True)
class ExpectedPerformance:
    """独立参考循环计算出的指标期望值。"""

    position_quantity: Decimal
    cumulative_buy_amount: Decimal
    cumulative_sell_amount: Decimal
    position: Decimal | None
    total_profit: Decimal | None
    total_profit_rate: Decimal | None
    annualized_rate: Decimal | None


def decimalPrice(cents: int) -> Decimal:
    """由整数分构造精确金额，禁止经过 float。"""
    return Decimal(cents) / Decimal(100)


def buildTransactions(
    rawTxns: list[tuple[str, int, int, int]], baseDate: date
) -> tuple[TransactionCase, ...]:
    """把方向、分、数量和日期偏移转换为计算器输入。"""
    return tuple(
        TransactionCase(
            direction=direction,
            unit_price=decimalPrice(cents),
            quantity=quantity,
            trade_date=baseDate + timedelta(days=dayOffset),
        )
        for direction, cents, quantity, dayOffset in rawTxns
    )


@st.composite
def productCases(draw: st.DrawFn) -> ProductCase:
    """偏置关键交易形态、年化边界及缺失输入。"""
    scenario = draw(
        st.sampled_from(
            (
                "all_buy",
                "all_sell",
                "offset",
                "total_loss",
                "one_day",
                "long_holding",
                "missing_valuation",
                "general",
            )
        )
    )
    baseDate = date(2000, 1, 1) + timedelta(
        days=draw(st.integers(min_value=0, max_value=4000))
    )
    cents = st.integers(min_value=1, max_value=100_000)
    quantities = st.integers(min_value=1, max_value=1_000)

    if scenario in ("all_buy", "all_sell"):
        direction = TradeDirection.BUY if scenario == "all_buy" else TradeDirection.SELL
        rawTxns = draw(
            st.lists(
                st.tuples(st.just(direction), cents, quantities, st.integers(0, 4000)),
                min_size=1,
                max_size=8,
            )
        )
        latestOffset = draw(st.integers(min_value=1, max_value=6000))
        latestPrice = decimalPrice(draw(st.integers(min_value=0, max_value=100_000)))
    elif scenario == "offset":
        quantity = draw(quantities)
        rawTxns = [
            (TradeDirection.BUY, draw(cents), quantity, 0),
            (TradeDirection.SELL, draw(cents), quantity, draw(st.integers(0, 4000))),
        ]
        latestOffset = draw(st.integers(min_value=1, max_value=6000))
        latestPrice = decimalPrice(draw(st.integers(min_value=0, max_value=100_000)))
    elif scenario == "total_loss":
        rawTxns = [(TradeDirection.BUY, draw(cents), draw(quantities), 0)]
        latestOffset = draw(st.one_of(st.just(1), st.integers(min_value=2, max_value=6000)))
        latestPrice = Decimal(0)
    elif scenario in ("one_day", "long_holding"):
        rawTxns = [(TradeDirection.BUY, draw(cents), draw(quantities), 0)]
        latestOffset = 1 if scenario == "one_day" else draw(st.integers(3000, 9000))
        latestPrice = decimalPrice(draw(st.integers(min_value=0, max_value=100_000)))
    else:
        rawTxns = draw(
            st.lists(
                st.tuples(
                    st.sampled_from(tuple(TradeDirection)),
                    cents,
                    quantities,
                    st.integers(min_value=0, max_value=4000),
                ),
                min_size=0,
                max_size=8,
            )
        )
        latestOffset = draw(st.integers(min_value=-100, max_value=6000))
        latestPrice = decimalPrice(draw(st.integers(min_value=0, max_value=100_000)))

    txns = buildTransactions(rawTxns, baseDate)
    if scenario == "missing_valuation":
        return ProductCase(txns=txns, valuations=())

    latestDate = baseDate + timedelta(days=latestOffset)
    earlierDayGaps = draw(
        st.lists(st.integers(min_value=1, max_value=1000), max_size=3, unique=True)
    )
    earlierValuations = [
        ValuationCase(
            unit_price=decimalPrice(draw(st.integers(min_value=0, max_value=100_000))),
            valuation_date=latestDate - timedelta(days=gap),
        )
        for gap in earlierDayGaps
    ]
    # 最新记录刻意放在首位，确保测试模型按日期选择而非依赖输入顺序。
    valuations = (ValuationCase(latestPrice, latestDate), *earlierValuations)
    return ProductCase(txns=txns, valuations=valuations)


def referencePerformance(case: ProductCase) -> ExpectedPerformance:
    """以直白循环独立计算全部产品统计及其定义域。"""
    with localcontext() as context:
        context.prec = 28
        buyQuantity = 0
        sellQuantity = 0
        cumulativeBuyAmount = Decimal(0)
        cumulativeSellAmount = Decimal(0)
        firstBuyDate: date | None = None

        for txn in case.txns:
            amount = txn.unit_price * Decimal(txn.quantity)
            if txn.direction == TradeDirection.BUY:
                buyQuantity += txn.quantity
                cumulativeBuyAmount += amount
                if firstBuyDate is None or txn.trade_date < firstBuyDate:
                    firstBuyDate = txn.trade_date
            else:
                sellQuantity += txn.quantity
                cumulativeSellAmount += amount

        positionQuantity = Decimal(buyQuantity - sellQuantity)
        if not case.valuations:
            return ExpectedPerformance(
                positionQuantity,
                cumulativeBuyAmount,
                cumulativeSellAmount,
                None,
                None,
                None,
                None,
            )

        latestValuation = max(case.valuations, key=lambda item: item.valuation_date)
        position = positionQuantity * latestValuation.unit_price
        totalProfit = cumulativeSellAmount + position - cumulativeBuyAmount
        if cumulativeBuyAmount <= 0:
            return ExpectedPerformance(
                positionQuantity,
                cumulativeBuyAmount,
                cumulativeSellAmount,
                position,
                totalProfit,
                None,
                None,
            )

        totalProfitRate = totalProfit / cumulativeBuyAmount
        holdingDays = (
            (latestValuation.valuation_date - firstBuyDate).days
            if firstBuyDate is not None
            else 0
        )
        if holdingDays <= 0 or totalProfitRate < Decimal(-1):
            annualizedRate = None
        elif totalProfitRate == Decimal(-1):
            annualizedRate = Decimal(-1)
        else:
            exponent = Decimal(ANNUALIZATION_DAYS) / Decimal(holdingDays)
            annualizedRate = (
                ((Decimal(1) + totalProfitRate).ln() * exponent).exp() - Decimal(1)
            )

        return ExpectedPerformance(
            positionQuantity,
            cumulativeBuyAmount,
            cumulativeSellAmount,
            position,
            totalProfit,
            totalProfitRate,
            annualizedRate,
        )


def assertMetric(metric: Metric, expected: Decimal | None, *, approximate: bool = False) -> None:
    """断言可用值精确，或不可用值不被数值替代。"""
    if expected is None:
        assert metric.available is False
        assert metric.value is None
        assert isinstance(metric.unavailable_reason, str)
        assert metric.unavailable_reason
        return

    assert metric.available is True
    assert isinstance(metric.value, Decimal)
    assert metric.unavailable_reason is None
    if approximate:
        assert abs(metric.value - expected) <= Decimal("1e-18")
    else:
        assert metric.value == expected


@given(case=productCases())
@settings(max_examples=100, deadline=None)
def test_property_8_product_statistics_are_exact_and_unavailable_explicit(
    case: ProductCase,
) -> None:
    """生产计算结果应与独立 Decimal 参考模型一致。"""
    expected = referencePerformance(case)
    latestValuation = (
        max(case.valuations, key=lambda item: item.valuation_date)
        if case.valuations
        else None
    )

    actual = ProductPerformanceCalculator().calculate(list(case.txns), latestValuation)

    assertMetric(actual.position_quantity, expected.position_quantity)
    assert actual.cumulative_buy_amount == expected.cumulative_buy_amount
    assert actual.cumulative_sell_amount == expected.cumulative_sell_amount
    assertMetric(actual.position, expected.position)
    assertMetric(actual.total_profit, expected.total_profit)
    assertMetric(actual.total_profit_rate, expected.total_profit_rate)
    assertMetric(actual.annualized_rate, expected.annualized_rate, approximate=True)