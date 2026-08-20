"""投资交易账本的 HTTP 路由层。

本模块只负责路径、参数绑定、服务依赖注入与统一响应信封，不包含业务规则。
交易仅支持查询、创建和删除；持仓仅提供只读查询（需求 1.4、2.4、2.23）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

import app.dependencies as dependencies
from app.investmentLedger.schemas import (
    ApiResponse,
    FundSearchOut,
    FundSearchQuery,
    HoldingOut,
    HoldingQuery,
    InitialModuleOut,
    PageOut,
    PortfolioStatisticsOut,
    TransactionCreate,
    TransactionOut,
    TransactionQuery,
)
from app.investmentLedger.fund_search import FundSearchService
from app.investmentLedger.service import (
    HoldingService,
    OverviewService,
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


def getHoldingService(
    db: Annotated[Session, Depends(get_db)],
) -> HoldingService:
    """构造绑定请求级数据库会话的只读持仓服务。"""
    return HoldingService(db)


def getOverviewService(
    db: Annotated[Session, Depends(get_db)],
) -> OverviewService:
    """构造绑定请求级数据库会话的初始模块决策服务。"""
    return OverviewService(db)


def getFundSearchService() -> FundSearchService:
    """构造无状态的基金搜索代理服务（不依赖数据库会话，需求 5.2）。"""
    return FundSearchService()


@router.get(
    "/initialModule",
    response_model=ApiResponse[InitialModuleOut],
)
def getInitialModule(
    service: Annotated[OverviewService, Depends(getOverviewService)],
) -> ApiResponse[InitialModuleOut]:
    """根据是否存在历史交易返回首次进入时应打开的模块。"""
    return ApiResponse(
        data=InitialModuleOut(module=service.resolveInitialModule())
    )


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


@router.get(
    "/portfolioStatistics",
    response_model=ApiResponse[PortfolioStatisticsOut],
)
def getPortfolioStatistics(
    query: Annotated[HoldingQuery, Depends()],
    service: Annotated[HoldingService, Depends(getHoldingService)],
) -> ApiResponse[PortfolioStatisticsOut]:
    """按完整筛选结果集返回投资组合统计，并忽略分页与排序。"""
    return ApiResponse(data=service.getPortfolioStatistics(query))


@router.get(
    "/fundSearch",
    response_model=ApiResponse[list[FundSearchOut]],
)
def searchFunds(
    query: Annotated[FundSearchQuery, Depends()],
    service: Annotated[FundSearchService, Depends(getFundSearchService)],
) -> ApiResponse[list[FundSearchOut]]:
    """转发用户输入至第三方基金搜索接口并返回标准格式结果。

    只接受一个参数 ``keyword``（用户输入内容）；第三方失败/超时/非法数据
    收敛为空列表并记录服务端日志，不向用户抛出异常（需求 5.2、5.6、5.7）。
    本接口只读，不写账本数据库、不写估值记录，结果不落库。
    """
    return ApiResponse(data=service.searchFunds(query.keyword))
