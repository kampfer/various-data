"""TransactionService 的用例级单元测试（任务 6.1）。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Iterator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.investmentLedger.calculators import (
    Metric as CalculationMetric,
    ProductPerformance,
)
from app.investmentLedger.exceptions import (
    InsufficientHolding,
    PageOutOfRange,
    TransactionNotFound,
)
from app.investmentLedger.models import Base, Transaction, Valuation
from app.investmentLedger.schemas import (
    ERROR_CODE_INSUFFICIENT_HOLDING,
    TransactionCreate,
    TransactionQuery,
)
from app.investmentLedger.service import (
    OverviewService,
    TransactionService,
    groupByProductKey,
    sortHoldings,
)
from app.investmentLedger.valuation_ingest.protocol import StandardValuation
from app.investmentLedger.valuation_ingest.repository import ValuationRepository


@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session) -> Iterator[Session]:
    """创建临时账本表并提供请求级会话。"""
    Base.metadata.create_all(bind=tempEngine)
    yield dbSession


def buildPayload(
    code: str = "F-001",
    direction: str = "BUY",
    quantity: int = 10,
) -> TransactionCreate:
    """构造已通过契约校验的交易创建参数。

    :param code: 产品代码，默认 ``F-001``；不同产品需用不同 code 隔离持仓。
    :param direction: 交易方向英文码，默认 ``BUY``；卖出传 ``SELL``。
    :param quantity: 交易数量，默认 10。
    """
    return TransactionCreate(
        product_type="FUND",
        product_name="成长基金",
        product_code=code,
        unit_price="1.25",
        quantity=quantity,
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


class TestHoldingGroupingAndSorting:
    """覆盖持仓分组、展示名选择和稳定数值排序（任务 6.2）。"""

    @staticmethod
    def transaction(
        transactionId: int,
        productType: str,
        productCode: str,
        productName: str,
        tradeDate: date,
    ) -> Transaction:
        """构造无需落库的完整交易模型，供纯分组逻辑使用。"""
        return Transaction(
            id=transactionId,
            product_type=productType,
            product_name=productName,
            product_code=productCode,
            unit_price=Decimal("1.00"),
            quantity=1,
            direction="BUY",
            trade_date=tradeDate,
        )

    @staticmethod
    def performance(position: str | None, totalProfit: str | None) -> ProductPerformance:
        """复用计算层值对象构造可排序持仓，None 表示指标不可用。"""
        unavailable = CalculationMetric.unavailable("缺少最新估值")
        return ProductPerformance(
            position_quantity=CalculationMetric.of(1),
            position=(CalculationMetric.of(Decimal(position)) if position is not None else unavailable),
            cumulative_buy_amount=Decimal("1.00"),
            cumulative_sell_amount=Decimal("0.00"),
            total_profit=(CalculationMetric.of(Decimal(totalProfit)) if totalProfit is not None else unavailable),
            total_profit_rate=CalculationMetric.of(0),
            annualized_rate=CalculationMetric.of(0),
        )

    def testGroupPreservesFirstAppearanceAndSelectsLatestDisplayName(self) -> None:
        """产品顺序取首次出现，名称取日期最大且同日 id 最大的交易。"""
        rows = [
            self.transaction(3, "FUND", "A", "A旧名", date(2024, 1, 2)),
            self.transaction(4, "STOCK", "B", "B名称", date(2024, 1, 3)),
            self.transaction(8, "FUND", "A", "A最新名", date(2024, 1, 5)),
            self.transaction(9, "FUND", "A", "A较早同名", date(2024, 1, 4)),
            self.transaction(7, "FUND", "A", "A同日较小id", date(2024, 1, 5)),
        ]

        groups = groupByProductKey(rows)

        assert [group.key for group in groups] == [("FUND", "A"), ("STOCK", "B")]
        assert groups[0].product_name == "A最新名"
        assert [row.id for row in groups[0].transactions] == [3, 8, 9, 7]
        assert groups[1].product_name == "B名称"

    @pytest.mark.parametrize(
        ("sortField", "sortOrder", "expectedIndexes"),
        [
            ("position", "asc", [1, 0, 2, 3]),
            ("position", "desc", [0, 2, 1, 3]),
            ("totalProfit", "asc", [1, 0, 2, 3]),
            ("totalProfit", "desc", [0, 2, 1, 3]),
        ],
    )
    def testSortIsNumericStableAndAlwaysPlacesUnavailableLast(
        self,
        sortField: str,
        sortOrder: str,
        expectedIndexes: list[int],
    ) -> None:
        """升降序均按 Decimal 数值排列，等值稳定且不可用项恒在末尾。"""
        holdings = [
            self.performance("10", "100"),
            self.performance("2", "20"),
            self.performance("10.0", "100.00"),
            self.performance(None, None),
        ]

        actual = sortHoldings(holdings, sortField, sortOrder)

        assert actual == [holdings[index] for index in expectedIndexes]

    def testMissingSortSelectionKeepsSourceOrder(self) -> None:
        """未完整选择数值排序时保持分组产生的来源顺序。"""
        holdings = [self.performance("3", "30"), self.performance("1", "10")]

        assert sortHoldings(holdings, None, "asc") == holdings
        assert sortHoldings(holdings, "position", None) == holdings


class TestHoldingService:
    """覆盖 HoldingService 的只读六步流水线与全结果集组合统计。"""

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
                unit_price=unitPrice,
                quantity=quantity,
                direction=direction,
                trade_date=tradeDate,
            )
        )

    @staticmethod
    def addValuation(
        session: Session,
        productType: str,
        productCode: str,
        valuationDate: date,
        unitPrice: str,
    ) -> None:
        """通过内部标准化值对象和唯一摄取仓储写入测试估值。"""
        ValuationRepository(session).ingestBatch([
            StandardValuation(
                product_type=productType,
                product_code=productCode,
                valuation_date=valuationDate,
                unit_price=Decimal(unitPrice),
                source_id="legacy",
                collected_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            )
        ])

    def seedPortfolio(self, session: Session) -> None:
        """写入两个已估值产品和一个无估值产品。"""
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
        self.addValuation(session, "FUND", "A", date(2024, 1, 2), "12.00")
        self.addValuation(session, "FUND", "A", date(2024, 1, 5), "20.00")
        self.addValuation(session, "STOCK", "B", date(2024, 1, 4), "40.00")

    def testListRunsGroupingLatestValuationSortingAndPagination(
        self, ledgerSession: Session
    ) -> None:
        """列表使用最新估值计算，按收益排序，并只返回请求页。"""
        from app.investmentLedger.schemas import HoldingQuery
        from app.investmentLedger.service import HoldingService

        self.seedPortfolio(ledgerSession)
        result = HoldingService(ledgerSession).listHoldings(
            HoldingQuery(
                holding_sort_field="totalProfit",
                holding_sort_order="desc",
                page=1,
                page_size=2,
            )
        )

        assert result.total == 3
        assert result.page_count == 2
        assert [item.product_code for item in result.items] == ["A", "B"]
        assert result.items[0].product_name == "甲基金新名"
        assert result.items[0].position.value == "160.00"
        assert result.items[0].position_quantity.value == "8"
        assert result.items[0].total_profit.value == "90.00"
        assert result.items[1].position.value == "200.00"
        assert result.items[1].total_profit.value == "50.00"

        lastPage = HoldingService(ledgerSession).listHoldings(
            HoldingQuery(
                holding_sort_field="totalProfit",
                holding_sort_order="desc",
                page=2,
                page_size=2,
            )
        )
        assert [item.product_code for item in lastPage.items] == ["C"]
        assert lastPage.items[0].position.available is False
        assert lastPage.items[0].position.value is None
        assert lastPage.items[0].position.unavailable_reason == "缺少最新估值"

    def testPortfolioStatisticsIgnorePaginationAndSorting(
        self, ledgerSession: Session
    ) -> None:
        """组合统计覆盖筛选后的全部产品，不受列表页和排序参数影响。"""
        from app.investmentLedger.schemas import HoldingQuery
        from app.investmentLedger.service import HoldingService

        self.seedPortfolio(ledgerSession)
        query = HoldingQuery(
            trade_date_order="desc",
            holding_sort_field="position",
            holding_sort_order="asc",
            page=3,
            page_size=1,
        )

        statistics = HoldingService(ledgerSession).getPortfolioStatistics(query)

        assert statistics.total_position.value == "360.00"
        assert statistics.total_profit.value == "140.00"
        assert statistics.total_profit_rate.value == "0.56"
        assert statistics.total_annualized_rate.available is True

    def testEmptyFilteredResultReturnsEmptyPageAndZeroPortfolioSums(
        self, ledgerSession: Session
    ) -> None:
        """无匹配记录时列表为零项，组合求和为零且比率显式不可用。"""
        from app.investmentLedger.schemas import HoldingQuery
        from app.investmentLedger.service import HoldingService

        self.seedPortfolio(ledgerSession)
        query = HoldingQuery(product_code="NOT-FOUND", page=7, page_size=10)
        service = HoldingService(ledgerSession)

        page = service.listHoldings(query)
        statistics = service.getPortfolioStatistics(query)

        assert page.items == []
        assert page.total == 0
        assert page.page_count == 0
        assert statistics.total_position.value == "0"
        assert statistics.total_profit.value == "0"
        assert statistics.total_profit_rate.available is False
        assert statistics.total_annualized_rate.available is False

    def testServiceExposesNoWriteMethods(self, ledgerSession: Session) -> None:
        """持仓服务仅提供列表和组合统计，不暴露写操作。"""
        from app.investmentLedger.service import HoldingService

        service = HoldingService(ledgerSession)

        for methodName in (
            "createHolding",
            "updateHolding",
            "deleteHolding",
            "createTransaction",
            "updateTransaction",
            "deleteTransaction",
        ):
            assert not hasattr(service, methodName)


class TestOverviewService:
    """覆盖交易存在性到默认模块的唯一决策规则（任务 6.6）。"""

    def testEmptyLedgerResolvesHistory(self, ledgerSession: Session) -> None:
        """没有任何已保存交易时默认进入历史交易记录模块。"""
        assert OverviewService(ledgerSession).resolveInitialModule() == "history"

    def testNonEmptyLedgerResolvesHoldings(self, ledgerSession: Session) -> None:
        """存在至少一笔已保存交易时默认进入持仓模块。"""
        TransactionService(ledgerSession).createTransaction(buildPayload())

        assert OverviewService(ledgerSession).resolveInitialModule() == "holdings"
