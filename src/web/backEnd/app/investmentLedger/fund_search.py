"""基金搜索代理：把前端搜索请求转发至第三方接口并格式化为标准结果。

设计要点（与设计文档「后端设计 · 7. 基金搜索代理服务」逐条对应）：

- 本模块是 ``GET /fundSearch`` 的业务实现，承担「转发 + 标准化 + 故障收敛」
  三项职责；路由层只做 HTTP 语义绑定，不接触第三方域名或异常处理。
- 第三方接口为天天基金搜索建议接口（``fundsuggest.eastmoney.com``）。
  本模块**不带 JSONP ``callback`` 参数**直接请求 JSON，避免 JSONP 解析；
  第三方任一失败（网络异常、超时、非 JSON、缺字段）均收敛为空结果并记录
  服务端日志，**绝不向用户抛出异常**（需求 5.6）。
- 仅保留基金条目（``FundBaseInfo`` 非空或 ``CATEGORYDESC == "基金"``），
  过滤掉股票、指数等非基金条目（需求 5.7）；出参只暴露 ``fund_name`` /
  ``fund_code`` 两个字段，长度上限与交易草稿对齐，使前端选中后可直接回填。
- 本模块**无数据库依赖、无状态**，服务按请求构造；第三方客户端可注入，
  便于单元测试以 fake client 隔离真实外网。
"""

from __future__ import annotations

from typing import Any

import requests

from app.investmentLedger.constants import (
    MAX_PRODUCT_CODE_LENGTH,
    MAX_PRODUCT_NAME_LENGTH,
)
from app.investmentLedger.schemas import FundSearchOut
from app.logger import logger

# ---------------------------------------------------------------------------
# 第三方接口配置（固化在本模块内部，不暴露给服务层或路由层）
# ---------------------------------------------------------------------------

#: 第三方基金搜索建议接口的固定 URL；仅在本模块内部使用，不拼接前缀。
EASTMONEY_FUND_SEARCH_URL = (
    "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
)

#: 第三方请求固定参数：``m=1`` 为搜索模式；刻意不带 ``callback``（JSONP）与
#: ``_``（时间戳）参数，使第三方直接返回纯 JSON，避免 JSONP 解析负担与风险。
EASTMONEY_FUND_SEARCH_MODE = "1"

#: 第三方请求超时（秒，connect, read 元组）。采用较短有限超时，避免请求挂起
#: 阻塞前端搜索体验；超时由服务层收敛为空结果，不向用户抛异常。
EASTMONEY_FUND_SEARCH_TIMEOUT = (3.0, 5.0)

#: 第三方响应中承载结果数组的字段名；缺失或非数组时视为空结果。
EASTMONEY_DATAS_FIELD = "Datas"

#: 第三方结果项中标识「基金类别」的字段；取值 ``"基金"`` 表示该条目为基金。
EASTMONEY_CATEGORYDESC_FIELD = "CATEGORYDESC"

#: 第三方结果项中承载基金详情的字段；非 ``None`` 表示该条目为基金。
EASTMONEY_FUNDBASEINFO_FIELD = "FundBaseInfo"

#: 第三方结果项中基金名称的字段名。
EASTMONEY_NAME_FIELD = "NAME"

#: 第三方结果项中基金代码的字段名。
EASTMONEY_CODE_FIELD = "CODE"

#: 标识为基金的第三方类别描述值。
FUND_CATEGORY_DESC = "基金"


def _isFundEntry(entry: Any) -> bool:
    """判断第三方结果项是否为基金条目（需求 5.7）。

    判定规则：``FundBaseInfo`` 字段非 ``None``（基金详情存在）**或**
    ``CATEGORYDESC`` 字段等于 ``"基金"``。两者满足其一即视为基金；
    股票、指数、债券等非基金条目一律返回 ``False``。

    :param entry: 第三方 ``Datas`` 数组中的单个对象（预期为 ``dict``）。
    :returns: 该条目是否为基金。
    """
    if not isinstance(entry, dict):
        return False
    if entry.get(EASTMONEY_FUNDBASEINFO_FIELD) is not None:
        return True
    return entry.get(EASTMONEY_CATEGORYDESC_FIELD) == FUND_CATEGORY_DESC


