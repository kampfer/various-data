"""基金搜索代理服务的定向单元测试（任务 16.4）。

测试目标：覆盖 :class:`FundSearchService` 的三项核心不变量：

1. **故障收敛**（需求 5.6）：第三方任一异常（网络/超时/非 JSON/缺字段）
   均被服务层捕获，返回空列表且不向调用方抛出异常；
2. **基金过滤**（需求 5.7）：仅返回基金条目（``FundBaseInfo`` 非空或
   ``CATEGORYDESC == "基金"``），过滤股票、指数、债券等非基金条目；
3. **标准化**：名称或代码缺失/为空/超长的条目被静默丢弃，不阻断后续条目，
   且最终结果字段长度对齐交易草稿上限，使前端选中后可直接回填。

测试不连接真实第三方接口，也不连接数据库；通过注入 fake client 隔离外网。
Validates: Requirements 5.2, 5.6, 5.7
"""

from __future__ import annotations

from typing import Any

import pytest

from app.investmentLedger.fund_search import FundSearchService
from app.investmentLedger.schemas import FundSearchOut


class _FakeClient:
    """复刻 :class:`EastmoneyFundSearchClient.search` 契约的内存替身。

    只用于驱动 :class:`FundSearchService` 的过滤与标准化逻辑；
    ``behavior`` 决定本次调用是返回固定 ``Datas``、抛异常还是返回非 dict。
    """

    def __init__(self, behavior: str, payload: Any = None) -> None:
        self._behavior = behavior
        self._payload = payload

    def search(self, keyword: str) -> list[dict]:
        """模拟第三方客户端：按构造期设定的行为返回数据或抛异常。"""
        if self._behavior == "raise":
            raise RuntimeError("simulated third-party failure")
        if self._behavior == "return_payload":
            # 直接把构造期 payload 当作第三方原始 dict 返回，
            # 用于覆盖「响应非 JSON 对象」「Datas 非数组」等异常形状。
            raise AssertionError("请使用 return_datas 行为测试正常路径")
        if self._behavior == "return_datas":
            # 正常路径：返回已经是 list[dict] 形态的 Datas 数组，
            # 跳过客户端层对响应形状的二次校验，专注服务层过滤/标准化。
            assert isinstance(self._payload, list)
            return self._payload
        raise AssertionError(f"未知的 fake client 行为：{self._behavior}")


def _fund_entry(name: str, code: str) -> dict:
    """构造一条「基金详情非空」的基金条目（FundBaseInfo 字段非 None）。"""
    return {
        "NAME": name,
        "CODE": code,
        "FundBaseInfo": {"FundCode": code, "ShortName": name},
        "CATEGORYDESC": "基金",
    }


def _stock_entry(name: str, code: str) -> dict:
    """构造一条非基金条目：FundBaseInfo 为 None 且 CATEGORYDESC 为「股票」。"""
    return {
        "NAME": name,
        "CODE": code,
        "FundBaseInfo": None,
        "CATEGORYDESC": "股票",
    }


def _index_entry(name: str, code: str) -> dict:
    """构造一条非基金条目：FundBaseInfo 缺失、CATEGORYDESC 为「指数」。"""
    return {
        "NAME": name,
        "CODE": code,
        "CATEGORYDESC": "指数",
    }


def _fund_entry_by_category_only(name: str, code: str) -> dict:
    """构造一条「仅靠 CATEGORYDESC 命中基金」的条目（FundBaseInfo 缺失）。"""
    return {
        "NAME": name,
        "CODE": code,
        "CATEGORYDESC": "基金",
    }


# ---------------------------------------------------------------------------
# 不变量 1：故障收敛（需求 5.6）
# ---------------------------------------------------------------------------


def testThirdPartyExceptionConvergesToEmptyListAndDoesNotPropagate() -> None:
    """第三方抛任意异常时，服务层返回空列表且不向调用方抛异常。"""
    service = FundSearchService(client=_FakeClient(behavior="raise"))

    result = service.searchFunds("易方达")

    assert result == []


# ---------------------------------------------------------------------------
# 不变量 2：基金过滤（需求 5.7）
# ---------------------------------------------------------------------------


