"""投资交易账本的持久化模型（SQLAlchemy 2.0 ``Mapped`` 风格）。

设计要点（与设计文档「Data Models」一节逐条对应）：

- 模块内自带 ``Base(DeclarativeBase)``，其 ``metadata`` 由 ``app/models.py`` 的
  ``initAppModels()`` 统一 ``create_all``，与 ``sinaFinanceNews`` / ``omo`` 两个既有模块惯例一致；
- 金额与单价列一律使用 :class:`~app.investmentLedger.types.DecimalText`，
  以十进制字符串精确存放 ``Decimal``，规避 SQLite 无精确 ``NUMERIC`` 导致的浮点误差；
- 交易记录**只有 INSERT 与 DELETE 两条路径，不存在 UPDATE**（需求 1.4），
  因此本表不设置任何 ``onupdate`` 行为；
- 枚举列存放的是**英文码**（``WEALTH`` / ``FUND`` / ``STOCK``、``BUY`` / ``SELL``，
  取值全集见 ``constants.py``），中文文案只出现在前端展示层，
  故 ``String(16)`` 足以容纳最长码 ``WEALTH`` 并留有余量。
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from sqlalchemy import Date, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.investmentLedger.types import DecimalText

# 复用型主键注解（PEP 593 Annotated）：自增整型主键，
# 避免每张表重复书写 mapped_column 参数；写法与 sinaFinanceNews/models.py 一致。
# https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html#step-five-make-use-of-pep-593-annotated-to-package-common-directives-into-types
primaryKey = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]

#: 枚举码列的声明长度：最长码 ``WEALTH`` 为 6 字符，留足余量便于后续扩展
ENUM_CODE_LENGTH = 16

#: 产品名称列长度上限，与 ``constants.MAX_PRODUCT_NAME_LENGTH`` 对应（需求 1.2）
PRODUCT_NAME_LENGTH = 100

#: 产品代码列长度上限，与 ``constants.MAX_PRODUCT_CODE_LENGTH`` 对应（需求 1.2、3.2）
PRODUCT_CODE_LENGTH = 32



class Base(DeclarativeBase):
    """本模块独立的声明式基类。

    与既有模块保持同构：每个业务模块各自持有一个 ``Base``，
    其 ``metadata`` 在 ``app/models.py`` 的 ``initAppModels()`` 中
    以 ``create_all(bind=engine)`` 建表，互不干扰。
    """

    pass


class Transaction(Base):
    """交易记录表：一行一笔买卖，**只有 INSERT 与 DELETE 两条路径，没有 UPDATE**（需求 1.4）。"""

    __tablename__ = "il_transaction"

    #: 主键：仅用于删除定位，既不展示也不提供按其查询的接口（需求 2.23）
    id: Mapped[primaryKey]

    #: 产品类型英文码，取值 ∈ {WEALTH, FUND, STOCK}（需求 1.1、1.2）；
    #: 单列索引支撑按产品类型筛选（需求 2.16）
    product_type: Mapped[str] = mapped_column(String(ENUM_CODE_LENGTH), index=True)

    #: 产品名称，1..100 字符（需求 1.2）；随每笔不可变交易保存，
    #: 因此允许同一产品在不同时间使用不同名称（展示名取最新一笔，需求 2.5）
    product_name: Mapped[str] = mapped_column(String(PRODUCT_NAME_LENGTH))

    #: 产品代码，1..32 字符（需求 1.2）；与 ``product_type`` 共同构成产品键（需求 2.5）；
    #: 单列索引支撑产品代码的包含匹配搜索（需求 2.17、2.18）
    product_code: Mapped[str] = mapped_column(String(PRODUCT_CODE_LENGTH), index=True)

    #: 交易价格，有限且大于 0 的 Decimal；以无长度、无标度的 TEXT 精确存放（需求 1.2、1.3）。
    transaction_price: Mapped[Decimal] = mapped_column(DecimalText())

    #: 交易数量，理财/基金为有限正 Decimal，股票为正整数；仍以无标度 TEXT 精确存放。
    transaction_quantity: Mapped[Decimal] = mapped_column(DecimalText())

    #: 交易费用，非负有限 Decimal；可空，未提供时由服务层归一为 ``Decimal(0)`` 落库（需求 6.2、6.3、6.4）。
    #: 以无标度 TEXT 精确存放，与交易价格/数量同口径，避免浮点误差。
    fee: Mapped[Decimal | None] = mapped_column(DecimalText(), nullable=True)

    #: 交易方向英文码，取值 ∈ {BUY, SELL}（需求 1.1、1.2）；
    #: 单列索引支撑按交易方向筛选（需求 2.16）
    direction: Mapped[str] = mapped_column(String(ENUM_CODE_LENGTH), index=True)

    #: 交易日期（有效公历日期）；建索引以支撑闭区间筛选与排序（需求 2.16、2.15）
    trade_date: Mapped[date] = mapped_column(Date, index=True)

    #: 写入时间：同一交易日期内多笔记录的稳定次序依据（需求 2.15）；
    #: 交易不可编辑，故不设置 onupdate（需求 1.4）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        # 复合索引：支撑按产品键分组与「产品历史交易范围」查询（需求 2.5、2.10）
        Index("ix_il_transaction_product", "product_type", "product_code"),
    )


class Valuation(Base):
    """标准估值结果表：账本只读，估值摄取服务负责受控写入（需求 3.1）。

    同一产品、估值日期和来源只允许一条记录；来源字段使同日不同来源可以并存，
    由后续估值读取/摄取服务按核心来源优先级决定生效记录（需求 3.1、3.17）。
    """

    __tablename__ = "il_valuation"

    #: 主键：仅内部使用，不对外暴露（需求 2.23）
    id: Mapped[primaryKey]

    #: 产品类型英文码，取值 ∈ {WEALTH, FUND, STOCK}（需求 3.1、3.2）
    product_type: Mapped[str] = mapped_column(String(ENUM_CODE_LENGTH))

    #: 产品代码，1..32 字符，与产品类型共同构成产品键（需求 3.2）
    product_code: Mapped[str] = mapped_column(String(PRODUCT_CODE_LENGTH))

    #: 估值日期（有效公历日期）；统计读取产品日期最大的标准化记录（需求 3.1）
    valuation_date: Mapped[date] = mapped_column(Date)

    #: 估值单价；由标准化采集结果提供，使用 DecimalText 保持十进制精度（需求 3.2）
    unit_price: Mapped[Decimal] = mapped_column(DecimalText())

    #: 外部数据源稳定标识，如 eastmoney；必须由正式摄取流程显式提供（需求 3.1、3.11、3.17）。
    source_id: Mapped[str] = mapped_column(String(64))

    #: 采集完成时间；必须由正式摄取流程显式提供，不以写库时间替代（需求 3.11、3.12）。
    collected_at: Mapped[datetime] = mapped_column(DateTime)

    #: 原始 URL、响应记录 ID 或内容摘要；不保存敏感请求头，可为空（需求 3.11、3.12）
    source_reference: Mapped[str | None] = mapped_column(String(512), nullable=True)

    #: 原始响应哈希；用于审计、重放和批次去重，可为空（需求 3.11、3.17）
    raw_payload_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)

    #: 核心受控写入时间；不是用户覆盖时间，不配置公开更新行为（需求 3.13）
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    __table_args__ = (
        # 同一产品、同一估值日期、同一来源至多一条；支持受控摄取幂等键（需求 3.1、3.17）
        UniqueConstraint(
            "product_type",
            "product_code",
            "valuation_date",
            "source_id",
            name="uq_il_valuation_product_date_source",
        ),
        # 支持按产品读取估值日期最大的候选记录（需求 3.1）
        Index(
            "ix_il_valuation_product_date",
            "product_type",
            "product_code",
            "valuation_date",
        ),
    )