def _coerceNonEmptyString(value: Any, maxLength: int) -> str | None:
    """把第三方字段值收敛为长度合法的非空字符串，非法时返回 ``None``。

    :param value: 第三方字段原始值，可能为 ``str`` / ``None`` / 其它类型。
    :param maxLength: 允许的最大字符数；超长视为非法（避免出参校验失败）。
    :returns: 去除首尾空白后非空且不超长的字符串；否则 ``None``。
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text or len(text) > maxLength:
        return None
    return text


class EastmoneyFundSearchClient:
    """对第三方 FundSearchAPI 的受控 HTTP 客户端（需求 5.2）。

    第三方域名、路径与参数在本类内部固化，不暴露给服务层或路由层，便于
    统一替换数据源时只改本类。本类只负责「取数」，不判断业务规则、不做
    基金过滤；过滤职责在 :class:`FundSearchService`。任何异常（网络、超时、
    非 JSON、缺字段）均向上抛出，由服务层捕获并收敛为空结果 + 日志。
    """

    def __init__(
        self,
        *,
        url: str = EASTMONEY_FUND_SEARCH_URL,
        mode: str = EASTMONEY_FUND_SEARCH_MODE,
        timeout: tuple[float, float] = EASTMONEY_FUND_SEARCH_TIMEOUT,
    ) -> None:
        """装配第三方接口配置。

        :param url: 第三方接口 URL，默认为天天基金搜索建议接口。
        :param mode: 第三方 ``m`` 参数值，固定为搜索模式。
        :param timeout: ``(connect_timeout, read_timeout)`` 元组，单位秒。
        """
        self._url = url
        self._mode = mode
        self._timeout = timeout

    def search(self, keyword: str) -> list[dict]:
        """转发关键词至第三方，返回原始 ``Datas`` 数组。

        不带 ``callback`` 参数以直接获得 JSON；响应体非约定形状时抛
        :class:`ValueError`，由服务层收敛。

        :param keyword: 已由 Pydantic 校验的非空用户输入。
        :returns: 第三方 ``Datas`` 数组（每项为 ``dict``）；缺字段时为空数组。
        :raises requests.RequestException: 网络异常或超时。
        :raises ValueError: 响应非 JSON 对象或 ``Datas`` 非数组。
        """
        response = requests.get(
            self._url,
            params={"m": self._mode, "key": keyword},
            timeout=self._timeout,
            headers={
                # 仅声明通用 Accept，不伪装浏览器 UA 以规避合规风险；
                # 第三方对该接口默认返回 JSON，无需特殊请求头。
                "Accept": "application/json"
            },
        )
        response.raise_for_status()
        payload: Any = response.json()
        if not isinstance(payload, dict):
            raise ValueError("第三方响应不是 JSON 对象")
        datas = payload.get(EASTMONEY_DATAS_FIELD)
        if not isinstance(datas, list):
            raise ValueError("第三方响应 Datas 字段不是数组")
        # 只保留可识别为 dict 的项，过滤掉 None/标量等噪声数据
        return [item for item in datas if isinstance(item, dict)]


class FundSearchService:
    """基金搜索代理用例：调用第三方客户端、过滤非基金条目、标准化为出参。

    第三方任一失败均收敛为空列表并记录服务端日志，**绝不向用户抛出异常**
    （需求 5.6）。本服务无数据库依赖、无状态，可被路由层按请求构造；
    第三方客户端可在构造期注入，便于单元测试以 fake client 隔离真实外网。
    """

    def __init__(
        self, client: EastmoneyFundSearchClient | None = None
    ) -> None:
        """装配第三方客户端。

        :param client: 第三方客户端实例；为 ``None`` 时使用默认实例，
            正式请求按配置访问真实接口；测试应注入 fake client。
        """
        self._client = client or EastmoneyFundSearchClient()

    @staticmethod
    def _normalize(entry: dict) -> FundSearchOut | None:
        """把单条第三方基金条目标准化为 :class:`FundSearchOut`。

        :param entry: 已确认是基金的第三方结果项。
        :returns: 标准结果；名称或代码缺失/为空/超长时返回 ``None``，
            该条目被静默丢弃，不抛异常、不阻断后续条目。
        """
        name = _coerceNonEmptyString(
            entry.get(EASTMONEY_NAME_FIELD), MAX_PRODUCT_NAME_LENGTH
        )
        code = _coerceNonEmptyString(
            entry.get(EASTMONEY_CODE_FIELD), MAX_PRODUCT_CODE_LENGTH
        )
        if name is None or code is None:
            return None
        return FundSearchOut(fund_name=name, fund_code=code)

    def searchFunds(self, keyword: str) -> list[FundSearchOut]:
        """转发关键词并返回标准化的基金结果列表。

        :param keyword: 已通过 Pydantic 校验的非空用户输入。
        :return: 仅含基金条目的标准结果；第三方失败或无匹配时为空列表。
        不变量: 第三方异常不外泄，全部收敛为空结果 + 服务端日志（需求 5.6）；
            非基金条目被过滤（需求 5.7）。
        """
        try:
            entries = self._client.search(keyword)
        except Exception as error:
            # 网络异常、超时、非 JSON、缺字段等一切第三方失败在此收敛；
            # 不记录 keyword 原文以遵循敏感值约束（需求 4.9 的延伸保护）。
            logger.warning(
                "investmentLedger 基金搜索第三方调用失败：%s",
                type(error).__name__,
            )
            return []

        results: list[FundSearchOut] = []
        for entry in entries:
            if not _isFundEntry(entry):
                continue
            normalized = self._normalize(entry)
            if normalized is not None:
                results.append(normalized)
        return results
