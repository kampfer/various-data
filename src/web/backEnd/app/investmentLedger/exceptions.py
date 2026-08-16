"""投资交易账本的异常体系与全局异常处理器。

设计要点（与设计文档「Error Handling · 后端异常体系（``exceptions.py``）」逐条对应）：

- 全部业务异常继承 :class:`LedgerError`，每个子类自带 HTTP 状态码、业务 ``code``
  与**完整中文** ``msg``，由 :func:`registerLedgerExceptionHandlers` 统一渲染为
  项目既有的 ``{code, msg, data}`` 信封（需求 1.2、1.5、2.20、2.21、2.26、2.30、3.2）；
- Pydantic 的 :class:`~fastapi.exceptions.RequestValidationError` 被翻译为
  ``data.fieldErrors``：``field`` 为 camelCase 字段名（与前端表单项名称一致），
  ``code`` 取 ``NOT_IN_ENUM`` / ``INVALID_SCALE`` / ``OUT_OF_RANGE`` / ``TOO_LONG``
  四个常量之一（复用 ``schemas.py`` 中同名的 ``ERROR_CODE_*``），
  ``message`` 为可直接展示的完整中文句子；
- **英文枚举码绝不原样回显给用户**：枚举取值非法时 ``message`` 直接书写
  「产品类型必须为理财、基金或股票之一」这类句子，后端不维护「码 → 中文」映射表，
  也不把 Pydantic 的英文原文（如 ``Input should be 'WEALTH', ...``）透传出去；
- 数据库异常（:class:`~sqlalchemy.exc.IntegrityError`、
  :class:`~sqlalchemy.exc.OperationalError`）统一收敛为 ``code: 500`` 与
  ``msg: "数据保存失败，请稍后重试"``，**不外泄 SQL 语句、表名与堆栈**；
  详细信息只写入服务端日志（``app.logger``）。

注意：``RequestValidationError`` 处理器注册在 ``FastAPI`` 应用级别，因此对既有模块
（``sinaFinanceNews`` / ``nbs`` / ``akshare``）的校验失败响应同样生效；这是设计文档
「装配点」明确接受的行为——统一信封本身与既有 ``{code, msg, data}`` 约定一致。
"""

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from app.investmentLedger.constants import (
    MAX_PAGE_SIZE,
    MAX_PRODUCT_CODE_LENGTH,
    MAX_PRODUCT_NAME_LENGTH,
    MAX_SEARCH_VALUE_LENGTH,
    MAX_VALUATION_UNIT_PRICE,
    MIN_PAGE_SIZE,
)
from app.investmentLedger.schemas import (
    ERROR_CODE_INVALID_SCALE,
    ERROR_CODE_NOT_A_NUMBER,
    ERROR_CODE_NOT_IN_ENUM,
    ERROR_CODE_NOT_INTEGER,
    ERROR_CODE_OUT_OF_RANGE,
    ERROR_CODE_TOO_LONG,
    FieldErrorItem,
)
from app.logger import logger

# ---------------------------------------------------------------------------
# HTTP 状态码：以字面量在本模块内定义，避免依赖 starlette 各版本间不断更名的常量
# （如 422 在新版中由 HTTP_422_UNPROCESSABLE_ENTITY 更名为 ..._CONTENT）
# ---------------------------------------------------------------------------

#: 请求语义有误的兜底状态码
HTTP_400_BAD_REQUEST = 400

#: 目标资源不存在
HTTP_404_NOT_FOUND = 404

#: 请求格式正确但内容未通过校验
HTTP_422_UNPROCESSABLE_ENTITY = 422

#: 服务端内部错误
HTTP_500_INTERNAL_SERVER_ERROR = 500

# ---------------------------------------------------------------------------
# 业务状态码：与 HTTP 状态码取同值，便于前端只判 code 一处（沿用项目既有信封语义）
# ---------------------------------------------------------------------------

#: 兜底业务错误码（LedgerError 基类）
BUSINESS_CODE_BAD_REQUEST = 400

#: 资源不存在错误码（删除的交易不存在，需求 1.5）
BUSINESS_CODE_NOT_FOUND = 404

#: 参数校验失败错误码（需求 1.2、2.20、2.21、2.26、2.30、3.2）
BUSINESS_CODE_VALIDATION_FAILED = 422

