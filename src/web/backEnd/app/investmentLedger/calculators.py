"""投资交易账本的纯计算组件。

本模块只处理内存中的领域值，不访问数据库、网络或文件系统。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, localcontext
from typing import Protocol, TypeVar

from app.investmentLedger.constants import ANNUALIZATION_DAYS, TradeDirection
from app.investmentLedger.exceptions import PageOutOfRange


# 分页器支持的任意条目类型；交易记录与持仓条目均可复用。
ItemT = TypeVar("ItemT")


class TransactionLike(Protocol):
    """产品业绩计算所需的最小交易只读接口。"""

    unit_price: Decimal
    quantity: int
    direction: str
    trade_date: date


class ValuationLike(Protocol):
    """产品业绩计算所需的最小估值只读接口。"""

    unit_price: Decimal
    valuation_date: date


@dataclass(frozen=True, slots=True)
class Metric:
    """计算层指标值对象，显式区分数值为零与指标不可用（需求 3.9）。"""

    available: bool
    value: Decimal | None = None
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        """维护可用性、数值与不可用原因三者的一致性。"""
        if self.available and (self.value is None or self.unavailable_reason is not None):
            raise ValueError("可用指标必须有数值且不能有不可用原因")
        if not self.available and (self.value is not None or not self.unavailable_reason):
            raise ValueError("不可用指标必须没有数值且提供中文原因")

    @classmethod
    def of(cls, value: Decimal | int) -> "Metric":
        """构造可用指标；整数先精确转换为 ``Decimal``，不经过浮点数。"""
        decimalValue = value if isinstance(value, Decimal) else Decimal(value)
        return cls(available=True, value=decimalValue)

    @classmethod
    def unavailable(cls, reason: str) -> "Metric":
        """构造不可用指标，并保留可直接展示的中文原因。"""
        return cls(available=False, value=None, unavailable_reason=reason)


@dataclass(frozen=True, slots=True)
class ProductPerformance:
    """单个产品的完整业绩结果，也是组合聚合计算器的输入值对象。"""

    position_quantity: Metric
    position: Metric
    cumulative_buy_amount: Decimal
    cumulative_sell_amount: Decimal
    total_profit: Metric
    total_profit_rate: Metric
    annualized_rate: Metric

    @property
    def has_latest_valuation(self) -> bool:
        """是否具有最新估值；组合统计据此筛选可聚合产品。"""
        return self.position.available

    @property
    def market_value(self) -> Metric:
        """持仓市值的语义别名；对外持仓列使用 ``position`` 字段。"""
        return self.position


@dataclass(frozen=True, slots=True)
class PortfolioStatistics:
    """投资组合的聚合统计结果（需求 3.10-3.12）。"""

    total_position: Metric
    total_profit: Metric
    total_profit_rate: Metric
    total_annualized_rate: Metric


class PortfolioCalculator:
    """仅以已计算的产品业绩聚合投资组合统计，无 I/O（需求 3.10-3.12）。"""

    def aggregate(
        self, performances: list[ProductPerformance]
    ) -> PortfolioStatistics:
        """按最新估值资格及累计买入金额权重聚合产品业绩。

        总持仓与总收益只包含具有最新估值的产品，合格集合为空时二者仍为
        可用的零值。总收益率仅在这些产品的累计买入金额总和大于零时可用。
        总年化收益率使用其中累计买入金额大于零的产品集合；该集合必须非空，
        且每个产品的年化收益率都可用。任何前提不成立时均显式返回不可用指标，
        不以零替代。

        :param performances: 全部产品的业绩结果，输入集合不会被修改。
        :return: 四项组合级统计指标。
        """
        with localcontext() as context:
            context.prec = 28
            valuedPerformances = [
                performance
                for performance in performances
                if performance.has_latest_valuation
            ]

            totalPositionValue = sum(
                (
                    performance.position.value
                    for performance in valuedPerformances
                    if performance.position.value is not None
                ),
                Decimal(0),
            )
            totalProfitValue = sum(
                (
                    performance.total_profit.value
                    for performance in valuedPerformances
                    if performance.total_profit.value is not None
                ),
                Decimal(0),
            )
            totalBuyAmount = sum(
                (
                    performance.cumulative_buy_amount
                    for performance in valuedPerformances
                ),
                Decimal(0),
            )

            if totalBuyAmount > 0:
                totalProfitRate = Metric.of(totalProfitValue / totalBuyAmount)
            else:
                totalProfitRate = Metric.unavailable("累计买入金额总和为 0")

            annualizedPerformances = [
                performance
                for performance in valuedPerformances
                if performance.cumulative_buy_amount > 0
            ]
            if not annualizedPerformances:
                totalAnnualizedRate = Metric.unavailable(
                    "没有累计买入金额大于 0 的已估值产品"
                )
            elif any(
                not performance.annualized_rate.available
                for performance in annualizedPerformances
            ):
                totalAnnualizedRate = Metric.unavailable(
                    "存在年化收益率不可用的产品"
                )
            else:
                annualizedWeightedSum = sum(
                    (
                        performance.annualized_rate.value
                        * performance.cumulative_buy_amount
                        for performance in annualizedPerformances
                        if performance.annualized_rate.value is not None
                    ),
                    Decimal(0),
                )
                annualizedBuyAmount = sum(
                    (
                        performance.cumulative_buy_amount
                        for performance in annualizedPerformances
                    ),
                    Decimal(0),
                )
                totalAnnualizedRate = Metric.of(
                    annualizedWeightedSum / annualizedBuyAmount
                )

            return PortfolioStatistics(
                total_position=Metric.of(totalPositionValue),
                total_profit=Metric.of(totalProfitValue),
                total_profit_rate=totalProfitRate,
                total_annualized_rate=totalAnnualizedRate,
            )


class ProductPerformanceCalculator:
    """单个产品的无状态业绩计算器（需求 3.4-3.9）。"""

    def calculate(
        self,
        txns: list[TransactionLike],
        latestValuation: ValuationLike | None,
    ) -> ProductPerformance:
        """以纯 ``Decimal`` 运算计算持仓、收益及年化收益率。

        交易顺序不影响金额与持仓汇总；首次买入日期仅用于计算持有天数。
        任一指标定义域不成立时只将该指标标记为不可用，不阻断其它指标。
        """
        with localcontext() as context:
            context.prec = 28
            buyQuantity = 0
            sellQuantity = 0
            cumulativeBuyAmount = Decimal(0)
            cumulativeSellAmount = Decimal(0)
            firstBuyDate: date | None = None

            for txn in txns:
                amount = txn.unit_price * Decimal(txn.quantity)
                if txn.direction == TradeDirection.BUY:
                    buyQuantity += txn.quantity
                    cumulativeBuyAmount += amount
                    if firstBuyDate is None or txn.trade_date < firstBuyDate:
                        firstBuyDate = txn.trade_date
                elif txn.direction == TradeDirection.SELL:
                    sellQuantity += txn.quantity
                    cumulativeSellAmount += amount
                else:
                    raise ValueError("交易方向必须为 BUY 或 SELL")

            positionQuantity = Metric.of(buyQuantity - sellQuantity)

            if latestValuation is None:
                missingValuation = Metric.unavailable("缺少最新估值")
                return ProductPerformance(
                    position_quantity=positionQuantity,
                    position=missingValuation,
                    cumulative_buy_amount=cumulativeBuyAmount,
                    cumulative_sell_amount=cumulativeSellAmount,
                    total_profit=missingValuation,
                    total_profit_rate=missingValuation,
                    annualized_rate=missingValuation,
                )

            marketValue = positionQuantity.value * latestValuation.unit_price
            totalProfitValue = (
                cumulativeSellAmount + marketValue - cumulativeBuyAmount
            )
            position = Metric.of(marketValue)
            totalProfit = Metric.of(totalProfitValue)

            if cumulativeBuyAmount <= 0:
                noBuyAmount = Metric.unavailable("累计买入金额为 0")
                return ProductPerformance(
                    position_quantity=positionQuantity,
                    position=position,
                    cumulative_buy_amount=cumulativeBuyAmount,
                    cumulative_sell_amount=cumulativeSellAmount,
                    total_profit=totalProfit,
                    total_profit_rate=noBuyAmount,
                    annualized_rate=noBuyAmount,
                )

            profitRateValue = totalProfitValue / cumulativeBuyAmount
            profitRate = Metric.of(profitRateValue)

            if firstBuyDate is None:
                # 正常领域数据中累计买入金额大于零必然存在首次买入；此分支保护
                # 计算器面对不完整输入时仍遵守“单项不可用、不影响其它指标”。
                annualizedRate = Metric.unavailable("缺少首次买入交易日期")
            else:
                holdingDays = (latestValuation.valuation_date - firstBuyDate).days
                if holdingDays <= 0:
                    annualizedRate = Metric.unavailable("持有天数不足")
                elif profitRateValue < Decimal(-1):
                    annualizedRate = Metric.unavailable("收益率小于 -1，无法计算年化收益率")
                elif profitRateValue == Decimal(-1):
                    annualizedRate = Metric.of(Decimal(-1))
                else:
                    exponent = Decimal(ANNUALIZATION_DAYS) / Decimal(holdingDays)
                    base = Decimal(1) + profitRateValue
                    annualizedValue = (base.ln() * exponent).exp() - Decimal(1)
                    annualizedRate = Metric.of(annualizedValue)

            return ProductPerformance(
                position_quantity=positionQuantity,
                position=position,
                cumulative_buy_amount=cumulativeBuyAmount,
                cumulative_sell_amount=cumulativeSellAmount,
                total_profit=totalProfit,
                total_profit_rate=profitRate,
                annualized_rate=annualizedRate,
            )


class Paginator:
    """与条目类型无关的分页切片器（需求 2.11、2.24-2.31）。"""

    def slice(
        self, items: list[ItemT], page: int, pageSize: int
    ) -> tuple[list[ItemT], int]:
        """返回请求页的有序切片及总页数。

        ``page`` 从 1 开始，``pageSize`` 是已由服务边界校验的 1 至 100
        整数。空结果的总页数为 0，且不存在需要判定为有效的页码；页码
        小于 1，或非空结果请求超过最后一页时抛出 :class:`PageOutOfRange`。

        :param items: 已完成筛选、搜索和排序的有序结果集。
        :param page: 已校验为大于或等于 1 的请求页码。
        :param pageSize: 已校验为 1 至 100 的页大小。
        :return: ``(当前页切片, 总页数)``。
        :raises PageOutOfRange: 非空结果中请求页码大于总页数。
        """
        total = len(items)
        pageCount = (total + pageSize - 1) // pageSize if total else 0

        isIntegerPage = isinstance(page, int) and not isinstance(page, bool)
        if not isIntegerPage or page < 1 or (pageCount > 0 and page > pageCount):
            raise PageOutOfRange(page=page, pageCount=pageCount)

        start = (page - 1) * pageSize
        return items[start : start + pageSize], pageCount
