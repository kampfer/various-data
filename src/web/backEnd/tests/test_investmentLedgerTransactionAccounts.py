"""交易与投资账户关联接口测试。"""
from collections.abc import Iterator
from datetime import date

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.dependencies import get_db
from app.investmentLedger.exceptions import registerLedgerExceptionHandlers
from app.investmentLedger.models import Base
from app.investmentLedger.router import router


@pytest.fixture()
def transactionClient(tempEngine: Engine) -> Iterator[TestClient]:
    """创建隔离的交易账户接口客户端。"""
    Base.metadata.create_all(bind=tempEngine)
    TestingSessionLocal = sessionmaker(bind=tempEngine, autoflush=False, autocommit=False)

    def overrideGetDb():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    registerLedgerExceptionHandlers(app)
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = overrideGetDb
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def transactionPayload(accountId: int | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "productType": "FUND",
        "productName": "测试基金",
        "productCode": "F001",
        "transactionPrice": "1.25",
        "transactionQuantity": "10",
        "direction": "BUY",
        "tradeDate": date(2024, 2, 29).isoformat(),
    }
    if accountId is not None:
        payload["accountId"] = accountId
    return payload


def testCreateAndListTransactionExposeAccount(transactionClient: TestClient):
    accountResponse = transactionClient.post(
        "/api/investmentLedger/accounts",
        json={"name": "基金账户", "accountType": "FUND", "institution": "示例机构"},
    )
    accountId = accountResponse.json()["data"]["id"]

    createResponse = transactionClient.post(
        "/api/investmentLedger/transactions",
        json=transactionPayload(accountId),
    )

    assert createResponse.status_code == 200
    created = createResponse.json()["data"]
    assert created["accountId"] == accountId
    assert created["accountName"] == "基金账户"
    assert created["accountInstitution"] == "示例机构"

    listResponse = transactionClient.get("/api/investmentLedger/transactions")
    assert listResponse.status_code == 200
    listed = listResponse.json()["data"]["items"]
    assert listed[0]["accountId"] == accountId
    assert listed[0]["accountName"] == "基金账户"
    assert listed[0]["accountInstitution"] == "示例机构"


def testCreateTransactionWithUnknownAccountReturnsNotFound(transactionClient: TestClient):
    response = transactionClient.post(
        "/api/investmentLedger/transactions",
        json=transactionPayload(999),
    )

    assert response.status_code == 404


def testLegacyTransactionCanStillHaveNoAccount(transactionClient: TestClient):
    response = transactionClient.post(
        "/api/investmentLedger/transactions",
        json=transactionPayload(),
    )

    assert response.status_code == 200
    assert response.json()["data"]["accountId"] is None
    assert response.json()["data"]["accountName"] is None
    assert response.json()["data"]["accountInstitution"] is None


def testDisabledAccountCannotCreateNewTransactionButHistoryRemainsVisible(
    transactionClient: TestClient,
):
    accountResponse = transactionClient.post(
        "/api/investmentLedger/accounts",
        json={"name": "基金账户", "accountType": "FUND", "institution": "示例机构"},
    )
    accountId = accountResponse.json()["data"]["id"]

    firstTransaction = transactionClient.post(
        "/api/investmentLedger/transactions",
        json=transactionPayload(accountId),
    )
    assert firstTransaction.status_code == 200

    disableResponse = transactionClient.patch(
        f"/api/investmentLedger/accounts/{accountId}/status",
        json={"isActive": False},
    )
    assert disableResponse.status_code == 200

    blockedTransaction = transactionClient.post(
        "/api/investmentLedger/transactions",
        json=transactionPayload(accountId),
    )
    assert blockedTransaction.status_code == 422
    blockedPayload = blockedTransaction.json()
    assert blockedPayload["data"]["fieldErrors"][0]["field"] == "accountId"
    assert blockedPayload["data"]["fieldErrors"][0]["code"] == "ACCOUNT_DISABLED"

    historyResponse = transactionClient.get("/api/investmentLedger/transactions")
    assert historyResponse.status_code == 200
    historyItems = historyResponse.json()["data"]["items"]
    assert len(historyItems) == 1
    assert historyItems[0]["accountId"] == accountId
    assert historyItems[0]["accountName"] == "基金账户"
