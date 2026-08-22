"""基金历史净值代理：把 akshare 单只基金历史净值调用收敛为标准出参。

设计要点（沿用 :mod:`app.investmentLedger.fund_search` 的「客户端 + 服务」两层结构）：

- 本模块是 ``GET /fundQuote/navHistory`` 的业务实现，路由层只做 HTTP 语义绑定，
  不接触 akshare 调用细节与异常处理。
- akshare 的 ``fund_open_fund_info_em`` 返回单只基金历史净值，客户端层把中文
  列名映射为英文键后转出。
- 任何 akshare 失败（网络异常、缺列、非 DataFrame、空结果）一律由服务层收敛
  为空列表，**绝不向用户抛出异常**（沿用需求 5.6 的故障收敛原则）。错误细节
  只写服务端日志，不外泄给前端。
- 本模块**无数据库依赖、无状态**，服务按请求构造；akshare 客户端可在构造期
  注入，便于单元测试以 fake client 隔离真实外网与 akshare 依赖。
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

from app.investmentLedger.constants import (
    AKSHARE_FUND_NAV_ACCUMULATED_COLUMN,
    AKSHARE_FUND_NAV_DATE_COLUMN,
    AKSHARE_FUND_NAV_UNIT_COLUMN,
)
from app.investmentLedger.schemas import (
    FundNavHistoryOut,
)
from app.logger import logger

if TYPE_CHECKING:
    # 仅用于静态类型检查；运行时由客户端层方法内延迟导入，
    # 使单元测试在不安装 pandas 的环境下能通过 fake client 隔离运行。
    import pandas as pd


class AkshareFundQuoteClient:
    """对 akshare 基金历史净值接口的受控客户端。

    封装 ``ak.fund_open_fund_info_em`` 调用，把返回的 DataFrame 转换为键名
    稳定的 ``list[dict]``：历史净值的中文列名被映射为英文键。本类只负责
    「取数 + 键名归一」，不做业务过滤；过滤职责在 :class:`FundQuoteService`。
    任何异常（网络、缺列、非 DataFrame）均向上抛出，由服务层捕获并收敛为
    空结果 + 日志。

    akshare 与 pandas 均在方法内延迟导入，避免在模块加载期触发 akshare 的
    重型初始化，也使单元测试在不安装 akshare/pandas 的环境下能通过 fake
    client 隔离运行。
    """

    def fetchNavHistory(self, fundCode: str) -> list[dict]:
        """调用 ``ak.fund_open_fund_info_em`` 并返回键名稳定的历史净值列表。

        :param fundCode: 已由 Pydantic 校验的非空基金代码。
        :returns: 历史净值列表，每项为 ``dict``，键名为
            ``trade_date`` / ``unit_nav`` / ``accumulated_nav``；
            DataFrame 为空时返回空列表。
        :raises Exception: akshare 调用失败、返回非 DataFrame 或缺关键列时
            向上抛出，由服务层收敛。
        """
        # 方法内延迟导入 akshare 与 pandas：避免在模块加载期触发 akshare 的重型
        # 初始化，也使单元测试在不安装 akshare/pandas 的环境下能通过 fake client
        # 隔离运行。
        import pandas as pd
        import akshare as ak

        df: pd.DataFrame = ak.fund_open_fund_info_em(symbol=fundCode)
        if not isinstance(df, pd.DataFrame) or df.empty:
            return []
        required = (
            AKSHARE_FUND_NAV_DATE_COLUMN,
            AKSHARE_FUND_NAV_UNIT_COLUMN,
            AKSHARE_FUND_NAV_ACCUMULATED_COLUMN,
        )
        if any(col not in df.columns for col in required):
            raise ValueError("akshare fund_open_fund_info_em 缺关键列")

        rows: list[dict] = []
        for _, row in df.iterrows():
            rows.append(
                {
                    "trade_date": row.get(AKSHARE_FUND_NAV_DATE_COLUMN),
                    "unit_nav": _coerceScalar(
                        row.get(AKSHARE_FUND_NAV_UNIT_COLUMN)
                    ),
                    "accumulated_nav": _coerceScalar(
                        row.get(AKSHARE_FUND_NAV_ACCUMULATED_COLUMN)
                    ),
                }
            )
        return rows


def _coerceScalar(value: Any) -> Any:
    """把 akshare 字段值收敛为可由出参层解析的标量。

    ``None`` 透传（表示缺失指标）；非空字符串去除首尾空白后透传；
    数值（含 ``numpy`` 类型）一律先转十进制字符串再交由出参层 :func:`_coerceDecimalString`
    精确解析为 :class:`Decimal`，避免 ``float`` 直入出参层被项目「金额以十进制
    精确表达」的校验拒绝。``numpy.nan`` 一律透传为 ``None``，避免 ``NaN``
    进入响应体后被序列化为非法 JSON 值。

    :param value: akshare 原始字段值。
    :returns: 标量值或 ``None``。
    """
    if value is None:
        return None
    # pandas / numpy 的 NaN 判定：与自身不等是 NaN 的特征
    try:
        if value != value:  # noqa: PLR0124
            return None
    except Exception:  # noqa: BLE001
        # 与自身比较失败（如 object dtype）视为非数值，按字符串路径处理
        pass
    if isinstance(value, str):
        text = value.strip()
        return text or None
    # 数值（int / float / numpy 数值）：转十进制字符串后再交由出参层精确解析，
    # 避免 float 直入出参层被项目「禁止 float」校验拒绝。float→str 会受 IEEE 754
    # 精度限制，但 akshare 返回的净值本身已是 float，此处只做最佳努力转换。
    text = str(value).strip()
    return text or None


class FundQuoteService:
    """基金历史净值代理用例：调用 akshare 客户端、过滤、标准化为出参。

    akshare 失败均收敛为空列表并记录服务端日志，**绝不向用户抛出异常**
    （沿用需求 5.6 的故障收敛原则）。本服务无数据库依赖、无状态，可被路由层
    按请求构造；akshare 客户端可在构造期注入，便于单元测试以 fake client
    隔离真实外网与 akshare 依赖。
    """

    def __init__(
        self, client: AkshareFundQuoteClient | None = None
    ) -> None:
        """装配 akshare 客户端。

        :param client: akshare 客户端实例；为 ``None`` 时使用默认实例，
            正式请求按配置访问真实 akshare 接口；测试应注入 fake client。
        """
        self._client = client or AkshareFundQuoteClient()

    def getNavHistory(
        self, fundCode: str, tradeDate: date | None = None
    ) -> list[FundNavHistoryOut]:
        """返回指定基金的历史净值条目列表。

        - ``tradeDate`` 为 ``None`` 时返回全部历史净值，按日期升序排列；
        - ``tradeDate`` 非 ``None`` 时返回匹配该日期的 0 或 1 条记录。

        :param fundCode: 已通过 Pydantic 校验的非空基金代码。
        :param tradeDate: 可选净值日期；为 ``None`` 时返回全部历史。
        :returns: 标准化出参列表；akshare 失败或无匹配时为空列表。
        """
        try:
            rows = self._client.fetchNavHistory(fundCode)
        except Exception as error:
            # akshare 异常不外泄，统一收敛为空列表 + 服务端日志
            logger.warning(
                "investmentLedger 基金历史净值 akshare 调用失败：%s",
                type(error).__name__,
            )
            return []

        normalized: list[FundNavHistoryOut] = []
        for row in rows:
            item = self._normalizeHistory(row, tradeDate)
            if item is not None:
                normalized.append(item)
        # 升序排列：使前端从最早到最新逐日渲染
        normalized.sort(key=lambda item: item.trade_date)
        return normalized

    @staticmethod
    def _normalizeHistory(
        row: dict, tradeDate: date | None
    ) -> FundNavHistoryOut | None:
        """把单条 akshare 历史净值原始字典标准化为 :class:`FundNavHistoryOut`。

        :param row: 客户端层输出的历史净值字典。
        :param tradeDate: 调用方传入的目标日期；非 ``None`` 时只接受同日记录。
        :returns: 标准结果；日期或净值缺失、或与目标日期不一致时返回 ``None``。
        """
        rawDate = row.get("trade_date")
        parsedDate = _coerceDate(rawDate)
        if parsedDate is None:
            return None
        if tradeDate is not None and parsedDate != tradeDate:
            return None
        try:
            return FundNavHistoryOut(
                trade_date=parsedDate,
                unit_nav=row.get("unit_nav"),
                accumulated_nav=row.get("accumulated_nav"),
            )
        except Exception:
            # 数值无法精确解析为十进制字符串等校验失败时静默丢弃
            return None


def _coerceDate(value: Any) -> date | None:
    """把 akshare 净值日期字段值收敛为 :class:`datetime.date`。

    akshare ``fund_open_fund_info_em`` 的净值日期通常为字符串
    （如 ``"2020-12-28"``）或 ``pandas.Timestamp``；本函数统一解析为
    :class:`date`，非法时返回 ``None``，由调用方决定是否丢弃该行。

    :param value: akshare 原始日期字段值。
    :returns: 解析后的 ``date``；非法或为空时为 ``None``。
    """
    if value is None:
        return None
    # datetime.datetime / pandas.Timestamp 均为 date 的子类，
    # 通过 .date() 方法剥离时间部分，确保返回纯 date 对象。
    if isinstance(value, date):
        dateMethod = getattr(value, "date", None)
        if callable(dateMethod):
            try:
                return dateMethod()
            except Exception:  # noqa: BLE001
                return value
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text)
        except ValueError:
            return None
    # 其它带 date() 方法的对象（兼容 object dtype 的非 str / 非 date 值）
    dateMethod = getattr(value, "date", None)
    if callable(dateMethod):
        try:
            return dateMethod()
        except Exception:  # noqa: BLE001
            return None
    return None
