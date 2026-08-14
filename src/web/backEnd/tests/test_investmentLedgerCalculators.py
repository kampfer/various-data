"""投资交易账本纯计算层的示例单元测试（任务 3.1）。"""

from __future__ import annotations

import pytest

from app.investmentLedger.calculators import Paginator
from app.investmentLedger.exceptions import PageOutOfRange


class TestPaginator:
    """``Paginator`` 的页数计算、切片与越界行为。"""

    def testEmptyItemsHaveNoBrowsablePage(self) -> None:
        """空结果返回空切片和 0 页，不把任何页码标记为有效（需求 2.31）。"""
        pageItems, pageCount = Paginator().slice([], page=1, pageSize=10)

        assert pageItems == []
        assert pageCount == 0

    def testExactMultipleReturnsRequestedFullPage(self) -> None:
        """结果数整除页大小时，总页数和当前页切片均准确（需求 2.28）。"""
        items = list(range(20))

        pageItems, pageCount = Paginator().slice(items, page=2, pageSize=10)

        assert pageItems == list(range(10, 20))
        assert pageCount == 2
        assert items == list(range(20))

    def testLastPageContainsAllRemainingItems(self) -> None:
        """最后一页不足页大小时仍返回全部剩余条目（需求 2.29）。"""
        pageItems, pageCount = Paginator().slice(
            list(range(23)), page=3, pageSize=10
        )

        assert pageItems == [20, 21, 22]
        assert pageCount == 3

    def testPageAboveLastPageRaisesRangeError(self) -> None:
        """非空结果请求超过总页数时报告有效范围（需求 2.30）。"""
        with pytest.raises(PageOutOfRange) as caught:
            Paginator().slice(list(range(11)), page=3, pageSize=10)

        assert caught.value.page == 3
        assert caught.value.pageCount == 2
        assert "有效页码为 1 至 2" in caught.value.msg


from datetime import date
from decimal import Decimal

from app.investmentLedger.calculators import ProductPerformanceCalculator
from app.investmentLedger.models import Transaction, Valuation


class TestProductPerformanceCalculator:
    """产品业绩公式与各指标独立不可用语义的示例测试。"""

    @staticmethod
    def transaction(
        direction: str,
        unitPrice: str,
        quantity: int,
        tradeDate: date,
    ) -> Transaction:
        """构造无需持久化的真实交易领域实体。"""
        return Transaction(
            product_type="FUND",
            product_name="示例基金",
            product_code="F001",
            unit_price=Decimal(unitPrice),
            quantity=quantity,
            direction=direction,
            trade_date=tradeDate,
        )

    @staticmethod
    def valuation(unitPrice: str, valuationDate: date) -> Valuation:
        """构造无需持久化的真实估值领域实体。"""
        return Valuation(
            product_type="FUND",
            product_code="F001",
            unit_price=Decimal(unitPrice),
            valuation_date=valuationDate,
        )

    def testCalculatesAllAvailableMetricsWithDecimal(self) -> None:
        """买卖并存且估值有效时精确计算全部指标（需求 3.4-3.8）。"""
        txns = [
            self.transaction("BUY", "10.00", 100, date(2023, 1, 1)),
            self.transaction("SELL", "12.00", 40, date(2023, 6, 1)),
        ]

        result = ProductPerformanceCalculator().calculate(
            txns, self.valuation("15.00", date(2024, 1, 1))
        )

        assert result.position_quantity.value == Decimal("60")
        assert result.position.value == Decimal("900.00")
        assert result.cumulative_buy_amount == Decimal("1000.00")
        assert result.cumulative_sell_amount == Decimal("480.00")
        assert result.total_profit.value == Decimal("380.00")
        assert result.total_profit_rate.value == Decimal("0.38")
        assert result.annualized_rate.value == Decimal("0.38")
        assert all(
            metric.available
            for metric in (
                result.position_quantity,
                result.position,
                result.total_profit,
                result.total_profit_rate,
                result.annualized_rate,
            )
        )

    def testMissingValuationOnlyDisablesDependentMetrics(self) -> None:
        """缺少估值时仍输出持仓数量与累计金额（需求 3.9）。"""
        result = ProductPerformanceCalculator().calculate(
            [self.transaction("BUY", "10.00", 2, date(2024, 1, 1))], None
        )

        assert result.position_quantity.value == Decimal("2")
        assert result.cumulative_buy_amount == Decimal("20.00")
        for metric in (
            result.position,
            result.total_profit,
            result.total_profit_rate,
            result.annualized_rate,
        ):
            assert metric.available is False
            assert metric.value is None
            assert metric.unavailable_reason == "缺少最新估值"

    def testZeroBuyAmountDoesNotDisablePositionAndProfit(self) -> None:
        """累计买入为零时仅收益率与年化不可用（需求 3.7、3.9）。"""
        result = ProductPerformanceCalculator().calculate(
            [self.transaction("SELL", "8.00", 3, date(2024, 1, 2))],
            self.valuation("10.00", date(2024, 2, 1)),
        )

        assert result.position.value == Decimal("-30.00")
        assert result.total_profit.value == Decimal("-6.00")
        assert result.total_profit_rate.value is None
        assert result.total_profit_rate.unavailable_reason == "累计买入金额为 0"
        assert result.annualized_rate.value is None
        assert result.annualized_rate.unavailable_reason == "累计买入金额为 0"

    def testAnnualizedRateHandlesBoundaryDomainsIndependently(self) -> None:
        """零持有天数不可用，而收益率 -1 按定义得到年化 -1（需求 3.8、3.9）。"""
        calculator = ProductPerformanceCalculator()
        purchase = self.transaction("BUY", "10.00", 1, date(2024, 1, 1))

        noHoldingDays = calculator.calculate(
            [purchase], self.valuation("12.00", date(2024, 1, 1))
        )
        totalLoss = calculator.calculate(
            [purchase], self.valuation("0", date(2024, 1, 2))
        )

        assert noHoldingDays.total_profit_rate.value == Decimal("0.2")
        assert noHoldingDays.annualized_rate.value is None
        assert noHoldingDays.annualized_rate.unavailable_reason == "持有天数不足"
        assert totalLoss.total_profit_rate.value == Decimal("-1")
        assert totalLoss.annualized_rate.value == Decimal("-1")


