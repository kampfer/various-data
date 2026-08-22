"""基金历史净值代理服务的定向单元测试。

测试目标：覆盖 :class:`FundQuoteService` 的核心不变量：

1. **故障收敛**（沿用需求 5.6 的原则）：akshare 任一异常（网络/超时/缺列/
   非 DataFrame）均被服务层捕获，「历史净值」收敛为空列表，且不向调用方
   抛出异常；
2. **历史净值日期过滤与升序**：提供 ``tradeDate`` 时只返回同日记录，
   不提供时返回全部历史，并按日期升序排列；
3. **标准化**：缺失/为空/超长的字段被静默丢弃，不阻断后续条目；
   历史净值中非法日期、无法解析的净值被静默丢弃。

测试不连接真实 akshare 接口，也不连接数据库；通过注入 fake client 隔离
akshare/pandas 依赖，使测试可在不安装 akshare 的环境下运行。
"""

from __future__ import annotations

from datetime import date

from app.investmentLedger.fund_quote import FundQuoteService, _coerceScalar
from app.investmentLedger.schemas import FundNavHistoryOut


class _FakeClient:
    """复刻 :class:`AkshareFundQuoteClient` 契约的内存替身。

    只用于驱动 :class:`FundQuoteService` 的过滤与标准化逻辑；
    ``behavior`` 决定本次调用是返回固定数据、抛异常还是返回空列表。
    """

    def __init__(
        self,
        *,
        behavior: str = "ok",
        navHistory: list[dict] | None = None,
    ) -> None:
        self._behavior = behavior
        self._navHistory = navHistory or []

    def fetchNavHistory(self, fundCode: str) -> list[dict]:
        """模拟 akshare 客户端：按构造期设定行为返回数据或抛异常。"""
        if self._behavior == "raise":
            raise RuntimeError("simulated akshare failure")
        if self._behavior == "ok":
            return list(self._navHistory)
        raise AssertionError(f"未知的 fake client 行为：{self._behavior}")


# ---------------------------------------------------------------------------
# 不变量 1：故障收敛（沿用需求 5.6）
# ---------------------------------------------------------------------------


def testNavHistoryAkshareExceptionConvergesToEmptyListAndDoesNotPropagate() -> None:
    """akshare 抛任意异常时，历史净值服务返回空列表且不向调用方抛异常。"""
    service = FundQuoteService(client=_FakeClient(behavior="raise"))

    result = service.getNavHistory("000001")

    assert result == []


# ---------------------------------------------------------------------------
# 不变量 2：历史净值日期过滤与升序
# ---------------------------------------------------------------------------


def testNavHistoryWithoutTradeDateReturnsAllSortedAscending() -> None:
    """未指定日期时返回全部历史净值，按日期升序排列。"""
    history = [
        {"trade_date": "2020-12-28", "unit_nav": "1.4500", "accumulated_nav": "3.2100"},
        {"trade_date": "2020-12-25", "unit_nav": "1.4400", "accumulated_nav": "3.2000"},
        {"trade_date": "2020-12-24", "unit_nav": "1.4300", "accumulated_nav": "3.1900"},
    ]
    service = FundQuoteService(
        client=_FakeClient(behavior="ok", navHistory=history)
    )

    result = service.getNavHistory("000001")

    assert result == [
        FundNavHistoryOut(
            trade_date=date(2020, 12, 24),
            unit_nav="1.4300",
            accumulated_nav="3.1900",
        ),
        FundNavHistoryOut(
            trade_date=date(2020, 12, 25),
            unit_nav="1.4400",
            accumulated_nav="3.2000",
        ),
        FundNavHistoryOut(
            trade_date=date(2020, 12, 28),
            unit_nav="1.4500",
            accumulated_nav="3.2100",
        ),
    ]


def testNavHistoryWithTradeDateReturnsOnlyMatchingDate() -> None:
    """指定日期时只返回该日期的 0 或 1 条记录。"""
    history = [
        {"trade_date": "2020-12-28", "unit_nav": "1.4500", "accumulated_nav": "3.2100"},
        {"trade_date": "2020-12-25", "unit_nav": "1.4400", "accumulated_nav": "3.2000"},
        {"trade_date": "2020-12-24", "unit_nav": "1.4300", "accumulated_nav": "3.1900"},
    ]
    service = FundQuoteService(
        client=_FakeClient(behavior="ok", navHistory=history)
    )

    result = service.getNavHistory("000001", date(2020, 12, 25))

    assert result == [
        FundNavHistoryOut(
            trade_date=date(2020, 12, 25),
            unit_nav="1.4400",
            accumulated_nav="3.2000",
        ),
    ]