#: 服务端内部错误码（数据库异常统一收敛于此）
BUSINESS_CODE_INTERNAL_ERROR = 500

#: 数据库异常对外统一提示语：不含 SQL、表名与堆栈，避免外泄实现细节
DATABASE_ERROR_MESSAGE = "数据保存失败，请稍后重试"


class LedgerError(Exception):
    """投资交易账本业务异常基类：兜底业务错误，对外 HTTP 400、业务 ``code`` 400。

    子类只需覆写三个类属性即可获得完整的响应渲染能力：

    - :attr:`statusCode`：HTTP 状态码；
    - :attr:`code`：``{code, msg, data}`` 信封中的业务状态码；
    - :attr:`defaultMsg`：未显式传入 ``msg`` 时使用的默认中文提示语。
    """

    #: HTTP 状态码，默认 400（兜底业务错误）
    statusCode: int = HTTP_400_BAD_REQUEST

    #: 业务状态码，写入响应信封的 code 字段
    code: int = BUSINESS_CODE_BAD_REQUEST

    #: 默认中文提示语，完整句子，可由前端直接展示
    defaultMsg: str = "投资交易账本操作失败"

    def __init__(
        self,
        msg: str | None = None,
        fieldErrors: Iterable[FieldErrorItem] | None = None,
    ) -> None:
        """构造业务异常。

        :param msg: 中文提示语；为 ``None`` 时取子类的 :attr:`defaultMsg`。
        :param fieldErrors: 字段级错误项集合；为 ``None`` 或空时响应 ``data`` 为 ``None``。
        """
        self.msg = msg or self.defaultMsg
        self.fieldErrors: list[FieldErrorItem] = list(fieldErrors or ())
        super().__init__(self.msg)

    def toResponsePayload(self) -> dict[str, Any]:
        """渲染为项目统一响应信封 ``{code, msg, data}``。

        :returns: 可直接交给 :class:`~fastapi.responses.JSONResponse` 的字典；
            存在字段级错误时 ``data`` 为 ``{"fieldErrors": [...]}``，否则为 ``None``。
        """
        data: dict[str, Any] | None = None
        if self.fieldErrors:
            # by_alias=True 保证 field/code/message 以 camelCase 输出，与前端契约一致
            data = {
                "fieldErrors": [
                    item.model_dump(by_alias=True) for item in self.fieldErrors
                ]
            }
        return {"code": self.code, "msg": self.msg, "data": data}


class LedgerValidationError(LedgerError):
    """服务层判定的业务校验失败：HTTP 422、业务 ``code`` 422（需求 1.2、3.2）。

    与 Pydantic 的字段校验互补：Pydantic 只能看到单个请求的字段形态，
    而本异常用于表达需要上下文（如结果集总页数、当前已应用条件）才能判定的失败。
    """

    statusCode = HTTP_422_UNPROCESSABLE_ENTITY
    code = BUSINESS_CODE_VALIDATION_FAILED
    defaultMsg = "参数校验失败"


class TransactionNotFound(LedgerError):
    """待删除的交易记录不存在：HTTP 404、业务 ``code`` 404（需求 1.5）。"""

    statusCode = HTTP_404_NOT_FOUND
    code = BUSINESS_CODE_NOT_FOUND
    defaultMsg = "交易记录不存在或已被删除"

    def __init__(self, transactionId: int | None = None) -> None:
        """构造交易不存在异常。

        :param transactionId: 交易主键，仅用于服务端定位；**不写入对外提示语**，
            因为需求 2.23 要求不向用户展示交易记录标识。
        """
        self.transactionId = transactionId
        super().__init__()


class PageOutOfRange(LedgerValidationError):
    """请求页码小于 1 或大于总页数（需求 2.30、2.31）。

    ``msg`` 在总页数大于 0 时必定包含「有效页码为 1 至 N」，
    使前端可直接把有效页码范围展示给用户；总页数为 0 时改用需求 2.31 的措辞
    （此时不存在任何有效页码，给出「1 至 0」这种范围会误导用户）。
    """

    def __init__(self, page: int, pageCount: int) -> None:
        """构造页码越界异常。

        :param page: 用户请求的页码。
        :param pageCount: 当前结果集的总页数；为 0 表示当前结果没有可浏览的页。
        """
        self.page = page
        self.pageCount = pageCount
        if pageCount > 0:
            msg = f"请求的页码无效，有效页码为 1 至 {pageCount}"
        else:
            msg = "当前结果没有可浏览的页"
        super().__init__(
            msg,
            fieldErrors=[
                FieldErrorItem(
                    field="page", code=ERROR_CODE_OUT_OF_RANGE, message=msg
                )
            ],
        )


