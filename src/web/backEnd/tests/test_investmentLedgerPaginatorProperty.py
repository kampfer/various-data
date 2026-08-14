# Feature: investment-trade-ledger, Property 6: 分页是结果集无重复、无遗漏的有序划分
# **Validates: Requirements 2.11, 2.25, 2.28, 2.29, 2.31**
"""Paginator 的 Property 6 属性测试。"""

from __future__ import annotations

from hypothesis import given, settings, strategies as st

from app.investmentLedger.calculators import Paginator


@st.composite
def paginationCases(draw: st.DrawFn) -> tuple[int, int]:
    """生成偏置空集、短页、整除、非整除及页大小边界的案例。"""
    scenario = draw(st.sampled_from(("empty", "underfilled", "divisible", "remainder")))
    if scenario == "remainder":
        pageSize = draw(st.one_of(st.just(100), st.integers(min_value=2, max_value=100)))
        quotient = draw(st.integers(min_value=0, max_value=20))
        remainder = draw(st.integers(min_value=1, max_value=pageSize - 1))
        return quotient * pageSize + remainder, pageSize

    pageSize = draw(
        st.one_of(st.sampled_from((1, 100)), st.integers(min_value=1, max_value=100))
    )
    if scenario == "empty":
        return 0, pageSize
    if scenario == "underfilled":
        return draw(st.integers(min_value=0, max_value=pageSize - 1)), pageSize
    return pageSize * draw(st.integers(min_value=1, max_value=20)), pageSize


@given(case=paginationCases())
@settings(max_examples=100, deadline=None)
def testPaginationIsOrderedPartitionWithoutDuplicatesOrOmissions(
    case: tuple[int, int],
) -> None:
    """全部有效页应按顺序、无重复且无遗漏地精确还原结果集。"""
    total, pageSize = case
    items = list(range(total))
    expectedPageCount = (total + pageSize - 1) // pageSize if total else 0

    if expectedPageCount == 0:
        pageItems, pageCount = Paginator().slice(items, page=1, pageSize=pageSize)
        assert pageItems == []
        assert pageCount == 0
        assert list(range(1, pageCount + 1)) == []
        return

    pages: list[list[int]] = []
    for page in range(1, expectedPageCount + 1):
        pageItems, pageCount = Paginator().slice(items, page=page, pageSize=pageSize)
        start = (page - 1) * pageSize
        assert pageCount == expectedPageCount
        assert pageItems == items[start : start + pageSize]
        pages.append(pageItems)

    concatenated = [item for pageItems in pages for item in pageItems]
    assert concatenated == items
    assert len(concatenated) == len(set(concatenated))
    assert len(pages[-1]) == (total % pageSize or pageSize)