def testNavHistoryWithNonExistingDateReturnsEmptyList() -> None:
    """指定日期不存在时返回空列表，不抛异常。"""
    history = [
        {"trade_date": "2020-12-28", "unit_nav": "1.4500", "accumulated_nav": "3.2100"},
    ]
    service = FundQuoteService(
        client=_FakeClient(behavior="ok", navHistory=history)
    )

    result = service.getNavHistory("000001", date(2099, 1, 1))

    assert result == []


def testNavHistoryEntriesWithIllegalDateAreDroppedSilently() -> None:
    """日期无法解析的条目被静默丢弃，不影响后续合法条目。"""
    history = [
        # 非法日期字符串
        {"trade_date": "not-a-date", "unit_nav": "1.4500", "accumulated_nav": "3.2100"},
        # 空字符串
        {"trade_date": "", "unit_nav": "1.4500", "accumulated_nav": "3.2100"},
        # None
        {"trade_date": None, "unit_nav": "1.4500", "accumulated_nav": "3.2100"},
        # 合法条目（应被保留）
        {"trade_date": "2020-12-28", "unit_nav": "1.4500", "accumulated_nav": "3.2100"},
    ]
    service = FundQuoteService(
        client=_FakeClient(behavior="ok", navHistory=history)
    )

    result = service.getNavHistory("000001")

    assert result == [
        FundNavHistoryOut(
            trade_date=date(2020, 12, 28),
            unit_nav="1.4500",
            accumulated_nav="3.2100",
        ),
    ]


def testNavHistoryAcceptsTimestampLikeDateValue() -> None:
    """净值日期为 date/datetime 子类时按 .date() 提取纯 date。"""
    class _FakeTimestamp:
        """模拟 pandas.Timestamp 的最小契约：提供 date() 方法。"""

        def __init__(self, year: int, month: int, day: int) -> None:
            self._year = year
            self._month = month
            self._day = day

        def date(self) -> date:  # noqa: D401
            """返回纯 date 对象。"""
            return date(self._year, self._month, self._day)

    history = [
        {
            "trade_date": _FakeTimestamp(2020, 12, 28),
            "unit_nav": "1.4500",
            "accumulated_nav": "3.2100",
        },
    ]
    service = FundQuoteService(
        client=_FakeClient(behavior="ok", navHistory=history)
    )

    result = service.getNavHistory("000001")

    assert result == [
        FundNavHistoryOut(
            trade_date=date(2020, 12, 28),
            unit_nav="1.4500",
            accumulated_nav="3.2100",
        ),
    ]


def testNavHistoryAcceptsPythonDateObject() -> None:
    """净值日期直接为 datetime.date 对象时按原值保留。"""
    history = [
        {
            "trade_date": date(2020, 12, 28),
            "unit_nav": "1.4500",
            "accumulated_nav": "3.2100",
        },
    ]
    service = FundQuoteService(
        client=_FakeClient(behavior="ok", navHistory=history)
    )

    result = service.getNavHistory("000001")

    assert result == [
        FundNavHistoryOut(
            trade_date=date(2020, 12, 28),
            unit_nav="1.4500",
            accumulated_nav="3.2100",
        ),
    ]


def testCoerceScalarConvertsFloatAndIntToStringForClientLayer() -> None:
    """客户端层 ``_coerceScalar`` 把 float/int 转成字符串，避免出参层拒绝 float。

    akshare 返回的净值通常为 ``float64``，若原样传给出参层会被项目「金额以十进制
    精确表达、禁止 float」的校验拒绝。客户端层调用 ``_coerceScalar`` 把数值统一转
    十进制字符串后再交由出参层精确解析为 :class:`Decimal`。
    """
    # float 转 str：受 IEEE 754 精度限制，1.4500 在 float64 中实际为 1.45
    assert _coerceScalar(1.4500) == "1.45"
    # int 转 str：原值保留
    assert _coerceScalar(3) == "3"
    # 字符串原样去空白透传
    assert _coerceScalar("1.4500") == "1.4500"
    assert _coerceScalar("  1.4500  ") == "1.4500"
    # None 透传，表示缺失指标
    assert _coerceScalar(None) is None
    # 空字符串视为缺失
    assert _coerceScalar("") is None
    assert _coerceScalar("   ") is None


def testCoerceScalarTreatsNumpyNanAsMissing() -> None:
    """``numpy.nan`` 与自身不等，``_coerceScalar`` 把它收敛为 ``None``。"""
    nan = float("nan")
    assert _coerceScalar(nan) is None


# ---------------------------------------------------------------------------
# 不变量 3：空数据收敛
# ---------------------------------------------------------------------------


def testNavHistoryEmptyAkshareResultReturnsEmptyList() -> None:
    """akshare 返回空列表时历史净值服务返回空列表。"""
    service = FundQuoteService(
        client=_FakeClient(behavior="ok", navHistory=[])
    )

    result = service.getNavHistory("000001")

    assert result == []
