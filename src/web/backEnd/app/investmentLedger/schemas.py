"""投资交易账本的 Pydantic v2 请求与响应契约。

设计要点（与设计文档「后端设计 · 3. Pydantic 模型（schemas.py）」逐条对应）：

- 字段内部一律使用 snake_case，经 :class:`LedgerSchema` 的
  ``alias_generator=to_camel`` 对外输出 camelCase，与前端
  ``src/web/frontEnd/src/api/types.ts`` 中的镜像声明逐字段一致；
- ``populate_by_name=True`` 使模型既能用字段名（后端内部构造）也能用别名
  （HTTP 入参）赋值；``from_attributes=True`` 使出参可直接由 ORM 对象转换；
- **金额与比率一律以十进制字符串序列化**（见 :data:`AmountString` /
  :data:`DecimalString`），彻底规避 JSON 浮点误差（需求 2.6、3.9）；
- 枚举字段一律使用英文码（``WEALTH`` / ``FUND`` / ``STOCK``、``BUY`` / ``SELL``），
  中文只出现在错误提示句子与前端展示映射层；
- 字段校验失败时抛 :class:`~pydantic_core.PydanticCustomError`，其 ``type`` 取
  本模块的 ``ERROR_CODE_*`` 常量，供 ``exceptions.py`` 的
  ``RequestValidationError`` 处理器直接翻译为 ``FieldErrorItem.code``（需求 1.2、3.2）。
"""

from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)
from pydantic.alias_generators import to_camel
from pydantic_core import PydanticCustomError

from app.investmentLedger.constants import (
    DEFAULT_PAGE_SIZE,
    MAX_PAGE_SIZE,
    MAX_PRODUCT_CODE_LENGTH,
    MAX_PRODUCT_NAME_LENGTH,
    MAX_SEARCH_VALUE_LENGTH,
    MAX_VALUATION_UNIT_PRICE,
    MIN_PAGE_SIZE,
    ProductType,
    TradeDirection,
)
from app.investmentLedger.types import DECIMAL_EXPONENT, DECIMAL_SCALE

# ---------------------------------------------------------------------------
# 字段级错误码：与 exceptions.py 的 RequestValidationError 翻译表共用（需求 1.2、3.2）
# ---------------------------------------------------------------------------

#: 取值不属于预定义枚举（如产品类型传入中文字面量或小写码）
ERROR_CODE_NOT_IN_ENUM = "NOT_IN_ENUM"

#: 小数位数不符合约定（交易单价须恰两位、估值单价须不超过两位）
ERROR_CODE_INVALID_SCALE = "INVALID_SCALE"

#: 数值或日期范围越界（含页码/页大小越界、起始日期晚于结束日期）
ERROR_CODE_OUT_OF_RANGE = "OUT_OF_RANGE"

#: 文本长度超过上限（产品名称 100、产品代码 32、搜索值 100）
ERROR_CODE_TOO_LONG = "TOO_LONG"

# ---------------------------------------------------------------------------
# 领域字面量类型：取值与前端 domain/ledger/constants.ts 的联合类型逐字符一致
# ---------------------------------------------------------------------------

#: 排序方向：asc=从小到大，desc=从大到小（需求 2.15、2.19）
SortOrderLiteral = Literal["asc", "desc"]

#: 持仓条目可排序的数值字段：position=持仓（市值），totalProfit=总收益（需求 2.19）
HoldingSortFieldLiteral = Literal["position", "totalProfit"]

#: 界面模块标识：history=历史交易记录模块，holdings=持仓模块（需求 2.1、2.2、2.3）
LedgerModuleLiteral = Literal["history", "holdings"]

#: 泛型负载类型变量：用于 ApiResponse[T] 与 PageOut[T]
T = TypeVar("T")

#: 估值单价上限，由字符串常量精确构造为 Decimal（需求 3.2）
MAX_VALUATION_UNIT_PRICE_DECIMAL = Decimal(MAX_VALUATION_UNIT_PRICE)


