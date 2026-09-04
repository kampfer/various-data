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
from app.investmentLedger.calculators import Paginator, Paginator2
from app.investmentLedger.constants import (
    MAX_PAGE_SIZE,
    MAX_SEARCH_VALUE_LENGTH,
    MIN_PAGE_SIZE,
    TradeDirection,
)
from app.investmentLedger.exceptions import (
    InsufficientHolding,
    InvalidDateRange,
    InvalidPageSize,
    InvalidSearchValue,
    AccountNotFound,
    TransactionNotFound,
)
from app.investmentLedger.models import Account
from app.investmentLedger.schemas import (
    AccountCreate,
    AccountOut,
    AccountRemarkUpdate,
    HoldingOut,
    HoldingQuery,
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


class TransactionService:
    """历史交易的查询、创建与删除用例；刻意不提供更新方法（需求 1.4）。"""

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
        if payload.account_id is not None and self._db.get(Account, payload.account_id) is None:
            raise AccountNotFound(payload.account_id)
        if payload.fee is None:
            payload = payload.model_copy(update={"fee": Decimal(0)})
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
    """持仓只读聚合用例；刻意不提供任何创建、修改或删除方法。"""

    def __init__(self, db: Session, fundQuoteService) -> None:
        """绑定请求级会话并装配无状态计算组件。"""
        self._db = db
        self._fundQuoteService = fundQuoteService

    def listHoldings(self, query: HoldingQuery) -> PageOut[HoldingOut]:
        """分页查询持仓。"""

        ServiceQueryValidator.validate(query)

        limit, offset = Paginator2.get_limit_offset(
            query.page, query.page_size
        )

        holdings, total = crud.get_current_holdings(
            self._db,
            product_type=query.product_type,
            productName=query.product_name,
            productCode=query.product_code,
            limit=limit,
            offset=offset,
        )

        pageCount = Paginator2.get_page_count(total, query.page_size)

        latestNav = self._fundQuoteService.getLatestNav(
            [row.product_code for row in holdings]
        )

        items = []
        for row in holdings:
            latestNavRow = next(
                (item for item in latestNav if item["fund_code"] == row.product_code), None,
            )

            items.append(
                HoldingOut(
                    product_type=row.product_type,
                    product_name=row.product_name,
                    product_code=row.product_code,
                    position=Metric.of(value=row.net_quantity * Decimal(latestNavRow.get("unit_nav", 0))),
                    position_quantity=Metric.of(value=row.net_quantity),
                    total_profit=Metric.of(value=0),
                    total_profit_rate=Metric.of(value=0),
                    annualized_rate=Metric.of(value=0),
                    latest_valuation_date=date.fromisoformat(latestNavRow.get("update_date")),
                    latest_valuation_unit_price=Metric.of(value=latestNavRow.get("unit_nav")),
                )
            )

        return PageOut[HoldingOut](
            items=items,
            total=total,
            page=query.page,
            page_size=query.page_size,
            page_count=pageCount,
        )