from app.investmentLedger.calculators import (
    Metric as CalculationMetric,
    PortfolioCalculator,
    ProductPerformance,
)


class TestPortfolioCalculator:
    """投资组合只聚合已估值产品并保持指标不可用语义。"""

    @staticmethod
    def performance(
        position: str | None,
        profit: str | None,
        buyAmount: str,
        annualizedRate: str | None,
    ) -> ProductPerformance:
        """构造满足产品业绩值对象不变量的组合聚合输入。"""
        unavailableValuation = CalculationMetric.unavailable("缺少最新估值")
        hasValuation = position is not None and profit is not None
        return ProductPerformance(
            position_quantity=CalculationMetric.of(0),
            position=(
                CalculationMetric.of(Decimal(position))
                if position is not None
                else unavailableValuation
            ),
            cumulative_buy_amount=Decimal(buyAmount),
            cumulative_sell_amount=Decimal(0),
            total_profit=(
                CalculationMetric.of(Decimal(profit))
                if profit is not None
                else unavailableValuation
            ),
            total_profit_rate=(
                CalculationMetric.of(0)
                if hasValuation and Decimal(buyAmount) > 0
                else CalculationMetric.unavailable("收益率不可用")
            ),
            annualized_rate=(
                CalculationMetric.of(Decimal(annualizedRate))
                if annualizedRate is not None
                else CalculationMetric.unavailable("年化收益率不可用")
            ),
        )

    def testAggregatesOnlyValuedProductsAndWeightsAnnualizedRate(self) -> None:
        """无估值产品完全排除，年化按正累计买入金额加权（需求 3.10-3.12）。"""
        performances = [
            self.performance("120", "20", "100", "0.10"),
            self.performance("260", "60", "300", "0.30"),
            self.performance(None, None, "1000", "0.90"),
            self.performance("5", "5", "0", None),
        ]

        result = PortfolioCalculator().aggregate(performances)

        assert result.total_position.value == Decimal("385")
        assert result.total_profit.value == Decimal("85")
        assert result.total_profit_rate.value == Decimal("0.2125")
        assert result.total_annualized_rate.value == Decimal("0.25")
        assert result.total_position.available is True
        assert result.total_profit.available is True

    def testEmptyPortfolioKeepsSumsAvailableAndRatesUnavailable(self) -> None:
        """无已估值产品时求和为零，但两个比率不以零冒充（需求 3.10-3.12）。"""
        result = PortfolioCalculator().aggregate(
            [self.performance(None, None, "100", "0.20")]
        )

        assert result.total_position.value == Decimal(0)
        assert result.total_profit.value == Decimal(0)
        assert result.total_profit_rate.available is False
        assert result.total_profit_rate.value is None
        assert result.total_profit_rate.unavailable_reason == "累计买入金额总和为 0"
        assert result.total_annualized_rate.available is False
        assert result.total_annualized_rate.value is None

    def testUnavailableAnnualizedRateDisablesOnlyPortfolioAnnualizedRate(self) -> None:
        """正买入产品缺少年化时仅总年化不可用，其它组合指标继续输出。"""
        result = PortfolioCalculator().aggregate(
            [
                self.performance("110", "10", "100", "0.10"),
                self.performance("220", "20", "200", None),
            ]
        )

        assert result.total_position.value == Decimal("330")
        assert result.total_profit.value == Decimal("30")
        assert result.total_profit_rate.value == Decimal("0.1")
        assert result.total_annualized_rate.available is False
        assert result.total_annualized_rate.value is None
        assert result.total_annualized_rate.unavailable_reason == "存在年化收益率不可用的产品"
