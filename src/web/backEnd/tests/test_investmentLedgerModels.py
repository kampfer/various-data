"""投资交易账本模型层与自定义列类型的单元测试（任务 1.4）。

覆盖范围：

- :class:`~app.investmentLedger.types.DecimalText` 的往返保真：
  两位小数规范化、上限值 ``999999999.99``、``None`` 透传，
  并断言库内实际存放的是十进制字符串而非浮点（需求 3.2）；
- :class:`~app.investmentLedger.models.Valuation` 的
  ``uq_il_valuation_product_date`` 三列唯一约束在真实 SQLite 上生效（需求 3.3）。

全部用例只使用 ``conftest.py`` 提供的临时 SQLite 夹具（``tempEngine`` / ``dbSession``），
不触达 ``various_data.db`` 与 ``various_data_dev.db``。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.investmentLedger.models import (
    DECIMAL_TEXT_LENGTH,
    Base,
    Transaction,
    Valuation,
)
from app.investmentLedger.types import DecimalText

#: 需求 3.2 规定的估值单价上限，作为 DecimalText 的边界取值
MAX_VALUATION_PRICE = Decimal("999999999.99")


class ProbeBase(DeclarativeBase):
    """仅测试使用的声明式基类，与业务 ``Base`` 隔离，避免污染真实建表元数据。"""

    pass


class NullableDecimalProbe(ProbeBase):
    """探针表：提供一个**可空**的 ``DecimalText`` 列以验证 ``None`` 往返透传。

    业务表的金额列均为 NOT NULL，无法在真实表上验证 ``None`` 语义，
    故以本探针表在同一个临时 SQLite 上做真实读写往返。
    """

    __tablename__ = "tmp_decimal_text_probe"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    #: 可空金额列：写入 ``None`` 即 SQL ``NULL``，读回仍应为 ``None``
    amount: Mapped[Decimal | None] = mapped_column(
        DecimalText(DECIMAL_TEXT_LENGTH), nullable=True
    )


@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session) -> Iterator[Session]:
    """在临时引擎上建好账本表与探针表，返回可直接读写的会话。"""
    Base.metadata.create_all(bind=tempEngine)
    ProbeBase.metadata.create_all(bind=tempEngine)
    yield dbSession


def buildTransaction(unitPrice: Decimal) -> Transaction:
    """构造一笔用于往返测试的交易记录，仅 ``unit_price`` 随参数变化。"""
    return Transaction(
        product_type="FUND",
        product_name="测试基金",
        product_code="000001",
        unit_price=unitPrice,
        quantity=100,
        direction="BUY",
        trade_date=date(2024, 1, 2),
    )


class TestDecimalTextRoundTrip:
    """``DecimalText`` 的读写往返保真。"""

    @pytest.mark.parametrize(
        ("inputValue", "expectedText"),
        [
            (Decimal("12.30"), "12.30"),  # 尾随 0 必须保留，字面量唯一
            (Decimal("12.3"), "12.30"),   # 不足两位补齐为两位（需求 1.2）
            (Decimal("1"), "1.00"),       # 整数同样规范化为两位小数
            (Decimal("0.01"), "0.01"),    # 最小正单价
            (MAX_VALUATION_PRICE, "999999999.99"),  # 上限值（需求 3.2）
        ],
    )
    def testTwoDecimalScaleIsPreservedThroughDatabase(
        self,
        ledgerSession: Session,
        inputValue: Decimal,
        expectedText: str,
    ) -> None:
        """写入的 ``Decimal`` 读回后数值与标度都不变，且库内是十进制字符串。"""
        transaction = buildTransaction(inputValue)
        ledgerSession.add(transaction)
        ledgerSession.commit()
        transactionId = transaction.id

        # 清空身份映射，强制从数据库重新读取，确保走 process_result_value
        ledgerSession.expunge_all()
        loaded = ledgerSession.get(Transaction, transactionId)

        assert loaded is not None
        assert isinstance(loaded.unit_price, Decimal)
        # 数值相等 + 字面量逐位相等（后者可捕获标度丢失，如 12.3 与 12.30）
        assert loaded.unit_price == Decimal(expectedText)
        assert str(loaded.unit_price) == expectedText

        # 直查原始列值：证明存放的是字符串而非 SQLite REAL（浮点）
        rawValue = ledgerSession.execute(
            text("SELECT unit_price FROM il_transaction WHERE id = :id"),
            {"id": transactionId},
        ).scalar_one()
        assert rawValue == expectedText
        assert isinstance(rawValue, str)

    def testUpperBoundValuationPriceRoundTripsExactly(
        self, ledgerSession: Session
    ) -> None:
        """估值单价上限 999999999.99 往返后不丢失任何一位（需求 3.2）。"""
        valuation = Valuation(
            product_type="STOCK",
            product_code="600519",
            valuation_date=date(2024, 3, 31),
            unit_price=MAX_VALUATION_PRICE,
        )
        ledgerSession.add(valuation)
        ledgerSession.commit()
        valuationId = valuation.id

        ledgerSession.expunge_all()
        loaded = ledgerSession.get(Valuation, valuationId)

        assert loaded is not None
        assert loaded.unit_price == MAX_VALUATION_PRICE
        assert str(loaded.unit_price) == "999999999.99"

    def testNoneIsPassedThroughInBothDirections(
        self, ledgerSession: Session
    ) -> None:
        """``None`` 写入即 SQL ``NULL``，读回仍为 ``None``，不被替换为 0。"""
        probe = NullableDecimalProbe(amount=None)
        ledgerSession.add(probe)
        ledgerSession.commit()
        probeId = probe.id

        ledgerSession.expunge_all()
        loaded = ledgerSession.get(NullableDecimalProbe, probeId)

        assert loaded is not None
        assert loaded.amount is None

        rawValue = ledgerSession.execute(
            text("SELECT amount FROM tmp_decimal_text_probe WHERE id = :id"),
            {"id": probeId},
        ).scalar_one()
        assert rawValue is None

    def testFloatInputIsRejected(self) -> None:
        """``float`` 入参直接报错，避免精度损失被静默接受。"""
        columnType = DecimalText(DECIMAL_TEXT_LENGTH)
        with pytest.raises(TypeError):
            columnType.process_bind_param(0.1, None)


class TestValuationUniqueConstraint:
    """``uq_il_valuation_product_date`` 三列唯一约束（需求 3.3）。"""

    def testDuplicateProductTypeCodeAndDateIsRejected(
        self, ledgerSession: Session
    ) -> None:
        """产品类型、产品代码、估值日期三列全同的第二行必须被数据库拒绝。"""
        ledgerSession.add(
            Valuation(
                product_type="FUND",
                product_code="000001",
                valuation_date=date(2024, 5, 20),
                unit_price=Decimal("1.23"),
            )
        )
        ledgerSession.commit()

        ledgerSession.add(
            Valuation(
                product_type="FUND",
                product_code="000001",
                valuation_date=date(2024, 5, 20),
                unit_price=Decimal("4.56"),
            )
        )
        with pytest.raises(IntegrityError):
            ledgerSession.commit()
        ledgerSession.rollback()

        remaining = ledgerSession.execute(
            text("SELECT COUNT(*) FROM il_valuation")
        ).scalar_one()
        assert remaining == 1

    @pytest.mark.parametrize(
        ("productType", "productCode", "valuationDate"),
        [
            ("STOCK", "000001", date(2024, 5, 20)),  # 仅产品类型不同
            ("FUND", "000002", date(2024, 5, 20)),   # 仅产品代码不同
            ("FUND", "000001", date(2024, 5, 21)),   # 仅估值日期不同
        ],
    )
    def testRowsDifferingInAnyKeyColumnAreAllowed(
        self,
        ledgerSession: Session,
        productType: str,
        productCode: str,
        valuationDate: date,
    ) -> None:
        """三列中任意一列不同即为不同的估值记录，应允许共存。"""
        ledgerSession.add(
            Valuation(
                product_type="FUND",
                product_code="000001",
                valuation_date=date(2024, 5, 20),
                unit_price=Decimal("1.23"),
            )
        )
        ledgerSession.commit()

        ledgerSession.add(
            Valuation(
                product_type=productType,
                product_code=productCode,
                valuation_date=valuationDate,
                unit_price=Decimal("4.56"),
            )
        )
        ledgerSession.commit()

        total = ledgerSession.execute(
            text("SELECT COUNT(*) FROM il_valuation")
        ).scalar_one()
        assert total == 2