def testOnlyFundEntriesAreReturnedAndNonFundEntriesAreFiltered() -> None:
    """仅返回基金条目；股票、指数等非基金条目被过滤。"""
    entries = [
        _fund_entry("易方达蓝筹精选混合", "005827"),
        _stock_entry("贵州茅台", "600519"),
        _index_entry("沪深300指数", "000300"),
        _fund_entry_by_category_only("华夏沪深300ETF联接A", "000051"),
    ]
    service = FundSearchService(client=_FakeClient(behavior="return_datas", payload=entries))

    result = service.searchFunds("沪深300")

    assert result == [
        FundSearchOut(fund_name="易方达蓝筹精选混合", fund_code="005827"),
        FundSearchOut(fund_name="华夏沪深300ETF联接A", fund_code="000051"),
    ]


def testEmptyDatasReturnsEmptyList() -> None:
    """第三方 Datas 为空数组时返回空列表，不抛异常。"""
    service = FundSearchService(client=_FakeClient(behavior="return_datas", payload=[]))

    result = service.searchFunds("不存在的关键词")

    assert result == []


# ---------------------------------------------------------------------------
# 不变量 3：标准化（名称/代码缺失/为空/超长被丢弃，不阻断后续条目）
# ---------------------------------------------------------------------------


def testEntriesWithMissingOrEmptyOrOverlongFieldsAreDroppedSilently() -> None:
    """名称或代码缺失/为空/超长的条目被静默丢弃，且不影响后续合法条目。"""
    entries = [
        # 名称缺失
        {"CODE": "005827", "FundBaseInfo": {"FundCode": "005827"}, "CATEGORYDESC": "基金"},
        # 代码缺失
        {"NAME": "易方达蓝筹", "FundBaseInfo": {"FundCode": "005827"}, "CATEGORYDESC": "基金"},
        # 名称为纯空白
        {"NAME": "   ", "CODE": "005827", "FundBaseInfo": {"FundCode": "005827"}, "CATEGORYDESC": "基金"},
        # 代码为空字符串
        {"NAME": "易方达蓝筹", "CODE": "", "FundBaseInfo": {"FundCode": "005827"}, "CATEGORYDESC": "基金"},
        # 名称非字符串（数字）：由 _coerceNonEmptyString 收敛为 None 后丢弃
        {"NAME": 123, "CODE": "005827", "FundBaseInfo": {"FundCode": "005827"}, "CATEGORYDESC": "基金"},
        # 合法基金条目（应被保留）
        _fund_entry("易方达蓝筹精选混合", "005827"),
    ]
    service = FundSearchService(client=_FakeClient(behavior="return_datas", payload=entries))

    result = service.searchFunds("易方达")

    # 仅最后一条合法条目被保留，前面 5 条非法条目被静默丢弃
    assert result == [
        FundSearchOut(fund_name="易方达蓝筹精选混合", fund_code="005827"),
    ]


@pytest.mark.parametrize(
    ("name", "code", "kept"),
    [
        # 名称首尾空白会被 strip 后保留
        ("  易方达蓝筹  ", "005827", True),
        # 名称超 100 字符：丢弃（与交易草稿 productName 上限对齐）
        ("易" * 101, "005827", False),
        # 代码超 32 字符：丢弃（与交易草稿 productCode 上限对齐）
        ("易方达蓝筹", "0" * 33, False),
        # 名称恰 100 字符：保留（闭区间上界）
        ("易" * 100, "005827", True),
        # 代码恰 32 字符：保留（闭区间上界）
        ("易方达蓝筹", "0" * 32, True),
    ],
)
def testFieldNameAndCodeLengthBoundariesAreRespected(name: str, code: str, kept: bool) -> None:
    """名称/代码长度边界与交易草稿上限对齐，超长条目被丢弃。"""
    entries = [_fund_entry(name, code)]
    service = FundSearchService(client=_FakeClient(behavior="return_datas", payload=entries))

    result = service.searchFunds("边界")

    if kept:
        # strip 后的期望值
        expected_name = name.strip()
        assert result == [FundSearchOut(fund_name=expected_name, fund_code=code)]
    else:
        assert result == []
