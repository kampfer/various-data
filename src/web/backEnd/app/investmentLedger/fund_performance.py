"""基金持仓与收益的纯计算模块。

本模块只处理内存中的交易、基金公司行为和估值，不访问数据库或网络。所有金额、
份额和收益率均使用 :class:`~decimal.Decimal`，便于服务层和测试复用。

收益口径：

* 买入成本 = 买入成交金额 + 申购费用；
* 卖出收入 = 卖出成交金额 - 赎回费用；
* 持仓金额 = 经分拆、红利再投资调整后的份额 × 最新单位净值；
* 累计收益 = 卖出收入 + 现金分红 + 持仓金额 - 买入成本；
* 累计收益率 = 累计收益 / 买入成本；
* 年化收益率 = (1 + 累计收益率) ** (365 / 持有天数) - 1。

现金分红不增加份额；红利再投资会按再投资净值增加份额，但不作为新的外部
投入。基金分拆只调整份额，不直接产生收益。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from typing import Iterable

from app.investmentLedger.constants import (
    ANNUALIZATION_DAYS,
    ProductType,
    TradeDirection,
)


ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class FundTrade:
    """收益计算所需的最小交易值对象。

    ``trade_date`` 保留交易发生日，``calculation_date`` 表示该笔交易
    进入收益计算的日期。基金优先使用确认日，其他产品使用交易日。
    """

    trade_date: date
    price: Decimal
    quantity: Decimal
    direction: str
    fee: Decimal = ZERO
    calculation_date: date | None = None

    @property
    def effective_date(self) -> date:
        """返回该笔交易进入收益计算的实际日期。"""
        return self.calculation_date or self.trade_date

    @classmethod
    def fromTransaction(cls, transaction: object) -> "FundTrade":
        """从 ORM 交易对象创建值对象并确定收益计算起算日。"""
        rawDirection = transaction.direction
        direction = (
            rawDirection.value
            if hasattr(rawDirection, "value")
            else str(rawDirection)
        )
        rawProductType = getattr(transaction, "product_type", None)
        productType = (
            rawProductType.value
            if hasattr(rawProductType, "value")
            else str(rawProductType)
        )
        tradeDate = transaction.trade_date
        confirmationDate = getattr(transaction, "confirmation_date", None)
        calculationDate = (
            confirmationDate
            if productType == ProductType.FUND.value and confirmationDate is not None
            else tradeDate
        )
        return cls(
            trade_date=tradeDate,
            price=cls.toDecimal(transaction.transaction_price),
            quantity=cls.toDecimal(transaction.transaction_quantity),
            direction=direction,
            fee=cls.toDecimal(transaction.fee),
            calculation_date=calculationDate,
        )

    @staticmethod
    def toDecimal(value: object | None) -> Decimal:
        """将数据库或上游值转换为有限 Decimal。"""
        if value is None:
            return ZERO
        if isinstance(value, Decimal):
            parsed = value
        else:
            try:
                parsed = Decimal(str(value))
            except (InvalidOperation, ValueError):
                return ZERO
        return parsed if parsed.is_finite() else ZERO


@dataclass(frozen=True, slots=True)
class FundDividend:
    """基金分红事件；reinvest_nav 不为空表示红利再投资。"""

    ex_date: date
    amount_per_share: Decimal
    pay_date: date | None = None
    reinvest_nav: Decimal | None = None


@dataclass(frozen=True, slots=True)
class FundSplit:
    """基金分拆事件；ratio 表示每一份拆分为多少份。"""

    effective_date: date
    ratio: Decimal


@dataclass(frozen=True, slots=True)
class FundPerformance:
    """基金收益计算结果。"""

    shares: Decimal
    position: Decimal | None
    total_profit: Decimal | None
    total_profit_rate: Decimal | None
    annualized_rate: Decimal | None
    buy_cost: Decimal
    sell_proceeds: Decimal
    cash_dividend: Decimal
    holding_start_date: date | None


class FundPerformanceCalculator:
    """按交易时间顺序计算基金持仓和收益的无状态组件。"""

    def calculate(
        self,
        trades: Iterable[FundTrade],
        unitNav: Decimal | None,
        valuationDate: date | None,
        dividends: Iterable[FundDividend] = (),
        splits: Iterable[FundSplit] = (),
    ) -> FundPerformance:
        """计算基金持仓份额、持仓金额、收益、收益率和年化收益率。"""
        orderedTrades = sorted(
            (
                trade
                for trade in trades
                if valuationDate is None or trade.effective_date <= valuationDate
            ),
            key=lambda item: item.effective_date,
        )
        orderedDividends = sorted(
            (
                dividend
                for dividend in dividends
                if valuationDate is None or dividend.ex_date <= valuationDate
            ),
            key=lambda item: item.ex_date,
        )
        orderedSplits = sorted(
            (
                split
                for split in splits
                if valuationDate is None or split.effective_date <= valuationDate
            ),
            key=lambda item: item.effective_date,
        )

        shares = ZERO
        buyCost = ZERO
        sellProceeds = ZERO
        cashDividend = ZERO
        tradeIndex = 0
        dividendIndex = 0
        splitIndex = 0
        holdingStartDate: date | None = None

        while (
            tradeIndex < len(orderedTrades)
            or dividendIndex < len(orderedDividends)
            or splitIndex < len(orderedSplits)
        ):
            nextTradeDate = (
                orderedTrades[tradeIndex].effective_date
                if tradeIndex < len(orderedTrades)
                else None
            )
            nextDividendDate = (
                orderedDividends[dividendIndex].ex_date
                if dividendIndex < len(orderedDividends)
                else None
            )
            nextSplitDate = (
                orderedSplits[splitIndex].effective_date
                if splitIndex < len(orderedSplits)
                else None
            )
            eventDate = min(
                value for value in (nextTradeDate, nextDividendDate, nextSplitDate)
                if value is not None
            )

            # 同日先处理公司行为，再处理交易，避免除息/拆分日新买入
            # 错误获得公司行为权益。
            while (
                splitIndex < len(orderedSplits)
                and orderedSplits[splitIndex].effective_date == eventDate
            ):
                split = orderedSplits[splitIndex]
                if split.ratio > ZERO:
                    shares *= split.ratio
                splitIndex += 1

            while (
                dividendIndex < len(orderedDividends)
                and orderedDividends[dividendIndex].ex_date == eventDate
            ):
                dividend = orderedDividends[dividendIndex]
                if shares > ZERO and dividend.amount_per_share > ZERO:
                    dividendAmount = shares * dividend.amount_per_share
                    if dividend.reinvest_nav is not None and dividend.reinvest_nav > ZERO:
                        shares += dividendAmount / dividend.reinvest_nav
                    else:
                        cashDividend += dividendAmount
                dividendIndex += 1

            while (
                tradeIndex < len(orderedTrades)
                and orderedTrades[tradeIndex].effective_date == eventDate
            ):
                trade = orderedTrades[tradeIndex]
                grossAmount = trade.price * trade.quantity
                if trade.direction == TradeDirection.BUY.value:
                    shares += trade.quantity
                    buyCost += grossAmount + trade.fee
                    if holdingStartDate is None:
                        holdingStartDate = trade.effective_date
                else:
                    shares -= trade.quantity
                    sellProceeds += grossAmount - trade.fee
                tradeIndex += 1

        shares = max(shares, ZERO)
        if unitNav is None or valuationDate is None:
            return FundPerformance(
                shares=shares,
                position=None,
                total_profit=None,
                total_profit_rate=None,
                annualized_rate=None,
                buy_cost=buyCost,
                sell_proceeds=sellProceeds,
                cash_dividend=cashDividend,
                holding_start_date=holdingStartDate,
            )

        position = shares * unitNav
        totalProfit = sellProceeds + cashDividend + position - buyCost
        totalProfitRate = totalProfit / buyCost if buyCost > ZERO else None
        annualizedRate = self._annualizedRate(
            totalProfitRate, holdingStartDate, valuationDate
        )
        return FundPerformance(
            shares=shares,
            position=position,
            total_profit=totalProfit,
            total_profit_rate=totalProfitRate,
            annualized_rate=annualizedRate,
            buy_cost=buyCost,
            sell_proceeds=sellProceeds,
            cash_dividend=cashDividend,
            holding_start_date=holdingStartDate,
        )

    @staticmethod
    def _annualizedRate(
        totalProfitRate: Decimal | None,
        holdingStartDate: date | None,
        valuationDate: date,
    ) -> Decimal | None:
        """按自然日计算年化收益率，处理零成本和亏损边界。"""
        if totalProfitRate is None or holdingStartDate is None:
            return None
        holdingDays = max((valuationDate - holdingStartDate).days, 1)
        base = Decimal(1) + totalProfitRate
        if base < ZERO:
            return None
        if base == ZERO:
            return Decimal("-1")
        with localcontext() as context:
            context.prec += 8
            exponent = Decimal(ANNUALIZATION_DAYS) / Decimal(holdingDays)
            return context.power(base, exponent) - Decimal(1)
