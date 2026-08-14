# Feature: investment-trade-ledger, Property 4: 持仓条目是结果集的一个精确划分
# **Validates: Requirements 2.5**
"""持仓产品键分组的 Property 4 属性测试。"""

from __future__ import annotations

from collections import Counter
from datetime import date

from hypothesis import given, settings, strategies as st

from app.investmentLedger.models import Transaction
from app.investmentLedger.service import groupByProductKey


productTypes = st.sampled_from(("WEALTH", "FUND", "STOCK"))
productCodes = st.sampled_from(("A", "B", "001", "SAME"))
productNames = st.text(
    alphabet=st.characters(categories=("L", "N")),
    min_size=1,
    max_size=20,
)
tradeDates = st.dates(min_value=date(2000, 1, 1), max_value=date(2099, 12, 31))
transactionCases = st.lists(
    st.tuples(productTypes, productCodes, productNames, tradeDates),
    min_size=0,
    max_size=60,
)


def buildTransactions(
    cases: list[tuple[str, str, str, date]],
) -> list[Transaction]:
    """将生成值转换为具有唯一记录标识的真实交易模型。"""
    return [
        Transaction(
            id=index,
            product_type=productType,
            product_name=productName,
            product_code=productCode,
            unit_price="1.00",
            quantity=1,
            direction="BUY",
            trade_date=tradeDate,
        )
        for index, (productType, productCode, productName, tradeDate) in enumerate(
            cases, start=1
        )
    ]


@given(cases=transactionCases)
@settings(max_examples=100, deadline=None)
def testProperty4HoldingGroupsAreExactPartition(
    cases: list[tuple[str, str, str, date]],
) -> None:
    """每笔交易恰属一个键一致的组，全部组无遗漏且无重复。"""
    rows = buildTransactions(cases)
    groups = groupByProductKey(rows)
    groupKeys = [group.key for group in groups]
    groupedRows = [row for group in groups for row in group.transactions]

    assert len(groupKeys) == len(set(groupKeys))
    for group in groups:
        assert group.transactions
        assert all(
            (row.product_type, row.product_code) == group.key
            for row in group.transactions
        )

    for sourceRow in rows:
        membershipCount = sum(
            groupedRow is sourceRow for groupedRow in groupedRows
        )
        assert membershipCount == 1

    assert Counter(row.id for row in groupedRows) == Counter(row.id for row in rows)
    assert len(groupedRows) == len(rows)