def _toDecimal(value: object, errorCode: str, message: str) -> Decimal:
    """把入参精确转换为 ``Decimal``，全程不经过 ``float``。

    :param value: 待转换的值，允许 ``Decimal`` / ``int`` / 十进制字符串；
        ``float`` 一律拒绝——浮点入参说明调用链上已发生精度损失，
        与「金额以十进制精确表达」的设计前提冲突。
    :param errorCode: 转换失败时使用的字段级错误码（``ERROR_CODE_*``）。
    :param message: 转换失败时展示给用户的完整中文句子。
    :returns: 与字面量逐位一致的 ``Decimal``。
    :raises PydanticCustomError: 类型不受支持、字面量非法或数值非有限（NaN / Infinity）。
    """
    if isinstance(value, Decimal):
        parsed = value
    elif isinstance(value, bool) or isinstance(value, float):
        # bool 是 int 的子类，但作为金额毫无意义；float 见上文说明
        raise PydanticCustomError(errorCode, message)
    elif isinstance(value, (int, str)):
        try:
            parsed = Decimal(value)
        except (InvalidOperation, ValueError):
            raise PydanticCustomError(errorCode, message)
    else:
        raise PydanticCustomError(errorCode, message)
    if not parsed.is_finite():
        raise PydanticCustomError(errorCode, message)
    return parsed


def _coerceAmountString(value: object) -> object:
    """出参金额的前置转换器：``Decimal`` / ``int`` / 字符串 → 恰两位小数的十进制字符串。

    金额（交易单价、估值单价）在库中以两位小数存放，出参保持同一标度，
    使前端拿到的字符串可直接展示且与库内字面量一致。

    :param value: ORM 或计算层给出的数值；``None`` 原样透传（由字段的可空性决定是否合法）。
    :returns: 形如 ``"12.30"`` / ``"999999999.99"`` 的字符串，或 ``None``。
    :raises PydanticCustomError: 值无法被精确解释为十进制数值。
    """
    if value is None:
        return None
    parsed = _toDecimal(value, ERROR_CODE_INVALID_SCALE, "金额必须是十进制数值")
    return str(parsed.quantize(DECIMAL_EXPONENT, rounding=ROUND_HALF_UP))


def _coerceDecimalString(value: object) -> object:
    """出参比率/高精度数值的前置转换器：``Decimal`` / ``int`` / 字符串 → 十进制字符串。

    与 :func:`_coerceAmountString` 的差别在于**不做两位小数量化**：
    收益率与年化收益率需要保留计算层给出的高精度（需求 3.7、3.8）。

    :param value: 计算层给出的数值；``None`` 原样透传（表示指标不可用，需求 3.9）。
    :returns: 不含指数记号的十进制字符串（如 ``"0.1234567890"``），或 ``None``。
    :raises PydanticCustomError: 值无法被精确解释为十进制数值。
    """
    if value is None:
        return None
    parsed = _toDecimal(value, ERROR_CODE_INVALID_SCALE, "指标值必须是十进制数值")
    # format(..., 'f') 强制定点表示，避免出现 1E-8 这类前端难以直接展示的科学记数法
    return format(parsed, "f")


#: 金额字符串：出参用，恰两位小数（需求 1.2、3.2）
AmountString = Annotated[str, BeforeValidator(_coerceAmountString)]

#: 十进制字符串：出参用，保留计算层精度，适用于收益率与年化收益率（需求 3.7、3.8）
DecimalString = Annotated[str, BeforeValidator(_coerceDecimalString)]


