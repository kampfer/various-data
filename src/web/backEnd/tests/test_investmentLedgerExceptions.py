"""投资交易账本统一异常处理器单元测试（任务 2.4）。

覆盖需求 1.2、2.30、3.2：业务异常的 HTTP/业务码/中文提示映射、
请求枚举校验错误的中文翻译，以及数据库异常响应的敏感信息脱敏。
测试使用隔离 FastAPI 应用，不创建数据库引擎或会话。
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError, OperationalError

from app.investmentLedger.exceptions import (
    InvalidDateRange,
    InvalidPageSize,
    InvalidSearchValue,
    LedgerError,
    LedgerValidationError,
    PageOutOfRange,
    TransactionNotFound,
    registerLedgerExceptionHandlers,
)
from app.investmentLedger.schemas import TransactionCreate, ValuationUpsert


def containsChinese(value: str) -> bool:
    """判断用户可见提示是否至少包含一个汉字。"""
    return any("\u4e00" <= char <= "\u9fff" for char in value)


@pytest.fixture()
def exceptionApp() -> FastAPI:
    """创建仅装配账本异常处理器的隔离应用，不触达任何数据库。"""
    app = FastAPI()
    errorFactories: dict[str, Callable[[], LedgerError]] = {
        "ledger": LedgerError,
        "validation": LedgerValidationError,
        "notFound": lambda: TransactionNotFound(transactionId=9527),
        "pageOutOfRange": lambda: PageOutOfRange(page=4, pageCount=3),
        "invalidPageSize": lambda: InvalidPageSize(pageSize="一百零一"),
        "invalidDateRange": InvalidDateRange,
        "invalidSearchValue": lambda: InvalidSearchValue(field="productCode"),
    }

    @app.get("/business/{errorName}")
    def raiseBusinessError(errorName: str) -> None:
        """按名称抛出业务异常，验证真实 FastAPI 分发链路。"""
        raise errorFactories[errorName]()

    @app.post("/transactions")
    def validateTransaction(payload: TransactionCreate) -> dict[str, bool]:
        """仅触发交易请求模型校验，不执行交易写入。"""
        return {"accepted": bool(payload)}

    @app.put("/valuations")
    def validateValuation(payload: ValuationUpsert) -> dict[str, bool]:
        """仅触发估值请求模型校验，不执行估值写入。"""
        return {"accepted": bool(payload)}

    @app.post("/database/{errorName}")
    def raiseDatabaseError(errorName: str) -> None:
        """抛出携带 SQL、表名和底层原因的数据库异常，验证响应脱敏。"""
        if errorName == "integrity":
            raise IntegrityError(
                statement="INSERT INTO il_transaction (product_code) VALUES (?)",
                params=("SECRET_CODE",),
                orig=RuntimeError(
                    "UNIQUE constraint failed: il_transaction.product_code"
                ),
            )
        raise OperationalError(
            statement="SELECT * FROM il_valuation",
            params={},
            orig=RuntimeError("no such table: il_valuation\nTraceback: secret stack"),
        )

    registerLedgerExceptionHandlers(app)
    return app


@pytest.fixture()
def exceptionClient(exceptionApp: FastAPI) -> Iterator[TestClient]:
    """复用 FastAPI TestClient 驱动隔离应用的完整异常处理链路。"""
    with TestClient(exceptionApp) as client:
        yield client


@pytest.mark.parametrize(
    ("errorName", "expectedStatus", "expectedCode", "expectedMsg", "expectedData"),
    [
        ("ledger", 400, 400, "投资交易账本操作失败", None),
        ("validation", 422, 422, "参数校验失败", None),
        ("notFound", 404, 404, "交易记录不存在或已被删除", None),
        (
            "pageOutOfRange",
            422,
            422,
            "请求的页码无效，有效页码为 1 至 3",
            {
                "fieldErrors": [
                    {
                        "field": "page",
                        "code": "OUT_OF_RANGE",
                        "message": "请求的页码无效，有效页码为 1 至 3",
                    }
                ]
            },
        ),
        (
            "invalidPageSize",
            422,
            422,
            "自定义页大小必须为 1 至 100 的整数",
            {
                "fieldErrors": [
                    {
                        "field": "pageSize",
                        "code": "OUT_OF_RANGE",
                        "message": "自定义页大小必须为 1 至 100 的整数",
                    }
                ]
            },
        ),
        (
            "invalidDateRange",
            422,
            422,
            "交易日期范围必须同时提供有效的起始日期与结束日期，且起始日期不能晚于结束日期",
            {
                "fieldErrors": [
                    {
                        "field": "startDate",
                        "code": "OUT_OF_RANGE",
                        "message": "交易日期范围必须同时提供有效的起始日期与结束日期，且起始日期不能晚于结束日期",
                    }
                ]
            },
        ),
        (
            "invalidSearchValue",
            422,
            422,
            "搜索值不能为空，且不能超过 100 个字符",
            {
                "fieldErrors": [
                    {
                        "field": "productCode",
                        "code": "OUT_OF_RANGE",
                        "message": "搜索值不能为空，且不能超过 100 个字符",
                    }
                ]
            },
        ),
    ],
)
def testBusinessExceptionsMapToExpectedEnvelope(
    exceptionClient: TestClient,
    errorName: str,
    expectedStatus: int,
    expectedCode: int,
    expectedMsg: str,
    expectedData: dict[str, object] | None,
) -> None:
    """每种业务异常均映射到正确 HTTP 状态、业务码和中文消息。"""
    response = exceptionClient.get(f"/business/{errorName}")

    assert response.status_code == expectedStatus
    assert response.json() == {
        "code": expectedCode,
        "msg": expectedMsg,
        "data": expectedData,
    }
    assert containsChinese(response.json()["msg"])


@pytest.mark.parametrize(
    ("path", "payload", "expectedErrors"),
    [
        (
            "/transactions",
            {
                "productType": "CRYPTO_ASSET",
                "productName": "测试产品",
                "productCode": "TEST001",
                "unitPrice": "1.00",
                "quantity": 1,
                "direction": "HOLD_POSITION",
                "tradeDate": "2024-01-02",
            },
            [
                {
                    "field": "productType",
                    "code": "NOT_IN_ENUM",
                    "message": "产品类型必须为理财、基金或股票之一",
                },
                {
                    "field": "direction",
                    "code": "NOT_IN_ENUM",
                    "message": "交易方向必须为买入或卖出之一",
                },
            ],
        ),
        (
            "/valuations",
            {
                "productType": "CRYPTO_ASSET",
                "productCode": "TEST001",
                "valuationDate": "2024-01-02",
                "unitPrice": "1.00",
            },
            [
                {
                    "field": "productType",
                    "code": "NOT_IN_ENUM",
                    "message": "产品类型必须为理财、基金或股票之一",
                }
            ],
        ),
    ],
)
def testInvalidEnumsUseChineseMessagesWithoutEchoingEnglishCodes(
    exceptionClient: TestClient,
    path: str,
    payload: dict[str, object],
    expectedErrors: list[dict[str, str]],
) -> None:
    """交易与估值的非法枚举只返回中文原因，不透传英文枚举码或提交值。"""
    response = exceptionClient.request(
        "POST" if path == "/transactions" else "PUT", path, json=payload
    )

    assert response.status_code == 422
    assert response.json() == {
        "code": 422,
        "msg": "参数校验失败",
        "data": {"fieldErrors": expectedErrors},
    }
    responseText = response.text
    for rawCode in (
        "WEALTH",
        "FUND",
        "STOCK",
        "BUY",
        "SELL",
        "CRYPTO_ASSET",
        "HOLD_POSITION",
    ):
        assert rawCode not in responseText
    assert all(containsChinese(item["message"]) for item in expectedErrors)


@pytest.mark.parametrize("errorName", ["integrity", "operational"])
def testDatabaseErrorsReturnSanitizedChineseEnvelope(
    exceptionClient: TestClient, errorName: str
) -> None:
    """数据库异常统一返回安全中文信封，不泄露 SQL、表名、参数或堆栈。"""
    response = exceptionClient.post(f"/database/{errorName}")

    assert response.status_code == 500
    assert response.json() == {
        "code": 500,
        "msg": "数据保存失败，请稍后重试",
        "data": None,
    }
    responseText = response.text.lower()
    for sensitiveFragment in (
        "insert into",
        "select *",
        "il_transaction",
        "il_valuation",
        "secret_code",
        "traceback",
        "runtimeerror",
        "stack",
    ):
        assert sensitiveFragment not in responseText
