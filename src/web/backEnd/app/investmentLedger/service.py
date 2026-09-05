"""投资交易账本的服务层用例编排。

本模块不接触 HTTP 对象，也不直接构造 SQL；数据访问、分页和输出契约分别
复用 ``crud``、``Paginator`` 与 ``schemas``。写操作的提交与异常回滚由 CRUD
在单次数据动作内完成，服务层负责业务结果判定。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Generic, Iterable, Protocol, TypeVar

from sqlalchemy.orm import Session

from app.investmentLedger import crud
from app.investmentLedger.business_days import next_working_day
from app.investmentLedger.calculators import Paginator
from app.investmentLedger.fund_performance import FundPerformanceCalculator, FundTrade
from app.investmentLedger.fund_quote import FundPerformanceData, FundQuoteService
from app.investmentLedger.constants import (
    MAX_PAGE_SIZE,
    MAX_SEARCH_VALUE_LENGTH,
    MIN_PAGE_SIZE,
    TradeDirection,
)
from app.investmentLedger.exceptions import (
    AccountDisabled,
    AccountNotFound,
    InsufficientHolding,
    InvalidDateRange,
    InvalidPageSize,
    InvalidSearchValue,
    TransactionNotFound,
)
from app.investmentLedger.models import Account
from app.investmentLedger.schemas import (
    AccountCreate,
    AccountOut,
    AccountRemarkUpdate,
    AccountStatusUpdate,
    HoldingOut,
    HoldingQuery,
    HoldingAccountOut,
    HoldingSortFieldLiteral,
    Metric,
    PageOut,
    SortOrderLiteral,
    TransactionCreate,
    TransactionOut,
    TransactionQuery,
)


class GroupableTransaction(Protocol):
    """持仓分组所需的最小交易只读接口。"""

    id: int
    product_type: str
    product_name: str
    product_code: str
    trade_date: date


TransactionRowT = TypeVar("TransactionRowT", bound=GroupableTransaction)


@dataclass(frozen=True, slots=True)
class HoldingGroup(Generic[TransactionRowT]):
    """按产品键聚合的不可变交易组，保留来源交易的原始顺序。"""

    product_type: str
    product_code: str
    product_name: str
    transactions: tuple[TransactionRowT, ...]

    @property
    def key(self) -> tuple[str, str]:
        """返回可直接传给估值批量查询的产品键。"""
        return self.product_type, self.product_code


class SortableMetric(Protocol):
    """计算指标和响应指标共同满足的数值排序接口。"""

    available: bool
    value: Decimal | str | None


class SortableHolding(Protocol):
    """持仓排序所需的最小只读接口。"""

    position: SortableMetric
    total_profit: SortableMetric


HoldingT = TypeVar("HoldingT", bound=SortableHolding)


class ServiceQueryValidator:
    """服务边界的查询校验器，把绕过契约层的无效值转换为领域异常。

    正常 HTTP 请求仍由 Pydantic schema 负责解析和校验；本校验器不修改
    schema，只保护服务被直接调用或由其它适配器调用时的领域契约。
    依赖结果集总页数的页码上界校验仍由 ``Paginator`` 完成。
    """

    @staticmethod
    def validate(query: TransactionQuery) -> None:
        """校验静态查询边界，失败时抛出需求指定的领域异常。"""
        pageSize = query.page_size
        if (
            not isinstance(pageSize, int)
            or isinstance(pageSize, bool)
            or not MIN_PAGE_SIZE <= pageSize <= MAX_PAGE_SIZE
        ):
            raise InvalidPageSize(pageSize)

        for attributeName, fieldName in (
            ("product_name", "productName"),
            ("product_code", "productCode"),
        ):
            value = getattr(query, attributeName)
            if value is not None and (
                not isinstance(value, str)
                or not 1 <= len(value) <= MAX_SEARCH_VALUE_LENGTH
            ):
                raise InvalidSearchValue(fieldName)

        startDate = query.start_date
        endDate = query.end_date
        if (startDate is None) != (endDate is None):
            raise InvalidDateRange(
                "交易日期范围必须同时提供起始日期与结束日期"
            )
        if startDate is None and endDate is None:
            return
        if not isinstance(startDate, date) or not isinstance(endDate, date):
            raise InvalidDateRange("交易日期范围必须包含有效的日历日期")
        if startDate > endDate:
            raise InvalidDateRange("交易日期范围的起始日期不能晚于结束日期")


def groupByProductKey(
    rows: Iterable[TransactionRowT],
) -> list[HoldingGroup[TransactionRowT]]:
    """按产品类型与代码分组，并保持产品及组内交易的来源顺序。"""
    groupedRows: dict[tuple[str, str], list[TransactionRowT]] = {}
    latestRows: dict[tuple[str, str], TransactionRowT] = {}

    for row in rows:
        key = (row.product_type, row.product_code)
        groupedRows.setdefault(key, []).append(row)
        latest = latestRows.get(key)
        if latest is None or (row.trade_date, row.id) > (
            latest.trade_date,
            latest.id,
        ):
            latestRows[key] = row

    return [
        HoldingGroup(
            product_type=key[0],
            product_code=key[1],
            product_name=latestRows[key].product_name,
            transactions=tuple(groupRows),
        )
        for key, groupRows in groupedRows.items()
    ]


def sortHoldings(
    holdings: Iterable[HoldingT],
    sortField: HoldingSortFieldLiteral | None,
    sortOrder: SortOrderLiteral | None,
) -> list[HoldingT]:
    """按计算指标稳定排序，不可用指标始终置于所有可用指标之后。"""
    source = list(holdings)
    if sortField is None or sortOrder is None:
        return source

    metricAttribute = {
        "position": "position",
        "totalProfit": "total_profit",
    }[sortField]
    availableItems: list[tuple[HoldingT, SortableMetric]] = []
    unavailableItems: list[HoldingT] = []
    for item in source:
        metric = getattr(item, metricAttribute)
        if metric.available:
            availableItems.append((item, metric))
        else:
            unavailableItems.append(item)

    def numericValue(entry: tuple[HoldingT, SortableMetric]) -> Decimal:
        value = entry[1].value
        if value is None:
            raise ValueError("可用指标必须包含数值")
        return value if isinstance(value, Decimal) else Decimal(value)

    orderedAvailable = sorted(
        availableItems,
        key=numericValue,
        reverse=sortOrder == "desc",
    )
    return [item for item, _metric in orderedAvailable] + unavailableItems


class AccountService:
    """账户查询、创建和备注更新用例；账户身份字段不可修改。"""

    def __init__(self, db: Session) -> None:
        """绑定请求级数据库会话。"""
        self._db = db

    def listAccounts(self) -> list[AccountOut]:
        """返回按创建时间倒序排列的全部账户。"""
        return [
            AccountOut.model_validate(account)
            for account in crud.listAccounts(self._db)
        ]

    def createAccount(self, payload: AccountCreate) -> AccountOut:
        """创建账户并返回最终落库值。"""
        account = crud.addAccount(self._db, payload)
        return AccountOut.model_validate(account)

    def updateAccountRemark(
        self, accountId: int, payload: AccountRemarkUpdate
    ) -> AccountOut:
        """仅更新账户备注；账户不存在时抛出 404 业务异常。"""
        account = crud.updateAccountRemark(
            self._db,
            accountId,
            payload.remark,
        )
        if account is None:
            raise AccountNotFound(accountId)
        return AccountOut.model_validate(account)

    def updateAccountStatus(
        self, accountId: int, payload: AccountStatusUpdate
    ) -> AccountOut:
        """更新账户启用状态；停用只限制新交易，不影响历史交易。"""
        account = crud.updateAccountStatus(
            self._db,
            accountId,
            payload.is_active,
        )
        if account is None:
            raise AccountNotFound(accountId)
        return AccountOut.model_validate(account)


class TransactionService:
    """历史交易的查询、创建与删除用例；交易创建后仍不提供整笔交易编辑。"""

    def __init__(self, db: Session) -> None:
        """绑定请求级数据库会话；会话的创建与关闭仍由调用方负责。"""
        self._db = db
        self._paginator = Paginator()

    def listTransactions(
        self, query: TransactionQuery
    ) -> PageOut[TransactionOut]:
        """查询并分页返回交易；空结果返回总数和总页数均为零。"""
        ServiceQueryValidator.validate(query)
        rows = crud.queryTransactions(self._db, query)
        pageRows, pageCount = self._paginator.slice(
            rows, page=query.page, pageSize=query.page_size
        )
        items = [TransactionOut.model_validate(row) for row in pageRows]
        return PageOut[TransactionOut](
            items=items,
            total=len(rows),
            page=query.page,
            page_size=query.page_size,
            page_count=pageCount,
        )

    def createTransaction(self, payload: TransactionCreate) -> TransactionOut:
        """创建并提交一笔不可编辑交易，返回最终落库值。

        落库前对卖出交易预演持仓：若同产品（按 ``product_type`` + ``product_code``
        聚合）的持仓数量（已落库 Σ 买入 − Σ 卖出，再扣减本次卖出数量）小于 0，
        立即抛出 :class:`InsufficientHolding`，不写入任何记录、不修改既有行，
        由路由层映射为 422 + ``fieldErrors`` 指向 ``transactionQuantity``（需求 1.3）。
        买入交易天然不会使持仓变负，直接落库。

        费用归一：``payload.fee`` 为 ``None`` 时在落库前归一为 ``Decimal(0)``，
        使出参的 ``fee`` 始终为非空十进制字符串（需求 6.2、6.4）。
        """
        if payload.account_id is not None:
            account = self._db.get(Account, payload.account_id)
            if account is None:
                raise AccountNotFound(payload.account_id)
            if not account.is_active:
                raise AccountDisabled()
        if payload.fee is None:
            payload = payload.model_copy(update={"fee": Decimal(0)})
        # 基金确认日允许由用户编辑；未提供时保留默认的下一个工作日。
        # 非基金交易不保存基金专用确认日期。
        if payload.product_type.value == "FUND":
            if payload.confirmation_date is None:
                payload = payload.model_copy(
                    update={"confirmation_date": next_working_day(payload.trade_date)}
                )
        elif payload.confirmation_date is not None:
            payload = payload.model_copy(update={"confirmation_date": None})
        if payload.direction == TradeDirection.SELL:
            currentQuantity = crud.getPositionQuantity(
                self._db,
                payload.product_type.value,
                payload.product_code,
            )
            if currentQuantity - payload.transaction_quantity < 0:
                raise InsufficientHolding()
        transaction = crud.addTransaction(self._db, payload)
        return TransactionOut.model_validate(transaction)

    def deleteTransaction(self, transactionId: int) -> None:
        """删除指定交易；目标不存在时抛出 ``TransactionNotFound``。"""
        removed = crud.removeTransaction(self._db, transactionId)
        if removed is None:
            raise TransactionNotFound(transactionId)


class HoldingService:
    """持仓和基金收益只读聚合用例。"""

    def __init__(
        self,
        db: Session,
        fundQuoteService: FundQuoteService | None = None,
        performanceCalculator: FundPerformanceCalculator | None = None,
    ) -> None:
        """绑定数据库、行情服务和可替换的纯收益计算器。"""
        self._db = db
        self._fundQuoteService = fundQuoteService
        self._performanceCalculator = performanceCalculator or FundPerformanceCalculator()

    def listHoldings(self, query: HoldingQuery) -> PageOut[HoldingOut]:
        """计算并分页返回基金、股票和理财产品的持仓指标。"""
        ServiceQueryValidator.validate(query)

        transactions = crud.getHoldingTransactions(
            self._db,
            productType=query.product_type,
            productName=query.product_name,
            productCode=query.product_code,
        )
        groups = groupByProductKey(transactions)
        keys = [group.key for group in groups]
        valuations = crud.getLatestValuations(self._db, keys)
        fundData = self._getFundPerformanceData(keys)
        marketQuotes = self._getMarketQuotes(keys, valuations, fundData)

        holdings: list[HoldingOut] = []
        for group in groups:
            quote = marketQuotes.get(group.key)
            unitNav = quote["unit_nav"] if quote is not None else None
            valuationDate = quote["valuation_date"] if quote is not None else None
            trades = [
                FundTrade.fromTransaction(transaction)
                for transaction in group.transactions
            ]
            performanceData = (
                fundData.get(group.product_code)
                if group.product_type == "FUND"
                else None
            )
            performance = self._performanceCalculator.calculate(
                trades,
                unitNav=unitNav,
                valuationDate=valuationDate,
                dividends=(performanceData.dividends if performanceData else ()),
                splits=(performanceData.splits if performanceData else ()),
            )
            if performance.shares <= Decimal("0"):
                continue
            holdings.append(self._toHoldingOut(group, performance, quote))

        orderedHoldings = sortHoldings(
            holdings,
            query.holding_sort_field,
            query.holding_sort_order,
        )
        pageRows, pageCount = Paginator().slice(
            orderedHoldings,
            page=query.page,
            pageSize=query.page_size,
        )
        return PageOut[HoldingOut](
            items=pageRows,
            total=len(orderedHoldings),
            page=query.page,
            page_size=query.page_size,
            page_count=pageCount,
        )

    def _getFundPerformanceData(
        self,
        keys: list[tuple[str, str]],
    ) -> dict[str, FundPerformanceData]:
        """读取基金详情；行情异常时返回空数据以便使用本地估值兜底。"""
        if self._fundQuoteService is None:
            return {}
        fundCodes = [
            code for productType, code in keys if productType == "FUND"
        ]
        if not fundCodes:
            return {}
        try:
            return self._fundQuoteService.getPerformanceData(fundCodes)
        except Exception:
            return {}

    @staticmethod
    def _getMarketQuotes(
        keys: list[tuple[str, str]],
        valuations: dict[tuple[str, str], object],
        fundData: dict[str, FundPerformanceData],
    ) -> dict[tuple[str, str], dict[str, object]]:
        """合并本地估值和基金详情接口的最新单位净值。"""
        quotes: dict[tuple[str, str], dict[str, object]] = {
            key: {
                "unit_nav": FundTrade.toDecimal(valuation.unit_price),
                "valuation_date": valuation.valuation_date,
            }
            for key, valuation in valuations.items()
        }
        for productType, code in keys:
            if productType != "FUND":
                continue
            data = fundData.get(code)
            if data is None or data.unit_nav is None or data.valuation_date is None:
                continue
            quotes[(productType, code)] = {
                "unit_nav": data.unit_nav,
                "valuation_date": data.valuation_date,
            }
        return quotes

    @staticmethod
    def _toHoldingAccounts(
        group: HoldingGroup,
    ) -> list[HoldingAccountOut]:
        """从产品交易组收集去重账户，并保留未关联账户记录。"""
        accountsById: dict[int | None, HoldingAccountOut] = {}
        for transaction in group.transactions:
            accountId = getattr(transaction, "account_id", None)
            if accountId in accountsById:
                continue
            accountsById[accountId] = HoldingAccountOut(
                account_id=accountId,
                account_name=getattr(transaction, "account_name", None),
                account_institution=getattr(
                    transaction, "account_institution", None
                ),
            )
        return sorted(
            accountsById.values(),
            key=lambda account: (
                account.account_id is None,
                account.account_id or 0,
            ),
        )

    @staticmethod
    def _toHoldingOut(
        group: HoldingGroup,
        performance,
        quote: dict[str, object] | None,
    ) -> HoldingOut:
        """将纯计算结果转换为现有 Metric 响应契约。"""
        missingValuation = "缺少最新估值"
        buyCostUnavailable = "累计买入金额为 0"
        position = (
            Metric.of(performance.position)
            if performance.position is not None
            else Metric.unavailable(missingValuation)
        )
        totalProfit = (
            Metric.of(performance.total_profit)
            if performance.total_profit is not None
            else Metric.unavailable(missingValuation)
        )
        totalProfitRate = (
            Metric.of(performance.total_profit_rate)
            if performance.total_profit_rate is not None
            else Metric.unavailable(
                missingValuation if quote is None else buyCostUnavailable
            )
        )
        annualizedRate = (
            Metric.of(performance.annualized_rate)
            if performance.annualized_rate is not None
            else Metric.unavailable(
                missingValuation if quote is None else buyCostUnavailable
            )
        )
        latestPrice = (
            Metric.of(quote["unit_nav"])
            if quote is not None
            else Metric.unavailable(missingValuation)
        )
        return HoldingOut(
            product_type=group.product_type,
            product_name=group.product_name,
            product_code=group.product_code,
            accounts=HoldingService._toHoldingAccounts(group),
            position=position,
            position_quantity=Metric.of(performance.shares),
            total_profit=totalProfit,
            total_profit_rate=totalProfitRate,
            annualized_rate=annualizedRate,
            latest_valuation_date=(
                quote["valuation_date"] if quote is not None else None
            ),
            latest_valuation_unit_price=latestPrice,
        )