class InvalidPageSize(LedgerValidationError):
    """自定义页大小不是 1 至 100 的整数（需求 2.26）。"""

    def __init__(self, pageSize: object = None) -> None:
        """构造页大小非法异常。

        :param pageSize: 用户提交的页大小原值，仅用于服务端排查，不写入提示语。
        """
        self.pageSize = pageSize
        msg = f"自定义页大小必须为 {MIN_PAGE_SIZE} 至 {MAX_PAGE_SIZE} 的整数"
        super().__init__(
            msg,
            fieldErrors=[
                FieldErrorItem(
                    field="pageSize", code=ERROR_CODE_OUT_OF_RANGE, message=msg
                )
            ],
        )


class InvalidDateRange(LedgerValidationError):
    """交易日期范围缺项、含非法日历日期或起始晚于结束（需求 2.21）。"""

    #: 该异常默认落到的表单字段：日期范围控件以起始日期为定位锚点
    fieldName = "startDate"

    def __init__(self, msg: str | None = None) -> None:
        """构造日期范围非法异常。

        :param msg: 具体中文原因（如「交易日期范围必须同时提供起始日期与结束日期」）；
            为 ``None`` 时使用覆盖三种失败形态的通用句子。
        """
        message = msg or (
            "交易日期范围必须同时提供有效的起始日期与结束日期，且起始日期不能晚于结束日期"
        )
        super().__init__(
            message,
            fieldErrors=[
                FieldErrorItem(
                    field=self.fieldName,
                    code=ERROR_CODE_OUT_OF_RANGE,
                    message=message,
                )
            ],
        )


class InvalidSearchValue(LedgerValidationError):
    """产品名称或产品代码搜索值为空或超过 100 个字符（需求 2.20）。"""

    def __init__(self, field: str = "productName") -> None:
        """构造搜索值非法异常。

        :param field: 触发失败的 camelCase 字段名，取 ``productName`` 或 ``productCode``，
            使前端能把错误定位到对应的搜索框。
        """
        self.field = field
        msg = f"搜索值不能为空，且不能超过 {MAX_SEARCH_VALUE_LENGTH} 个字符"
        super().__init__(
            msg,
            fieldErrors=[
                FieldErrorItem(
                    field=field, code=ERROR_CODE_OUT_OF_RANGE, message=msg
                )
            ],
        )


# ---------------------------------------------------------------------------
# RequestValidationError → fieldErrors 的翻译表（需求 1.2、3.2）
# ---------------------------------------------------------------------------

#: FastAPI 在 loc 首位放置的请求来源标记，翻译字段名时需要剥离
REQUEST_SOURCES = ("body", "query", "path", "header", "cookie")

#: 模型级校验器（TransactionQuery.checkDateRange / checkProductScope 等）产生的错误
#: loc 中不含字段名，此处按中文原因里的关键词回落到一个合理的 camelCase 字段名，
#: 使前端仍能把提示挂到具体控件上。
MODEL_LEVEL_FIELD_HINTS = (
    ("交易日期范围", "startDate"),  # 日期范围成对性与先后顺序 → 定位到起始日期控件
    ("产品历史交易范围", "scopeProductType"),  # 范围成对性 → 定位到范围产品类型
    ("指标", "available"),  # Metric 可用性不变量（仅出参构造期出现）
)

#: 既无字段名也无关键词可依时使用的兜底字段名：表示「整份请求」而非某一控件
FALLBACK_FIELD_NAME = "request"

