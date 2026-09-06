"""TransactionService 的用例级单元测试（任务 6.1）。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Iterator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.investmentLedger.exceptions import (
    InsufficientHolding,
    PageOutOfRange,
    TransactionNotFound,
)
from app.investmentLedger.models import Base, Transaction
from app.investmentLedger.schemas import (
    ERROR_CODE_INSUFFICIENT_HOLDING,
    TransactionCreate,
    TransactionQuery,
)
from app.investmentLedger.service import TransactionService


@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session) -> Iterator[Session]:
    """创建临时账本表并提供请求级会话。"""
    Base.metadata.create_all(bind=tempEngine)
    yield dbSession


def buildPayload(
    code: str = "F-001",
    direction: str = "BUY",
    quantity: int = 10,
    fee: Decimal | str | None = None,
) -> TransactionCreate:
    """构造已通过契约校验的交易创建参数。

    :param code: 产品代码，默认 ``F-001``；不同产品需用不同 code 隔离持仓。
    :param direction: 交易方向英文码，默认 ``BUY``；卖出传 ``SELL``。
    :param quantity: 交易数量，默认 10。
    :param fee: 交易费用，默认 ``None``；用于验证服务层归一为 ``Decimal(0)``（需求 6.2）。
    """
    return TransactionCreate(
        product_type="FUND",
        product_name="成长基金",
        product_code=code,
        transaction_price="1.25",
        transaction_quantity=quantity,
        fee=fee,
        direction=direction,
        trade_date=date(2024, 2, 29),
    )


class TestTransactionService:
    """覆盖交易服务的分页、创建、删除及只增删边界。"""

    def testEmptyResultHasZeroTotalAndPageCount(
        self, ledgerSession: Session
    ) -> None:
        """空结果没有有效页，但任意已校验正页码都不会触发越界。"""
        result = TransactionService(ledgerSession).listTransactions(
            TransactionQuery(page=7, page_size=10)
        )

        assert result.items == []
        assert result.total == 0
        assert result.page == 7
        assert result.page_size == 10
        assert result.page_count == 0

    def testCreateAndListReturnSchemaPageInStableSlices(
        self, ledgerSession: Session
    ) -> None:
        """创建会落库，列表按 Paginator 切片并返回 PageOut。"""
        service = TransactionService(ledgerSession)
        created = [service.createTransaction(buildPayload(f"F-{index:03d}")) for index in range(1, 4)]

        firstPage = service.listTransactions(TransactionQuery(page=1, page_size=2))
        secondPage = service.listTransactions(TransactionQuery(page=2, page_size=2))

        assert firstPage.total == secondPage.total == 3
        assert firstPage.page_count == secondPage.page_count == 2
        assert [item.id for item in firstPage.items] == [created[0].id, created[1].id]
        assert [item.id for item in secondPage.items] == [created[2].id]
        assert ledgerSession.get(Transaction, created[0].id) is not None

    def testNonEmptyOutOfRangePagePropagatesBusinessError(
        self, ledgerSession: Session
    ) -> None:
        """非空结果的越界页码由 Paginator 统一拒绝。"""
        service = TransactionService(ledgerSession)
        service.createTransaction(buildPayload())

        with pytest.raises(PageOutOfRange):
            service.listTransactions(TransactionQuery(page=2, page_size=10))

    def testDeleteRemovesOnlyTargetAndMissingRaises(
        self, ledgerSession: Session
    ) -> None:
        """删除目标记录不影响其他记录，不存在时转换为领域异常。"""
        service = TransactionService(ledgerSession)
        target = service.createTransaction(buildPayload("F-TARGET"))
        survivor = service.createTransaction(buildPayload("F-SURVIVOR"))

        assert service.deleteTransaction(target.id) is None
        assert ledgerSession.get(Transaction, target.id) is None
        assert ledgerSession.get(Transaction, survivor.id) is not None

        with pytest.raises(TransactionNotFound) as caught:
            service.deleteTransaction(target.id)

        assert caught.value.transactionId == target.id

    def testServiceIntentionallyExposesNoUpdateMethod(
        self, ledgerSession: Session
    ) -> None:
        """历史交易不可编辑，服务对象不暴露更新入口。"""
        service = TransactionService(ledgerSession)

        assert not hasattr(service, "updateTransaction")

    def testSellWithinHoldingPersistsAndReducesPosition(
        self, ledgerSession: Session
    ) -> None:
        """卖出数量不超过已有持仓时正常落库，持仓等量扣减。"""
        service = TransactionService(ledgerSession)
        service.createTransaction(buildPayload(quantity=10))
        service.createTransaction(buildPayload(direction="SELL", quantity=3))

        result = service.listTransactions(TransactionQuery(page=1, page_size=10))
        assert len(result.items) == 2
        assert ledgerSession.query(Transaction).count() == 2

    def testSellEqualHoldingSucceedsWithZeroPosition(
        self, ledgerSession: Session
    ) -> None:
        """卖出数量等于已有持仓时持仓归零，不视为持仓不足。"""
        service = TransactionService(ledgerSession)
        service.createTransaction(buildPayload(quantity=10))
        service.createTransaction(buildPayload(direction="SELL", quantity=10))

        assert ledgerSession.query(Transaction).count() == 2

    def testSellBeyondHoldingRaisesInsufficientHoldingWithoutWrite(
        self, ledgerSession: Session
    ) -> None:
        """卖出数量超过已有持仓时抛出 InsufficientHolding，且不写入任何记录。"""
        service = TransactionService(ledgerSession)
        service.createTransaction(buildPayload(quantity=10))

        with pytest.raises(InsufficientHolding):
            service.createTransaction(buildPayload(direction="SELL", quantity=11))

        assert ledgerSession.query(Transaction).count() == 1
        result = service.listTransactions(TransactionQuery(page=1, page_size=10))
        assert [item.direction for item in result.items] == ["BUY"]

    def testSellWithoutPriorBuyRaisesInsufficientHolding(
        self, ledgerSession: Session
    ) -> None:
        """空库直接卖出第一笔时持仓不足，拦截且不写入。"""
        service = TransactionService(ledgerSession)

        with pytest.raises(InsufficientHolding):
            service.createTransaction(buildPayload(direction="SELL", quantity=1))

        assert ledgerSession.query(Transaction).count() == 0

    def testInsufficientHoldingExposesFieldErrorsOnTransactionQuantity(
        self, ledgerSession: Session
    ) -> None:
        """InsufficientHolding 的 fieldErrors 指向 transactionQuantity 字段。"""
        service = TransactionService(ledgerSession)
        service.createTransaction(buildPayload(quantity=10))

        with pytest.raises(InsufficientHolding) as caught:
            service.createTransaction(buildPayload(direction="SELL", quantity=11))

        fieldErrors = caught.value.fieldErrors
        assert len(fieldErrors) == 1
        assert fieldErrors[0].field == "transactionQuantity"
        assert fieldErrors[0].code == ERROR_CODE_INSUFFICIENT_HOLDING
        assert fieldErrors[0].message == "卖出数量超过当前持仓"

    def testSellOfOneProductDoesNotBlockAnother(
        self, ledgerSession: Session
    ) -> None:
        """A 产品的卖出拦截不影响 B 产品的买入或卖出落库。"""
        service = TransactionService(ledgerSession)
        service.createTransaction(buildPayload(code="F-A", quantity=5))

        with pytest.raises(InsufficientHolding):
            service.createTransaction(
                buildPayload(code="F-A", direction="SELL", quantity=6)
            )

        service.createTransaction(buildPayload(code="F-B", quantity=8))
        service.createTransaction(buildPayload(code="F-B", direction="SELL", quantity=8))

        assert ledgerSession.query(Transaction).count() == 3

    def testCreateTransactionNormalizesNoneFeeToZero(self, ledgerSession: Session) -> None:
        """未提供 fee 时服务层归一为 Decimal(0) 落库，出参为 '0'（需求 6.2、6.4）。"""
        service = TransactionService(ledgerSession)
        result = service.createTransaction(buildPayload())

        assert result.fee == "0"
        persisted = ledgerSession.get(Transaction, result.id)
        assert persisted is not None and persisted.fee == Decimal("0")

    def testCreateTransactionPersistsProvidedFeeAsCanonicalString(
        self, ledgerSession: Session
    ) -> None:
        """提供 fee 时按原字面量精度落库，出参为十进制字符串（需求 6.4、6.5）。"""
        service = TransactionService(ledgerSession)
        result = service.createTransaction(buildPayload(fee="5.00"))

        assert result.fee == "5.00"
        persisted = ledgerSession.get(Transaction, result.id)
        assert persisted is not None and persisted.fee == Decimal("5.00")


class TestFundHoldingService:
    """覆盖 FundHoldingService 的基金持仓聚合流水线。"""

    @staticmethod
    def addTransaction(
        session: Session,
        productType: str,
        productName: str,
        productCode: str,
        unitPrice: str,
        quantity: int,
        direction: str,
        tradeDate: date,
    ) -> None:
        """通过真实交易服务写入测试交易，避免绕过契约与持久化层。"""
        TransactionService(session).createTransaction(
            TransactionCreate(
                product_type=productType,
                product_name=productName,
                product_code=productCode,
                transaction_price=unitPrice,
                transaction_quantity=quantity,
                direction=direction,
                trade_date=tradeDate,
            )
        )

    def seedPortfolio(self, session: Session) -> None:
        """写入基金、股票和理财交易，验证服务只聚合基金。"""
        self.addTransaction(
            session, "FUND", "甲基金旧名", "A", "10.00", 10, "BUY", date(2024, 1, 1)
        )
        self.addTransaction(
            session, "FUND", "甲基金新名", "A", "15.00", 2, "SELL", date(2024, 1, 3)
        )
        self.addTransaction(
            session, "STOCK", "乙股票", "B", "30.00", 5, "BUY", date(2024, 1, 2)
        )
        self.addTransaction(
            session, "WEALTH", "丙理财", "C", "50.00", 1, "BUY", date(2024, 1, 4)
        )

    def testListReturnsOnlyFundHoldings(
        self, ledgerSession: Session
    ) -> None:
        """基金持仓服务固定过滤股票和理财，并使用基金最新净值。"""
        from app.investmentLedger.fund_quote import FundPerformanceData
        from app.investmentLedger.schemas import HoldingQuery
        from app.investmentLedger.service import FundHoldingService

        class StubFundQuoteService:
            """为服务测试提供稳定基金净值，不访问第三方行情接口。"""

            @staticmethod
            def getPerformanceData(
                fundCodes: list[str],
            ) -> dict[str, FundPerformanceData]:
                return {
                    code: FundPerformanceData(
                        unit_nav=Decimal("20.00"),
                        valuation_date=date(2024, 1, 5),
                    )
                    for code in fundCodes
                }

        self.seedPortfolio(ledgerSession)
        result = FundHoldingService(
            ledgerSession,
            fundQuoteService=StubFundQuoteService(),
        ).listHoldings(
            HoldingQuery(
                holding_sort_field="totalProfit",
                holding_sort_order="desc",
                page=1,
                page_size=2,
            )
        )

        assert result.total == 1
        assert result.page_count == 1
        assert [item.product_code for item in result.items] == ["A"]
        assert all(item.product_type == "FUND" for item in result.items)
        assert result.items[0].product_name == "甲基金新名"
        assert result.items[0].position.value == "160.00"
        assert result.items[0].position_quantity.value == "8"
        assert result.items[0].total_profit.value == "90.00"

    def testServiceExposesNoWriteMethods(self, ledgerSession: Session) -> None:
        """基金持仓服务仅提供列表和组合统计，不暴露写操作。"""
        from app.investmentLedger.service import FundHoldingService

        service = FundHoldingService(ledgerSession)

        for methodName in (
            "createHolding",
            "updateHolding",
            "deleteHolding",
            "createTransaction",
            "updateTransaction",
            "deleteTransaction",
        ):
            assert not hasattr(service, methodName)
