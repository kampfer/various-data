"""投资交易账本的自定义 SQLAlchemy 列类型。

存在意义：SQLite 没有原生的精确 ``NUMERIC`` 类型，SQLAlchemy 的 ``Numeric``
在 SQLite 方言上会退化为 ``REAL``（IEEE-754 双精度浮点），从而破坏
「交易单价恰有两位小数」（需求 1.2）与「估值单价 ≤ 999999999.99 且小数位 ≤ 2」
（需求 3.2）这类精确性约束。因此本模块提供 :class:`DecimalText`：
以定长十进制字符串把 :class:`~decimal.Decimal` 存入 ``TEXT`` 列，
读写两个方向**全程不经过 ``float``**。

既有 ``app/omo/models.py`` 同样以字符串存放金额与利率，风格一致。
"""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import String
from sqlalchemy.types import TypeDecorator

#: 金额与单价统一保留的小数位数（两位小数，需求 1.2、3.2）
DECIMAL_SCALE = 2

#: quantize 的目标指数模板：``Decimal('0.01')`` 表示保留两位小数
DECIMAL_EXPONENT = Decimal(1).scaleb(-DECIMAL_SCALE)  # == Decimal('0.01')


class DecimalText(TypeDecorator):
    """把 ``Decimal`` 以定长十进制字符串存入 ``TEXT`` 列的自定义列类型。

    - ``impl = String``：底层实际列类型，在 SQLite 上即 ``TEXT``（``VARCHAR(n)``）；
    - ``cache_ok = True``：本类型不含随实例变化的行为参数，
      允许 SQLAlchemy 缓存使用本类型的编译后语句；
    - 写库方向把 ``Decimal`` 量化为恰好两位小数的字符串（``"12.30"``），
      使同一数值在库中只有唯一字面量，字符串比较与排序结果与数值一致；
    - 读库方向以字符串直接构造 ``Decimal``，不经过 ``float``，无精度损失；
    - ``None``（SQL ``NULL``）在两个方向均原样透传，语义为「该列无值」。
    """

    impl = String  # 底层实际列类型
    cache_ok = True  # 允许语句缓存：本类型无实例级行为差异

    def process_bind_param(self, value: Decimal | None, dialect) -> str | None:
        """写库方向：``Decimal`` → 两位小数的十进制字符串；``None`` 透传。

        :param value: 待写入的十进制数值；``None`` 表示写入 SQL ``NULL``。
            允许传入 ``Decimal`` / ``int`` / ``str``（字符串按十进制字面量精确解析），
            **不接受 ``float``**：浮点入参说明调用方链路上已发生精度损失，
            与本类型的存在意义冲突，故直接报错而非静默容忍。
        :param dialect: SQLAlchemy 方言对象，本类型的行为与方言无关，未使用。
        :returns: 形如 ``"0.00"`` / ``"-1.50"`` / ``"999999999.99"`` 的字符串，或 ``None``。
        :raises TypeError: 入参为 ``float`` 或其它不支持的类型。
        """
        if value is None:
            return None
        if isinstance(value, float):
            raise TypeError(
                "DecimalText 不接受 float 入参，请改用 Decimal 以避免精度损失"
            )
        if not isinstance(value, Decimal):
            if isinstance(value, (int, str)):
                # int 与十进制字符串均可被 Decimal 精确构造，不经过 float
                value = Decimal(value)
            else:
                raise TypeError(
                    f"DecimalText 不支持的入参类型：{type(value).__name__}"
                )
        # ROUND_HALF_UP：与「四舍五入」的用户直觉一致；
        # 正常链路上入参已由 Pydantic 校验为两位小数，此处仅做规范化。
        return str(value.quantize(DECIMAL_EXPONENT, rounding=ROUND_HALF_UP))

    def process_result_value(self, value: str | None, dialect) -> Decimal | None:
        """读库方向：十进制字符串 → ``Decimal``，全程不经过 ``float``；``None`` 透传。

        :param value: 库中存放的十进制字符串；``None`` 表示 SQL ``NULL``。
        :param dialect: SQLAlchemy 方言对象，未使用。
        :returns: 与写入字面量逐位一致的 ``Decimal``（含两位小数标度），或 ``None``。
        """
        if value is None:
            return None
        if isinstance(value, Decimal):
            # 少数驱动可能已返回 Decimal，此时直接透传，避免多余转换
            return value
        return Decimal(value)