#: Pydantic v2 错误 type → 本模块四个字段级错误码的映射；未列出的一律回落 OUT_OF_RANGE
PYDANTIC_TYPE_TO_ERROR_CODE = {
    "enum": ERROR_CODE_NOT_IN_ENUM,  # 枚举取值非法（含中文字面量、小写码）
    "literal_error": ERROR_CODE_NOT_IN_ENUM,  # Literal 取值非法（排序方向、模块标识）
    "string_too_long": ERROR_CODE_TOO_LONG,  # 文本超长
    "decimal_max_places": ERROR_CODE_INVALID_SCALE,  # 小数位超限
    "decimal_parsing": ERROR_CODE_NOT_A_NUMBER,  # 十进制字面量非法
    "float_parsing": ERROR_CODE_NOT_A_NUMBER,  # 数值字面量非法
}

#: 字段 → 中文标签，供兜底句子拼装（后端此处的中文只服务于错误提示，不承担展示职责）
FIELD_LABELS = {
    "productType": "产品类型",
    "productName": "产品名称",
    "productCode": "产品代码",
    "transactionPrice": "交易价格",
    "transactionQuantity": "交易数量",
    "direction": "交易方向",
    "tradeDate": "交易日期",
    "valuationDate": "估值日期",
    "startDate": "起始日期",
    "endDate": "结束日期",
    "page": "页码",
    "pageSize": "页大小",
    "tradeDateOrder": "交易日期排序方向",
    "holdingSortField": "持仓条目排序字段",
    "holdingSortOrder": "持仓条目排序方向",
    "scopeProductType": "产品历史交易范围的产品类型",
    "scopeProductCode": "产品历史交易范围的产品代码",
}

#: 无字段标签时使用的中文代称
FALLBACK_FIELD_LABEL = "该输入项"

#: (字段, 错误码) → 完整中文句子；覆盖 Pydantic 内置校验（其原文为英文）产生的错误。
#: 枚举类错误在此处直接书写「必须为理财、基金或股票之一」，绝不回显英文码。
FIELD_MESSAGES = {
    ("productType", ERROR_CODE_NOT_IN_ENUM): "产品类型必须为理财、基金或股票之一",
    ("direction", ERROR_CODE_NOT_IN_ENUM): "交易方向必须为买入或卖出之一",
    ("scopeProductType", ERROR_CODE_NOT_IN_ENUM): (
        "产品历史交易范围的产品类型必须为理财、基金或股票之一"
    ),
    ("tradeDateOrder", ERROR_CODE_NOT_IN_ENUM): "交易日期排序方向必须为升序或降序",
    ("holdingSortField", ERROR_CODE_NOT_IN_ENUM): (
        "持仓条目排序字段必须为持仓或总收益"
    ),
    ("holdingSortOrder", ERROR_CODE_NOT_IN_ENUM): "持仓条目排序方向必须为升序或降序",
    ("productName", ERROR_CODE_TOO_LONG): (
        f"产品名称不能超过 {MAX_PRODUCT_NAME_LENGTH} 个字符"
    ),
    ("productName", ERROR_CODE_OUT_OF_RANGE): (
        f"产品名称不能为空，且不能超过 {MAX_PRODUCT_NAME_LENGTH} 个字符"
    ),
    ("productCode", ERROR_CODE_TOO_LONG): (
        f"产品代码不能超过 {MAX_PRODUCT_CODE_LENGTH} 个字符"
    ),
    ("productCode", ERROR_CODE_OUT_OF_RANGE): (
        f"产品代码不能为空，且不能超过 {MAX_PRODUCT_CODE_LENGTH} 个字符"
    ),
    ("scopeProductCode", ERROR_CODE_OUT_OF_RANGE): (
        f"产品历史交易范围的产品代码不能为空，且不能超过 {MAX_PRODUCT_CODE_LENGTH} 个字符"
    ),
    ("transactionQuantity", ERROR_CODE_OUT_OF_RANGE): "交易数量必须大于 0",
    ("transactionQuantity", ERROR_CODE_NOT_INTEGER): "股票数量必须为正整数",
    ("transactionPrice", ERROR_CODE_OUT_OF_RANGE): "交易价格必须大于 0",
    ("transactionPrice", ERROR_CODE_NOT_A_NUMBER): "交易价格必须是有限十进制数值",
    ("transactionQuantity", ERROR_CODE_NOT_A_NUMBER): "交易数量必须是有限十进制数值",
    ("tradeDate", ERROR_CODE_OUT_OF_RANGE): "交易日期必须是有效的日历日期",
    ("valuationDate", ERROR_CODE_OUT_OF_RANGE): "估值日期必须是有效的日历日期",
    ("startDate", ERROR_CODE_OUT_OF_RANGE): (
        "交易日期范围必须同时提供有效的起始日期与结束日期，且起始日期不能晚于结束日期"
    ),
    ("endDate", ERROR_CODE_OUT_OF_RANGE): (
        "交易日期范围必须同时提供有效的起始日期与结束日期，且起始日期不能晚于结束日期"
    ),
    ("page", ERROR_CODE_OUT_OF_RANGE): "页码必须是大于或等于 1 的整数",
    ("pageSize", ERROR_CODE_OUT_OF_RANGE): (
        f"自定义页大小必须为 {MIN_PAGE_SIZE} 至 {MAX_PAGE_SIZE} 的整数"
    ),
}