class LedgerSchema(BaseModel):
    """本模块所有 Pydantic 模型的公共基类，集中承载统一的模型配置。

    - ``alias_generator=to_camel``：内部 snake_case 字段对外以 camelCase 出现，
      与前端 ``api/types.ts`` 的字段名逐字符一致；
    - ``populate_by_name=True``：既可用字段名（后端内部构造）也可用别名（HTTP 入参）赋值；
    - ``from_attributes=True``：出参模型可直接由 SQLAlchemy ORM 对象转换。
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ---------------------------------------------------------------------------
# 通用信封与错误项
# ---------------------------------------------------------------------------


class ApiResponse(LedgerSchema, Generic[T]):
    """统一响应信封，与前端既有 ``{code, msg, data}`` 约定一致（镜像 ``ApiEnvelope<T>``）。

    :ivar code: 业务状态码，200 表示成功；失败码由 ``exceptions.py`` 的映射表给出。
    :ivar msg: 中文提示语，失败时可由前端直接展示给用户。
    :ivar data: 业务负载；失败或无返回值的接口（如删除交易）为 ``None``。
    """

    #: 业务状态码，200 成功（需求 1.2、2.30 的错误码在 exceptions.py 统一映射）
    code: int = 200

    #: 中文提示语，成功时固定为 ok，失败时为可直接展示的完整中文句子
    msg: str = "ok"

    #: 业务负载；无返回值的接口为 None
    data: T | None = None


class FieldErrorItem(LedgerSchema):
    """字段级错误项，前端据此把错误定位到具体表单项并保留已填值（需求 1.2、3.2）。"""

    #: camelCase 字段名，与前端表单项名称一致，如 unitPrice
    field: str

    #: 英文错误码，取值见本模块 ERROR_CODE_* 常量（NOT_IN_ENUM / INVALID_SCALE / OUT_OF_RANGE / TOO_LONG）
    code: str

    #: 中文原因，完整句子，可直接渲染给用户
    message: str


class Metric(LedgerSchema):
    """统计指标包装：把「可用性」与「值」显式分开，避免用 0 冒充不可用（需求 3.9）。

    不变量：``available`` 为 ``False`` 时 ``value`` 必为 ``None`` 且必须给出中文
    ``unavailable_reason``；``available`` 为 ``True`` 时 ``value`` 必须有值且
    ``unavailable_reason`` 必为 ``None``。该不变量由 :meth:`checkAvailability` 强制。
    """

    #: 是否满足该指标计算公式的定义域（需求 3.9）
    available: bool

    #: 指标值，十进制字符串（金额两位小数、比率保留计算精度）；不可用时必为 None
    value: DecimalString | None = None

    #: 中文不可用原因（如「缺少最新估值」「累计买入金额为 0」）；可用时必为 None
    unavailable_reason: str | None = None

    @model_validator(mode="after")
    def checkAvailability(self) -> "Metric":
        """校验可用性与取值的一致性，杜绝「不可用却带值」或「可用却缺值」的中间态。

        :returns: 校验通过的自身实例。
        :raises ValueError: 违反可用性不变量（需求 3.9）。
        """
        if self.available:
            if self.value is None:
                raise ValueError("指标可用时必须给出指标值")
            if self.unavailable_reason is not None:
                raise ValueError("指标可用时不应给出不可用原因")
        else:
            if self.value is not None:
                raise ValueError("指标不可用时指标值必须为空，不得以数值替代")
            if not self.unavailable_reason:
                raise ValueError("指标不可用时必须给出中文不可用原因")
        return self

    @classmethod
    def of(cls, value: Decimal | int | str) -> "Metric":
        """构造可用指标。

        :param value: 指标数值，须为 ``Decimal`` / ``int`` / 十进制字符串（禁止 ``float``）。
        :returns: ``available=True`` 且带值的指标。
        """
        return cls(available=True, value=value)

    @classmethod
    def unavailable(cls, reason: str) -> "Metric":
        """构造不可用指标（需求 3.9）。

        :param reason: 中文不可用原因，如「缺少最新估值」，非空。
        :returns: ``available=False``、``value=None`` 且带中文原因的指标。
        """
        return cls(available=False, value=None, unavailable_reason=reason)


# ---------------------------------------------------------------------------
# 交易记录：入参、出参与查询条件
# ---------------------------------------------------------------------------


class TransactionCreate(LedgerSchema):
    """创建交易的入参（需求 1.1、1.2）。

    非法枚举值（中文字面量「理财」、小写码 ``wealth``）由 Pydantic 的枚举校验直接拒绝；
    长度、正数、两位小数等约束由下方字段校验器给出中文原因。
    """

    #: 产品类型英文码，取值 ∈ {WEALTH, FUND, STOCK}（需求 1.1、1.2）
    product_type: ProductType

    #: 产品名称，1..100 字符（需求 1.2）
    product_name: str = Field(min_length=1, max_length=MAX_PRODUCT_NAME_LENGTH)

    #: 产品代码，1..32 字符（需求 1.2）；与产品类型共同构成产品键（需求 2.5）
    product_code: str = Field(min_length=1, max_length=MAX_PRODUCT_CODE_LENGTH)

    #: 交易单价，> 0 且小数位恰为 2（需求 1.2）；以 Decimal 承载，禁止 float 入参
    unit_price: Decimal

    #: 交易数量，> 0 的整数（需求 1.2）
    quantity: int = Field(gt=0)

    #: 交易方向英文码，取值 ∈ {BUY, SELL}（需求 1.1、1.2）
    direction: TradeDirection

    #: 交易日期，有效公历日期（需求 1.2）；非法日历日期（如 2 月 30 日）在解析阶段即失败
    trade_date: date

    @field_validator("unit_price", mode="before")
    @classmethod
    def parseUnitPrice(cls, value: object) -> Decimal:
        """把交易单价精确解析为 ``Decimal``，拒绝 ``float`` 与非十进制字面量。

        :param value: 原始入参（``Decimal`` / ``int`` / 十进制字符串）。
        :returns: 解析后的 ``Decimal``，标度保持原字面量。
        :raises PydanticCustomError: 无法精确解析为十进制数值（需求 1.2）。
        """
        return _toDecimal(
            value,
            ERROR_CODE_INVALID_SCALE,
            "交易单价必须是大于 0 且恰有两位小数的十进制数值",
        )

    @field_validator("unit_price")
    @classmethod
    def checkUnitPrice(cls, value: Decimal) -> Decimal:
        """校验交易单价 > 0 且小数位**恰为** 2（需求 1.2）。

        :param value: 已解析的交易单价。
        :returns: 校验通过的交易单价。
        :raises PydanticCustomError: 非正数，或小数位不等于 2（如 ``10`` / ``10.5`` / ``10.123``）。
        """
        if value <= 0:
            raise PydanticCustomError(
                ERROR_CODE_OUT_OF_RANGE, "交易单价必须大于 0"
            )
        if value.as_tuple().exponent != -DECIMAL_SCALE:
            raise PydanticCustomError(
                ERROR_CODE_INVALID_SCALE, "交易单价必须恰有两位小数，例如 12.30"
            )
        return value


class TransactionOut(LedgerSchema):
    """交易出参（历史交易表格的行数据，需求 2.12）。"""

    #: 交易主键，仅用于删除定位；前端不渲染，也不提供按其查询的接口（需求 2.23）
    id: int

    #: 产品类型英文码，前端经展示映射转中文
    product_type: ProductType

    #: 产品名称
    product_name: str

    #: 产品代码
    product_code: str

    #: 交易单价，十进制字符串，恰两位小数（序列化为字符串以规避 JSON 浮点误差）
    unit_price: AmountString

    #: 交易数量，> 0 的整数
    quantity: int

    #: 交易方向英文码，前端经展示映射转中文
    direction: TradeDirection

    #: 交易日期，序列化为 YYYY-MM-DD
    trade_date: date


class TransactionQuery(LedgerSchema):
    """历史交易查询入参；以 ``Annotated[TransactionQuery, Depends()]`` 从 query string 注入。

    所有筛选与搜索字段的 ``None`` 均表示「未启用该条件」，多个已启用条件按逻辑与组合
    （需求 2.16、2.17、2.18）。
    """

    #: 产品类型筛选；None=未启用（需求 2.16）
    product_type: ProductType | None = None

    #: 交易方向筛选；None=未启用（需求 2.16）
    direction: TradeDirection | None = None

    #: 交易日期闭区间下界；须与 end_date 成对出现（需求 2.16、2.21）
    start_date: date | None = None

    #: 交易日期闭区间上界；须 >= start_date（需求 2.16、2.21）
    end_date: date | None = None

    #: 产品名称包含匹配搜索值，长度 1..100；None=未启用（需求 2.17、2.18、2.20）
    product_name: str | None = Field(
        None, min_length=1, max_length=MAX_SEARCH_VALUE_LENGTH
    )

    #: 产品代码包含匹配搜索值，长度 1..100；None=未启用（需求 2.17、2.18、2.20）
    product_code: str | None = Field(
        None, min_length=1, max_length=MAX_SEARCH_VALUE_LENGTH
    )

    #: 交易日期排序方向；None=未启用日期排序，此时按 id 升序保证顺序稳定（需求 2.15）
    trade_date_order: SortOrderLiteral | None = None

    #: 产品历史交易范围的产品类型码；与 scope_product_code 同时为 None 或同时非 None（需求 2.9、2.10）
    scope_product_type: ProductType | None = None

    #: 产品历史交易范围的产品代码，1..32 字符（需求 2.9、2.10）
    scope_product_code: str | None = Field(
        None, min_length=1, max_length=MAX_PRODUCT_CODE_LENGTH
    )

    #: 请求页码，1 起（需求 2.28、2.30）
    page: int = Field(1, ge=1)

    #: 页大小，闭区间 1..100（需求 2.24、2.25、2.26）
    page_size: int = Field(DEFAULT_PAGE_SIZE, ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE)

    @model_validator(mode="after")
    def checkDateRange(self) -> "TransactionQuery":
        """校验交易日期范围成对出现且起始日期不晚于结束日期（需求 2.21）。

        :returns: 校验通过的自身实例。
        :raises PydanticCustomError: 缺少起始或结束日期，或起始日期晚于结束日期。
        """
        if (self.start_date is None) != (self.end_date is None):
            raise PydanticCustomError(
                ERROR_CODE_OUT_OF_RANGE,
                "交易日期范围必须同时提供起始日期与结束日期",
            )
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.start_date > self.end_date
        ):
            raise PydanticCustomError(
                ERROR_CODE_OUT_OF_RANGE,
                "交易日期范围的起始日期不能晚于结束日期",
            )
        return self

    @model_validator(mode="after")
    def checkProductScope(self) -> "TransactionQuery":
        """校验产品历史交易范围的两个字段成对出现（需求 2.9、2.10）。

        :returns: 校验通过的自身实例。
        :raises PydanticCustomError: 仅提供产品类型或仅提供产品代码。
        """
        if (self.scope_product_type is None) != (self.scope_product_code is None):
            raise PydanticCustomError(
                ERROR_CODE_OUT_OF_RANGE,
                "产品历史交易范围必须同时提供产品类型与产品代码",
            )
        return self


class HoldingQuery(TransactionQuery):
    """持仓查询入参：复用全部交易筛选/搜索条件，追加持仓条目的数值排序（需求 2.19）。"""

    #: 排序字段：position（持仓）或 totalProfit（总收益）；None=按首次出现顺序（需求 2.15、2.19）
    holding_sort_field: HoldingSortFieldLiteral | None = None

    #: 排序方向；仅在 holding_sort_field 非 None 时生效（需求 2.19）
    holding_sort_order: SortOrderLiteral | None = None


class HoldingOut(LedgerSchema):
    """持仓条目汇总出参（需求 2.6 的 7 列数据源）。

    每个指标均为 :class:`Metric`：不满足定义域时以 ``available=False`` 显式标记，
    绝不以 0 替代（需求 3.9）。
    """

    #: 产品键之一：产品类型英文码（需求 2.5）
    product_type: ProductType

    #: 展示名称：取条目内「交易日期最大、同日 id 最大」那笔交易的产品名称（需求 2.5）
    product_name: str

    #: 产品键之二：产品代码（需求 2.5）
    product_code: str

    #: 持仓（= 持仓市值 = 持仓数量 × 最新估值单价），需求 2.6、3.5
    position: Metric

    #: 持仓数量（累计买入数量 − 累计卖出数量），需求 3.5；不作为独立列渲染
    position_quantity: Metric

    #: 总收益 = 累计卖出金额 + 持仓市值 − 累计买入金额（需求 2.6、3.6）
    total_profit: Metric

    #: 总收益率 = 总收益 ÷ 累计买入金额（需求 2.6、3.7）
    total_profit_rate: Metric

    #: 年化收益率 = (1 + 总收益率)^(365 / 持有天数) − 1（需求 2.6、3.8）
    annualized_rate: Metric


class PageOut(LedgerSchema, Generic[T]):
    """通用分页出参；T 为行数据类型（需求 2.24、2.28、2.29、2.31）。"""

    #: 当前页行数据；最后一页可少于 page_size（需求 2.29），结果集为空时为空列表（需求 2.22）
    items: list[T]

    #: 结果集总条数（分页前）
    total: int = Field(ge=0)

    #: 当前页码，1 起（需求 2.28）
    page: int = Field(ge=1)

    #: 当前页大小，闭区间 1..100（需求 2.25）
    page_size: int = Field(ge=MIN_PAGE_SIZE, le=MAX_PAGE_SIZE)

    #: 总页数 = ceil(total / page_size)；为 0 表示当前结果没有可浏览的页（需求 2.31）
    page_count: int = Field(ge=0)


class PortfolioStatisticsOut(LedgerSchema):
    """投资组合统计出参：只聚合具有最新估值的产品（需求 3.10-3.12）。"""

    #: 总持仓 = Σ 各产品持仓市值（需求 3.10）
    total_position: Metric

    #: 总收益 = Σ 各产品收益（需求 3.10）
    total_profit: Metric

    #: 总收益率 = 总收益 ÷ Σ 累计买入金额（需求 3.11）
    total_profit_rate: Metric

    #: 总年化收益率 = Σ(年化收益率 × 累计买入金额) ÷ Σ 累计买入金额（需求 3.12）
    total_annualized_rate: Metric


# ---------------------------------------------------------------------------
# 估值记录与初始模块
# ---------------------------------------------------------------------------


class ValuationUpsert(LedgerSchema):
    """估值写入入参（需求 3.1、3.2）；同键重复提交由 upsert 覆盖（需求 3.3）。"""

    #: 产品类型英文码，取值 ∈ {WEALTH, FUND, STOCK}（需求 3.1、3.2）
    product_type: ProductType

    #: 产品代码，1..32 字符（需求 3.2）
    product_code: str = Field(min_length=1, max_length=MAX_PRODUCT_CODE_LENGTH)

    #: 估值日期，有效公历日期（需求 3.2）；同一产品下取最大者为最新估值（需求 3.4）
    valuation_date: date

    #: 估值单价，0 ≤ v ≤ 999999999.99 且小数位 ≤ 2（需求 3.2）
    unit_price: Decimal

    @field_validator("unit_price", mode="before")
    @classmethod
    def parseUnitPrice(cls, value: object) -> Decimal:
        """把估值单价精确解析为 ``Decimal``，拒绝 ``float`` 与非十进制字面量。

        :param value: 原始入参（``Decimal`` / ``int`` / 十进制字符串）。
        :returns: 解析后的 ``Decimal``，标度保持原字面量。
        :raises PydanticCustomError: 无法精确解析为十进制数值（需求 3.2）。
        """
        return _toDecimal(
            value,
            ERROR_CODE_INVALID_SCALE,
            "估值单价必须是 0 至 999999999.99 之间、小数位不超过两位的十进制数值",
        )

    @field_validator("unit_price")
    @classmethod
    def checkUnitPrice(cls, value: Decimal) -> Decimal:
        """校验估值单价落在 0..999999999.99 闭区间内且小数位 ≤ 2（需求 3.2）。

        :param value: 已解析的估值单价。
        :returns: 校验通过的估值单价。
        :raises PydanticCustomError: 小于 0、超过上限，或小数位超过 2 位。
        """
        if value < 0 or value > MAX_VALUATION_UNIT_PRICE_DECIMAL:
            raise PydanticCustomError(
                ERROR_CODE_OUT_OF_RANGE,
                f"估值单价必须在 0 至 {MAX_VALUATION_UNIT_PRICE} 之间",
            )
        exponent = value.as_tuple().exponent
        if isinstance(exponent, int) and exponent < -DECIMAL_SCALE:
            raise PydanticCustomError(
                ERROR_CODE_INVALID_SCALE, "估值单价的小数位不能超过两位"
            )
        return value


class ValuationOut(LedgerSchema):
    """估值记录出参（``PUT /valuations`` 的回显，需求 3.3）。"""

    #: 产品类型英文码
    product_type: ProductType

    #: 产品代码
    product_code: str

    #: 估值日期，序列化为 YYYY-MM-DD
    valuation_date: date

    #: 估值单价，十进制字符串，两位小数（需求 3.2）
    unit_price: AmountString


class InitialModuleOut(LedgerSchema):
    """初始模块决策出参（需求 2.2、2.3）。"""

    #: 应默认打开的模块：无任何已保存交易时为 history，否则为 holdings
    module: LedgerModuleLiteral
