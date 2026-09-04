"""投资账户公开接口测试。"""
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.dependencies import get_db
from app.investmentLedger.models import Base
from app.investmentLedger.router import router


@pytest.fixture()
def accountClient(tempEngine: Engine) -> Iterator[TestClient]:
    """创建使用临时数据库会话的隔离账户 API 客户端。"""
    Base.metadata.create_all(bind=tempEngine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=tempEngine,
    )

    def overrideGetDb():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app = FastAPI()
    app.include_router(router, prefix="/api")
    app.dependency_overrides[get_db] = overrideGetDb

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def testCreateAndListAccountsOrdersByCreatedAtDescending(
    accountClient: TestClient,
):
    firstResponse = accountClient.post(
        "/api/investmentLedger/accounts",
        json={
            "name": "基金账户",
            "accountType": "FUND",
            "institution": "天天基金",
            "remark": "第一账户",
        },
    )
    secondResponse = accountClient.post(
        "/api/investmentLedger/accounts",
        json={
            "name": "证券账户",
            "accountType": "STOCK",
            "institution": "招商证券",
            "remark": "第二账户",
        },
    )

    assert firstResponse.status_code == 200
    assert secondResponse.status_code == 200
    assert firstResponse.json()["data"]["isActive"] is True

    listResponse = accountClient.get("/api/investmentLedger/accounts")

    assert listResponse.status_code == 200
    items = listResponse.json()["data"]
    assert [item["name"] for item in items] == ["证券账户", "基金账户"]
    assert items[0]["accountType"] == "STOCK"


def testPatchAccountRemarkOnlyUpdatesRemark(accountClient: TestClient):
    createResponse = accountClient.post(
        "/api/investmentLedger/accounts",
        json={
            "name": "基金账户",
            "accountType": "FUND",
            "institution": "天天基金",
            "remark": "旧备注",
        },
    )
    accountId = createResponse.json()["data"]["id"]

    updateResponse = accountClient.patch(
        f"/api/investmentLedger/accounts/{accountId}/remark",
        json={"remark": "新备注"},
    )

    assert updateResponse.status_code == 200
    updated = updateResponse.json()["data"]
    assert updated["id"] == accountId
    assert updated["name"] == "基金账户"
    assert updated["accountType"] == "FUND"
    assert updated["institution"] == "天天基金"
    assert updated["remark"] == "新备注"


def testPatchAccountStatusDisablesAndReEnablesAccount(accountClient: TestClient):
    createResponse = accountClient.post(
        "/api/investmentLedger/accounts",
        json={"name": "基金账户", "accountType": "FUND"},
    )
    accountId = createResponse.json()["data"]["id"]

    disableResponse = accountClient.patch(
        f"/api/investmentLedger/accounts/{accountId}/status",
        json={"isActive": False},
    )
    assert disableResponse.status_code == 200
    assert disableResponse.json()["data"]["isActive"] is False

    listResponse = accountClient.get("/api/investmentLedger/accounts")
    assert listResponse.status_code == 200
    assert listResponse.json()["data"][0]["isActive"] is False

    enableResponse = accountClient.patch(
        f"/api/investmentLedger/accounts/{accountId}/status",
        json={"isActive": True},
    )
    assert enableResponse.status_code == 200
    assert enableResponse.json()["data"]["isActive"] is True


def testPatchAccountStatusRejectsOtherFields(accountClient: TestClient):
    createResponse = accountClient.post(
        "/api/investmentLedger/accounts",
        json={"name": "基金账户", "accountType": "FUND"},
    )
    accountId = createResponse.json()["data"]["id"]

    response = accountClient.patch(
        f"/api/investmentLedger/accounts/{accountId}/status",
        json={"isActive": False, "name": "不允许修改"},
    )

    assert response.status_code == 422


    createResponse = accountClient.post(
        "/api/investmentLedger/accounts",
        json={"name": "基金账户", "accountType": "FUND"},
    )
    accountId = createResponse.json()["data"]["id"]

    response = accountClient.patch(
        f"/api/investmentLedger/accounts/{accountId}/remark",
        json={"remark": "新备注", "name": "不允许修改"},
    )

    assert response.status_code == 422


def testAccountInterfaceDoesNotExposePutOrDelete(accountClient: TestClient):
    response = accountClient.post(
        "/api/investmentLedger/accounts",
        json={"name": "基金账户", "accountType": "FUND"},
    )
    accountId = response.json()["data"]["id"]

    assert accountClient.put(
        f"/api/investmentLedger/accounts/{accountId}",
        json={"remark": "不允许"},
    ).status_code == 404
    assert accountClient.delete(
        f"/api/investmentLedger/accounts/{accountId}"
    ).status_code == 404


def testCreateAccountValidatesRequiredFields(accountClient: TestClient):
    response = accountClient.post(
        "/api/investmentLedger/accounts",
        json={"name": "", "accountType": ""},
    )

    assert response.status_code == 422
