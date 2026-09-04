"""投资台账模型与账户关联的定向测试。"""
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.investmentLedger.models import Account, Base, Transaction
from app.investmentLedger.types import DecimalText


@pytest.fixture()
def ledgerSession(tempEngine: Engine, dbSession: Session):
    Base.metadata.create_all(bind=tempEngine)
    dbSession.execute(text("PRAGMA foreign_keys = ON"))
    yield dbSession


def testTransactionDecimalsRoundTripWithoutPaddingTruncationOrRounding(
    ledgerSession: Session,
):
    transaction = Transaction(
        product_type="FUND",
        product_name="基金",
        product_code="F001",
        transaction_price=Decimal("1.230000000000000001"),
        transaction_quantity=Decimal("2.500000000000000003"),
        direction="BUY",
        trade_date=date(2024, 1, 1),
    )
    ledgerSession.add(transaction)
    ledgerSession.commit()
    transaction_id = transaction.id
    ledgerSession.expunge_all()

    loaded = ledgerSession.get(Transaction, transaction_id)

    assert loaded is not None
    assert str(loaded.transaction_price) == "1.230000000000000001"
    assert str(loaded.transaction_quantity) == "2.500000000000000003"
    raw = ledgerSession.execute(
        text(
            "SELECT transaction_price, transaction_quantity "
            "FROM il_transaction WHERE id = :id"
        ),
        {"id": transaction.id},
    ).one()
    assert raw == ("1.230000000000000001", "2.500000000000000003")


def testDecimalTextRejectsFloatAndNonfiniteValues():
    column = DecimalText()

    with pytest.raises(TypeError):
        column.process_bind_param(0.1, None)
    with pytest.raises(TypeError):
        column.process_bind_param(Decimal("NaN"), None)


def testAccountSchemaStoresExtensibleTypesAndDefaults(ledgerSession: Session):
    fund_account = Account(
        name="天天基金",
        account_type="FUND",
        institution="天天基金",
    )
    stock_account = Account(
        name="证券账户",
        account_type="STOCK",
    )
    future_account = Account(
        name="银行账户",
        account_type="BANK",
    )

    ledgerSession.add_all([fund_account, stock_account, future_account])
    ledgerSession.commit()
    ledgerSession.refresh(fund_account)

    assert fund_account.id > 0
    assert fund_account.is_active is True
    assert fund_account.institution == "天天基金"
    assert stock_account.remark is None
    assert future_account.account_type == "BANK"


def testTransactionAccountIdAllowsLegacyNullAndValidAccount(
    ledgerSession: Session,
):
    account = Account(name="基金账户", account_type="FUND")
    ledgerSession.add(account)
    ledgerSession.flush()

    legacy_transaction = Transaction(
        account_id=None,
        product_type="FUND",
        product_name="历史基金",
        product_code="F002",
        transaction_price=Decimal("1.00"),
        transaction_quantity=Decimal("1"),
        direction="BUY",
        trade_date=date(2024, 1, 1),
    )
    linked_transaction = Transaction(
        account_id=account.id,
        product_type="FUND",
        product_name="新基金",
        product_code="F003",
        transaction_price=Decimal("1.00"),
        transaction_quantity=Decimal("1"),
        direction="BUY",
        trade_date=date(2024, 1, 2),
    )

    ledgerSession.add_all([legacy_transaction, linked_transaction])
    ledgerSession.commit()

    assert ledgerSession.get(Transaction, legacy_transaction.id).account_id is None
    assert ledgerSession.get(Transaction, linked_transaction.id).account_id == account.id


def testTransactionAccountForeignKeyRejectsUnknownAccount(
    ledgerSession: Session,
):
    transaction = Transaction(
        account_id=999999,
        product_type="FUND",
        product_name="基金",
        product_code="F004",
        transaction_price=Decimal("1.00"),
        transaction_quantity=Decimal("1"),
        direction="BUY",
        trade_date=date(2024, 1, 1),
    )
    ledgerSession.add(transaction)

    with pytest.raises(IntegrityError):
        ledgerSession.commit()

    ledgerSession.rollback()


def testReferencedAccountCannotBePhysicallyDeleted(ledgerSession: Session):
    account = Account(name="证券账户", account_type="STOCK")
    ledgerSession.add(account)
    ledgerSession.flush()
    ledgerSession.add(
        Transaction(
            account_id=account.id,
            product_type="STOCK",
            product_name="股票",
            product_code="600000",
            transaction_price=Decimal("10.00"),
            transaction_quantity=Decimal("100"),
            direction="BUY",
            trade_date=date(2024, 1, 1),
        )
    )
    ledgerSession.commit()

    ledgerSession.delete(account)

    with pytest.raises(IntegrityError):
        ledgerSession.commit()

    ledgerSession.rollback()


def testTransactionAccountIndexesAndForeignKeyAreDeclared(tempEngine: Engine):
    Base.metadata.create_all(bind=tempEngine)
    inspector = inspect(tempEngine)

    transaction_indexes = {
        index["name"] for index in inspector.get_indexes("il_transaction")
    }
    foreign_keys = inspector.get_foreign_keys("il_transaction")

    assert "ix_il_transaction_account_product" in transaction_indexes
    assert any(
        foreign_key["referred_table"] == "il_account"
        and foreign_key["constrained_columns"] == ["account_id"]
        for foreign_key in foreign_keys
    )