#: query string 中的同名字段语义不同（productName/productCode 在此为**搜索值**，
#: 上限 100 字符，需求 2.20），故单独给出覆盖表，按请求来源优先匹配。
QUERY_FIELD_MESSAGES = {
    ("productName", ERROR_CODE_TOO_LONG): (
        f"产品名称搜索值不能超过 {MAX_SEARCH_VALUE_LENGTH} 个字符"
    ),
    ("productName", ERROR_CODE_OUT_OF_RANGE): (
        f"产品名称搜索值不能为空，且不能超过 {MAX_SEARCH_VALUE_LENGTH} 个字符"
    ),
    ("productCode", ERROR_CODE_TOO_LONG): (
        f"产品代码搜索值不能超过 {MAX_SEARCH_VALUE_LENGTH} 个字符"
    ),
    ("productCode", ERROR_CODE_OUT_OF_RANGE): (
        f"产品代码搜索值不能为空，且不能超过 {MAX_SEARCH_VALUE_LENGTH} 个字符"
    ),
}

#: 错误码 → 兜底句子模板（``{label}`` 由 :data:`FIELD_LABELS` 填充），
#: 保证任何未预料到的校验失败也能给出一句可展示的中文，且不泄露英文原文。
CODE_FALLBACK_MESSAGES = {
    ERROR_CODE_NOT_IN_ENUM: "{label}的取值不在预定义取值范围内，请从可选项中选择",
    ERROR_CODE_INVALID_SCALE: "{label}的小数位不符合要求",
    ERROR_CODE_TOO_LONG: "{label}的长度超过上限",
    ERROR_CODE_OUT_OF_RANGE: "{label}的取值不在允许范围内",
}

#: Pydantic 把 ``ValueError`` 包装为 ``value_error`` 时给 msg 添加的英文前缀
VALUE_ERROR_PREFIX = "Value error, "

#: 本模块自定义的四个字段级错误码全集：这些 type 的 msg 已是完整中文句子，可直接采用
CUSTOM_ERROR_CODES = frozenset(
    {
        ERROR_CODE_NOT_IN_ENUM,
        ERROR_CODE_INVALID_SCALE,
        ERROR_CODE_OUT_OF_RANGE,
        ERROR_CODE_TOO_LONG,
    }
)


def toCamelCase(name: str) -> str:
    """把 snake_case 字段名转换为 camelCase；已是 camelCase 时原样返回。

    :param name: 字段名，如 ``product_type`` 或 ``productType``。
    :returns: camelCase 字段名，如 ``productType``。
    """
    if "_" not in name:
        # 已是 camelCase（HTTP 入参按别名校验时 Pydantic 直接给出别名），不可再做 title 化
        return name
    head, *rest = name.split("_")
    return head + "".join(part[:1].upper() + part[1:] for part in rest if part)


def splitErrorLocation(loc: Sequence[object]) -> tuple[str, str]:
    """从 Pydantic 错误的 ``loc`` 中拆出请求来源与 camelCase 字段名。

    :param loc: Pydantic 错误定位元组，如 ``("body", "product_type")``、
        ``("query", "pageSize")``；模型级校验器产生的错误只含来源（如 ``("query",)``）。
    :returns: ``(来源, 字段名)``；来源不可识别时为空串，字段名缺失时为空串。
    """
    parts = list(loc)
    source = ""
    if parts and isinstance(parts[0], str) and parts[0] in REQUEST_SOURCES:
        source = str(parts.pop(0))
    # 过滤掉列表下标等非字符串定位项，取最后一个字符串作为字段名
    names = [part for part in parts if isinstance(part, str)]
    field = toCamelCase(names[-1]) if names else ""
    return source, field


