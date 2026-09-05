"""投资交易账本的 HTTP 路由层。

本模块只负责路径、参数绑定、服务依赖注入与统一响应信封，不包含业务规则。
交易仅支持查询、创建和删除；持仓仅提供只读查询（需求 1.4、2.4、2.23）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path
from sqlalchemy.orm import Session

import app.dependencies as dependencies
from app.investmentLedger.schemas import (
    AccountCreate,
    AccountOut,
    AccountRemarkUpdate,
    AccountStatusUpdate,
    ApiResponse,
    HoldingOut,
    HoldingQuery,
    PageOut,
    TransactionCreate,
    TransactionOut,
    TransactionQuery,
)
from app.investmentLedger.fund_quote import FundQuoteService
from app.investmentLedger.service import (
    AccountService,
    HoldingService,
    TransactionService,
)

get_db = dependencies.get_db

router = APIRouter(
    prefix="/investmentLedger",
    tags=["investmentLedger"],
)


def getTransactionService(
    db: Annotated[Session, Depends(get_db)],
) -> TransactionService:
    """构造绑定请求级数据库会话的历史交易服务。"""
    return TransactionService(db)


def getAccountService(
    db: Annotated[Session, Depends(get_db)],
) -> AccountService:
    """构造绑定请求级数据库会话的账户服务。"""
    return AccountService(db)


fund_quote_service = FundQuoteService()


def getFundQuoteService() -> FundQuoteService:
    """构造供持仓查询使用的基金最新净值服务。"""
    return fund_quote_service


def getHoldingService(
    db: Annotated[Session, Depends(get_db)],
    fundQuoteService: Annotated[FundQuoteService, Depends(getFundQuoteService)],
) -> HoldingService:
    """构造绑定请求级数据库会话的只读持仓服务。"""
    return HoldingService(db, fundQuoteService)


@router.get(
    "/accounts",
    response_model=ApiResponse[list[AccountOut]],
)
def getAccounts(
    service: Annotated[AccountService, Depends(getAccountService)],
) -> ApiResponse[list[AccountOut]]:
    """按创建时间倒序返回全部投资账户。"""
    return ApiResponse(data=service.listAccounts())


@router.post(
    "/accounts",
    response_model=ApiResponse[AccountOut],
)
def createAccount(
    payload: AccountCreate,
    service: Annotated[AccountService, Depends(getAccountService)],
) -> ApiResponse[AccountOut]:
    """创建投资账户；账户身份字段创建后不可修改。"""
    return ApiResponse(data=service.createAccount(payload))


@router.patch(
    "/accounts/{accountId}/remark",
    response_model=ApiResponse[AccountOut],
)
def updateAccountRemark(
    accountId: Annotated[int, Path(ge=1)],
    payload: AccountRemarkUpdate,
    service: Annotated[AccountService, Depends(getAccountService)],
) -> ApiResponse[AccountOut]:
    """仅更新指定账户的备注。"""
    return ApiResponse(
        data=service.updateAccountRemark(accountId, payload)
    )


@router.patch(
    "/accounts/{accountId}/status",
    response_model=ApiResponse[AccountOut],
)
def updateAccountStatus(
    accountId: Annotated[int, Path(ge=1)],
    payload: AccountStatusUpdate,
    service: Annotated[AccountService, Depends(getAccountService)],
) -> ApiResponse[AccountOut]:
    """更新账户启用状态；停用账户仍保留历史交易关联。"""
    return ApiResponse(data=service.updateAccountStatus(accountId, payload))


@router.get(
    "/transactions",
    response_model=ApiResponse[PageOut[TransactionOut]],
)
def getTransactions(
    query: Annotated[TransactionQuery, Depends()],
    service: Annotated[TransactionService, Depends(getTransactionService)],
) -> ApiResponse[PageOut[TransactionOut]]:
    """按筛选、搜索、产品范围、排序和分页条件查询历史交易。"""
    return ApiResponse(data=service.listTransactions(query))


@router.post(
    "/transactions",
    response_model=ApiResponse[TransactionOut],
)
def createTransaction(
    payload: TransactionCreate,
    service: Annotated[TransactionService, Depends(getTransactionService)],
) -> ApiResponse[TransactionOut]:
    """创建并保存一笔此后不可编辑的历史交易。"""
    return ApiResponse(data=service.createTransaction(payload))


@router.delete(
    "/transactions/{transactionId}",
    response_model=ApiResponse[None],
)
def deleteTransaction(
    transactionId: int,
    service: Annotated[TransactionService, Depends(getTransactionService)],
) -> ApiResponse[None]:
    """删除指定交易；不存在时由统一异常处理器返回错误信封。"""
    service.deleteTransaction(transactionId)
    return ApiResponse(data=None)


@router.get(
    "/holdings",
    response_model=ApiResponse[PageOut[HoldingOut]],
)
def getHoldings(
    query: Annotated[HoldingQuery, Depends()],
    service: Annotated[HoldingService, Depends(getHoldingService)],
) -> ApiResponse[PageOut[HoldingOut]]:
    """按查询条件返回只读持仓汇总，不暴露逐笔交易或写操作。"""
    return ApiResponse(data=service.listHoldings(query))
