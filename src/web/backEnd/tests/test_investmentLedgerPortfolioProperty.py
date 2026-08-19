# Feature: investment-trade-ledger, Property 9: 组合统计只聚合合格产品并按累计买入金额加权
# **Validates: Requirements 3.10, 3.11, 3.12**
"""组合统计 Property 9 的纯 Decimal 模型对比属性测试。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, localcontext

from hypothesis import example, given, settings, strategies as st

from app.investmentLedger.calculators import (
    Metric,
    PortfolioCalculator,
    ProductPerformance,
)


@dataclass(frozen=True, slots=True)
class ProductCase:
    """组合聚合所需的单个产品统计输入。"""

    has_valuation: bool
    position: Decimal
    total_profit: Decimal
    cumulative_buy_amount: Decimal
    annualized_rate: Decimal | None
    position_quantity: Decimal


@dataclass(frozen=True, slots=True)
class ExpectedPortfolio:
    """独立参考聚合得到的五项组合指标。"""

    total_position: Decimal
    total_position_quantity: Decimal
    total_profit: Decimal
    total_profit_rate: Decimal | None
    total_annualized_rate: Decimal | None


def decimalFromUnits(units: int, scale: int = 100) -> Decimal:
    """以整数单位构造 Decimal，禁止经过 float。"""
    return Decimal(units) / Decimal(scale)


def productCase(
    hasValuation: bool,
    position: str,
    profit: str,
    buyAmount: str,
    annualizedRate: str | None,
    positionQuantity: str = "0",
) -> ProductCase:
    """为显式边界样例构造产品输入。"""
    return ProductCase(
        has_valuation=hasValuation,
        position=Decimal(position),
        total_profit=Decimal(profit),
        cumulative_buy_amount=Decimal(buyAmount),
        annualized_rate=(Decimal(annualizedRate) if annualizedRate is not None else None),
        position_quantity=Decimal(positionQuantity),
    )


@st.composite
def productCases(draw: st.DrawFn) -> tuple[ProductCase, ...]:
    """偏置空集合、无估值、零买入、年化不可用及不同权重。"""
    scenario = draw(
        st.sampled_from(
            (
                "empty",
                "missing_valuation",
                "zero_buy",
                "unavailable_annualized",
                "different_weights",
                "general",
            )
        )
    )
    if scenario == "empty":
        return ()

    size = draw(st.integers(min_value=1, max_value=10))
    amountUnits = st.integers(min_value=-1_000_000, max_value=1_000_000)
    buyUnits = st.integers(min_value=0, max_value=1_000_000)
    rateUnits = st.integers(min_value=-10_000, max_value=50_000)
    quantityUnits = st.integers(min_value=-1_000_000, max_value=1_000_000)
    products = [
        ProductCase(
            has_valuation=draw(st.booleans()),
            position=decimalFromUnits(draw(amountUnits)),
            total_profit=decimalFromUnits(draw(amountUnits)),
            cumulative_buy_amount=decimalFromUnits(draw(buyUnits)),
            annualized_rate=draw(
                st.one_of(st.none(), rateUnits.map(lambda value: decimalFromUnits(value, 10_000)))
            ),
            position_quantity=decimalFromUnits(draw(quantityUnits)),
        )
        for _ in range(size)
    ]

    if scenario == "missing_valuation":
        products[0] = ProductCase(
            False, Decimal("999999"), Decimal("888888"), Decimal("777777"), Decimal("9"), Decimal("9999")
        )
    elif scenario == "zero_buy":
        products[0] = ProductCase(True, Decimal("10"), Decimal("2"), Decimal(0), None, Decimal("3"))
    elif scenario == "unavailable_annualized":
        products[0] = ProductCase(True, Decimal("10"), Decimal("2"), Decimal("100"), None, Decimal("4"))
    elif scenario == "different_weights":
        products = [
            ProductCase(True, Decimal("120"), Decimal("20"), Decimal("100"), Decimal("0.10"), Decimal("10")),
            ProductCase(True, Decimal("260"), Decimal("60"), Decimal("300"), Decimal("0.30"), Decimal("20")),
            *products,
        ]

    return tuple(products)


def toPerformance(case: ProductCase) -> ProductPerformance:
    """把生成案例转换为满足值对象不变量的真实计算器输入。"""
    unavailableValuation = Metric.unavailable("缺少最新估值")
    position = Metric.of(case.position) if case.has_valuation else unavailableValuation
    totalProfit = Metric.of(case.total_profit) if case.has_valuation else unavailableValuation
    totalProfitRate = (
        Metric.of(case.total_profit / case.cumulative_buy_amount)
        if case.has_valuation and case.cumulative_buy_amount > 0
        else Metric.unavailable("收益率不可用")
    )
    annualizedRate = (
        Metric.of(case.annualized_rate)
        if case.has_valuation and case.annualized_rate is not None
        else Metric.unavailable("年化收益率不可用")
    )
    return ProductPerformance(
        position_quantity=Metric.of(case.position_quantity),
        position=position,
        cumulative_buy_amount=case.cumulative_buy_amount,
        cumulative_sell_amount=Decimal(0),
        total_profit=totalProfit,
        total_profit_rate=totalProfitRate,
        annualized_rate=annualizedRate,
    )


def referenceAggregate(cases: tuple[ProductCase, ...]) -> ExpectedPortfolio:
    """以直白循环和纯 Decimal 独立实现需求 3.10-3.12。"""
    with localcontext() as context:
        context.prec = 28
        totalPosition = Decimal(0)
        totalPositionQuantity = Decimal(0)
        totalProfit = Decimal(0)
        totalBuyAmount = Decimal(0)
        annualizedWeightedSum = Decimal(0)
        annualizedBuyAmount = Decimal(0)
        annualizedAvailable = True

        for case in cases:
            if not case.has_valuation:
                continue
            totalPosition += case.position
            totalPositionQuantity += case.position_quantity
            totalProfit += case.total_profit
            totalBuyAmount += case.cumulative_buy_amount
            if case.cumulative_buy_amount > 0:
                annualizedBuyAmount += case.cumulative_buy_amount
                if case.annualized_rate is None:
                    annualizedAvailable = False
                else:
                    annualizedWeightedSum += (
                        case.annualized_rate * case.cumulative_buy_amount
                    )

        totalProfitRate = (
            totalProfit / totalBuyAmount if totalBuyAmount > 0 else None
        )
        totalAnnualizedRate = (
            annualizedWeightedSum / annualizedBuyAmount
            if annualizedBuyAmount > 0 and annualizedAvailable
            else None
        )
        return ExpectedPortfolio(
            totalPosition,
            totalPositionQuantity,
            totalProfit,
            totalProfitRate,
            totalAnnualizedRate,
        )


def assertMetric(metric: Metric, expected: Decimal | None) -> None:
    """断言数值精确相等，或不可用指标没有数值替代。"""
    if expected is None:
        assert metric.available is False
        assert metric.value is None
        assert isinstance(metric.unavailable_reason, str)
        assert metric.unavailable_reason
        return
    assert metric.available is True
    assert metric.value == expected
    assert isinstance(metric.value, Decimal)
    assert metric.unavailable_reason is None


@given(cases=productCases())
@example(cases=())
@example(cases=(productCase(False, "999", "888", "777", "9"),))
@example(cases=(productCase(True, "10", "2", "0", None),))
@example(
    cases=(
        productCase(True, "110", "10", "100", "0.10"),
        productCase(True, "220", "20", "200", None),
    )
)
@example(
    cases=(
        productCase(True, "120", "20", "100", "0.10"),
        productCase(True, "260", "60", "300", "0.30"),
    )
)
@settings(max_examples=100, deadline=None)
def test_property_9_portfolio_aggregates_only_eligible_products_with_buy_weights(
    cases: tuple[ProductCase, ...],
) -> None:
    """生产聚合结果应与独立 Decimal 参考模型逐项一致。"""
    expected = referenceAggregate(cases)
    actual = PortfolioCalculator().aggregate(
        [toPerformance(case) for case in cases]
    )

    assertMetric(actual.total_position, expected.total_position)
    assertMetric(actual.total_position_quantity, expected.total_position_quantity)
    assertMetric(actual.total_profit, expected.total_profit)
    assertMetric(actual.total_profit_rate, expected.total_profit_rate)
    assertMetric(actual.total_annualized_rate, expected.total_annualized_rate)