def containsChinese(text: str) -> bool:
    """判断文本是否含中日韩统一表意文字，用于识别「已是中文句子」的错误消息。

    :param text: 待判断文本。
    :returns: 含至少一个汉字时为 ``True``。
    """
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def resolveErrorCode(errorType: str) -> str:
    """把 Pydantic 错误 ``type`` 映射为本模块的四个字段级错误码之一。

    :param errorType: Pydantic 错误 type，可能是本模块自定义的 ``ERROR_CODE_*``，
        也可能是内置 type（``enum`` / ``string_too_long`` / ``missing`` 等）。
    :returns: ``NOT_IN_ENUM`` / ``INVALID_SCALE`` / ``OUT_OF_RANGE`` / ``TOO_LONG`` 之一；
        未识别的 type 一律回落 ``OUT_OF_RANGE``（表示「取值不在允许范围内」）。
    """
    if errorType in CUSTOM_ERROR_CODES:
        return errorType
    return PYDANTIC_TYPE_TO_ERROR_CODE.get(errorType, ERROR_CODE_OUT_OF_RANGE)


def resolveErrorMessage(
    source: str, field: str, errorCode: str, rawMessage: str
) -> str:
    """为字段级错误挑选一句完整的中文提示语。

    优先级：本模块自定义校验器给出的中文原文 → query 专用文案 → 通用字段文案 →
    按错误码拼装的兜底文案。英文原文（如 ``Input should be 'WEALTH', 'FUND' or 'STOCK'``）
    在任何分支下都不会进入返回值，避免把英文码回显给用户。

    :param source: 请求来源（``body`` / ``query`` / ...），用于区分同名字段的不同语义。
    :param field: camelCase 字段名。
    :param errorCode: 已归一的字段级错误码。
    :param rawMessage: Pydantic 给出的原始 ``msg``。
    :returns: 可直接展示给用户的完整中文句子。
    """
    # 1) 自定义校验器（PydanticCustomError / ValueError）的 msg 本身就是中文完整句子
    message = rawMessage
    if message.startswith(VALUE_ERROR_PREFIX):
        message = message[len(VALUE_ERROR_PREFIX) :]
    if containsChinese(message):
        return message
    # 2) query string 中的搜索值等同名字段另有语义，优先使用专用文案
    if source == "query":
        queryMessage = QUERY_FIELD_MESSAGES.get((field, errorCode))
        if queryMessage:
            return queryMessage
    # 3) 通用字段文案
    fieldMessage = FIELD_MESSAGES.get((field, errorCode))
    if fieldMessage:
        return fieldMessage
    # 4) 按错误码拼装兜底文案
    label = FIELD_LABELS.get(field, FALLBACK_FIELD_LABEL)
    template = CODE_FALLBACK_MESSAGES.get(
        errorCode, CODE_FALLBACK_MESSAGES[ERROR_CODE_OUT_OF_RANGE]
    )
    return template.format(label=label)


def translateValidationError(error: Mapping[str, Any]) -> FieldErrorItem:
    """把单条 Pydantic 错误翻译为一个 :class:`FieldErrorItem`。

    :param error: ``RequestValidationError.errors()`` 中的一项，含 ``loc`` / ``msg`` / ``type``。
    :returns: 字段级错误项，``field`` 为 camelCase 字段名，``code`` 为四个常量之一，
        ``message`` 为完整中文句子（需求 1.2、3.2）。
    """
    source, field = splitErrorLocation(error.get("loc") or ())
    errorCode = resolveErrorCode(str(error.get("type", "")))
    rawMessage = str(error.get("msg", ""))
    if not field:
        # 模型级校验器（如日期范围成对性）不带字段名，按中文关键词回落到合理控件
        stripped = rawMessage
        if stripped.startswith(VALUE_ERROR_PREFIX):
            stripped = stripped[len(VALUE_ERROR_PREFIX) :]
        field = FALLBACK_FIELD_NAME
        for keyword, hintedField in MODEL_LEVEL_FIELD_HINTS:
            if keyword in stripped:
                field = hintedField
                break
    message = resolveErrorMessage(source, field, errorCode, rawMessage)
    return FieldErrorItem(field=field, code=errorCode, message=message)


