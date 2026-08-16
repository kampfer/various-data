"""投资交易账本的精确十进制 TEXT 列类型。"""

from decimal import Decimal, InvalidOperation

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator

#: 估值独立规则使用的两位标度常量；交易字段不使用它们。
DECIMAL_SCALE = 2
DECIMAL_EXPONENT = Decimal("0.01")


class DecimalText(TypeDecorator):
    """以不量化的十进制文本存储 ``Decimal``，不经过 ``float`` 或舍入。

    交易价格和交易数量使用该类型以保留用户输入的任意有效精度；估值调用方
    仍由自身 schema/normalizer 决定独立的精度规则。
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: Decimal | None, dialect) -> str | None:
        """将有限 ``Decimal`` 原样转换为定点十进制文本。"""
        if value is None:
            return None
        if isinstance(value, bool) or isinstance(value, float):
            raise TypeError("DecimalText 不接受 bool 或 float 入参")
        if not isinstance(value, Decimal):
            if not isinstance(value, (int, str)):
                raise TypeError(f"DecimalText 不支持的入参类型：{type(value).__name__}")
            try:
                value = Decimal(value)
            except (InvalidOperation, ValueError) as error:
                raise TypeError("DecimalText 入参必须是十进制数值") from error
        if not value.is_finite():
            raise TypeError("DecimalText 不接受非有限十进制数值")
        return format(value, "f")

    def process_result_value(self, value: str | None, dialect) -> Decimal | None:
        """将数据库十进制文本精确还原为 ``Decimal``。"""
        if value is None:
            return None
        return value if isinstance(value, Decimal) else Decimal(value)
