"""公开账本路由边界：估值写入只能存在于内部摄取包。"""

from app.investmentLedger.router import router


def testPublicLedgerRoutesExposeOnlyTransactionWritesAndLedgerReads() -> None:
    """公开路由只允许交易创建/删除及账本读取，不提供估值或交易更新入口。"""
    routes = {
        (route.path, method)
        for route in router.routes
        for method in route.methods or set()
    }
    assert routes == {
        ("/investmentLedger/initialModule", "GET"),
        ("/investmentLedger/transactions", "GET"),
        ("/investmentLedger/transactions", "POST"),
        ("/investmentLedger/transactions/{transactionId}", "DELETE"),
        ("/investmentLedger/holdings", "GET"),
        ("/investmentLedger/portfolioStatistics", "GET"),
        # 基金搜索代理：只读、不落库、不接触估值写入（需求 5.2）
        ("/investmentLedger/fundSearch", "GET"),
    }
    assert all("valuation" not in path.lower() for path, _method in routes)
    assert ("/investmentLedger/transactions/{transactionId}", "GET") not in routes
    assert not any(
        method in {"PUT", "PATCH"}
        for _path, method in routes
    )
