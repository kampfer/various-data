#!/usr/bin/env python3
"""测试基金收益计算器明细功能"""
from decimal import Decimal
from datetime import date
from app.investmentLedger.fund_performance import (
    FundPerformanceCalculator, 
    FundTrade, 
    FundDividend,
    FundSplit
)

# 创建测试数据
trades = [
    FundTrade(
        trade_date=date(2024, 1, 1),
        price=Decimal("1.00"),
        quantity=Decimal("1000"),
        direction="BUY"
    ),
    FundTrade(
        trade_date=date(2024, 6, 30),
        price=Decimal("1.20"),
        quantity=Decimal("500"),
        direction="SELL"
    )
]

dividends = [
    FundDividend(
        ex_date=date(2024, 3, 1),
        amount_per_share=Decimal("0.10"),
        pay_date=date(2024, 3, 5)
    )
]

splits = [
    FundSplit(
        effective_date=date(2024, 4, 1),
        ratio=Decimal("1.5")
    )
]

# 测试计算器
calculator = FundPerformanceCalculator()

# 测试原始计算方法（向后兼容）
simple_result = calculator.calculate(
    trades=trades,
    unitNav=Decimal("1.50"),
    valuationDate=date(2024, 12, 31),
    dividends=dividends,
    splits=splits
)

print("原始结果（向后兼容）：")
print(f"  份额: {simple_result.shares}")
print(f"  持仓金额: {simple_result.position}")
print(f"  总收益: {simple_result.total_profit}")
print(f"  买入成本: {simple_result.buy_cost}")
print(f"  卖出收入: {simple_result.sell_proceeds}")
print(f"  现金分红: {simple_result.cash_dividend}")

# 测试明细计算方法
details_result = calculator.calculate_with_details(
    trades=trades,
    unitNav=Decimal("1.50"),
    valuationDate=date(2024, 12, 31),
    dividends=dividends,
    splits=splits
)

print("\n明细结果：")
print(f"  份额: {details_result.shares}")
print(f"  持仓金额: {details_result.position}")
print(f"  总收益: {details_result.total_profit}")
print(f"  交易数量: {len(details_result.trades)}")
print(f"  分红数量: {len(details_result.dividends)}")
print(f"  拆分数量: {len(details_result.splits)}")

print("\n第一笔交易明细：")
if details_result.trades:
    trade = details_result.trades[0]
    print(f"  交易日期: {trade.trade_date}")
    print(f"  价格: {trade.price}")
    print(f"  数量: {trade.quantity}")
    print(f"  方向: {trade.direction}")

print("\n第一笔分红明细：")
if details_result.dividends:
    dividend = details_result.dividends[0]
    print(f"  除息日: {dividend.ex_date}")
    print(f"  每份金额: {dividend.amount_per_share}")
    print(f"  发放日: {dividend.pay_date}")

print("\n第一笔拆分明细：")
if details_result.splits:
    split = details_result.splits[0]
    print(f"  生效日: {split.effective_date}")
    print(f"  比率: {split.ratio}")

# 验证向后兼容性
print("\n向后兼容性验证：")
print(f"  份额是否一致: {simple_result.shares == details_result.shares}")
print(f"  持仓金额是否一致: {simple_result.position == details_result.position}")
print(f"  总收益是否一致: {simple_result.total_profit == details_result.total_profit}")

print("\n✅ 测试完成")