def translateValidationErrors(
    errors: Iterable[Mapping[str, Any]]
) -> list[FieldErrorItem]:
    """批量翻译 Pydantic 错误，并按 ``(字段, 错误码, 文案)`` 去重。

    去重的意义：同一字段可能同时触发前置转换器与范围校验，重复提示对用户无价值。

    :param errors: ``RequestValidationError.errors()`` 的结果。
    :returns: 保持原有顺序的字段级错误项列表（需求 1.2 要求逐项指出每个无效信息项）。
    """
    items: list[FieldErrorItem] = []
    seen: set[tuple[str, str, str]] = set()
    for error in errors:
        item = translateValidationError(error)
        key = (item.field, item.code, item.message)
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
    return items


def registerLedgerExceptionHandlers(app: FastAPI) -> None:
    """在 FastAPI 应用上注册账本模块的三类异常处理器（装配点，由 ``main.py`` 调用）。

    - :class:`LedgerError` 及其子类 → 各自的 HTTP 状态码 + 统一 ``{code, msg, data}`` 信封；
    - :class:`~fastapi.exceptions.RequestValidationError` → HTTP 422 +
      ``data.fieldErrors``（camelCase 字段名、四个英文错误码、完整中文句子）；
    - :class:`~sqlalchemy.exc.IntegrityError` / :class:`~sqlalchemy.exc.OperationalError`
      → HTTP 500 + ``code: 500`` + 通用中文提示，SQL、表名与堆栈只进服务端日志。

    :param app: FastAPI 应用实例。
    :returns: 无返回值；副作用为在 ``app`` 上登记异常处理器。
    """

    @app.exception_handler(LedgerError)
    async def handleLedgerError(request: Request, exc: LedgerError) -> JSONResponse:
        """渲染业务异常为统一信封（需求 1.5、2.20、2.21、2.26、2.30）。

        :param request: 触发异常的请求，仅用于日志定位。
        :param exc: 业务异常实例。
        :returns: 带业务状态码与中文提示的 JSON 响应。
        """
        logger.info(
            "investmentLedger 业务异常：%s %s -> code=%s msg=%s",
            request.method,
            request.url.path,
            exc.code,
            exc.msg,
        )
        return JSONResponse(status_code=exc.statusCode, content=exc.toResponsePayload())

    @app.exception_handler(RequestValidationError)
    async def handleRequestValidationError(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """把请求校验失败翻译为字段级中文错误（需求 1.2、3.2）。

        :param request: 触发异常的请求，仅用于日志定位。
        :param exc: Pydantic 请求校验异常。
        :returns: HTTP 422 响应，``data.fieldErrors`` 逐项指出无效字段及中文原因。
        """
        fieldErrors = translateValidationErrors(exc.errors())
        error = LedgerValidationError(fieldErrors=fieldErrors)
        logger.info(
            "investmentLedger 参数校验失败：%s %s -> %s",
            request.method,
            request.url.path,
            [item.field for item in fieldErrors],
        )
        return JSONResponse(
            status_code=error.statusCode, content=error.toResponsePayload()
        )

    @app.exception_handler(IntegrityError)
    @app.exception_handler(OperationalError)
    async def handleDatabaseError(
        request: Request, exc: IntegrityError | OperationalError
    ) -> JSONResponse:
        """把数据库异常收敛为通用 500 响应，不外泄 SQL、表名与堆栈。

        :param request: 触发异常的请求，仅用于日志定位。
        :param exc: SQLAlchemy 完整性约束或连接/执行异常。
        :returns: HTTP 500 响应，``msg`` 为通用中文提示，``data`` 为 ``None``。
        """
        # 细节（含 SQL 与堆栈）只写日志；响应体绝不携带
        logger.exception(
            "investmentLedger 数据库异常：%s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "code": BUSINESS_CODE_INTERNAL_ERROR,
                "msg": DATABASE_ERROR_MESSAGE,
                "data": None,
            },
        )
