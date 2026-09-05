"""投资台账账户结构升级测试。"""
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    inspect,
    text,
)
from sqlalchemy.engine import Engine

from app.investmentLedger.models import Base
from app.investmentLedger.schema import AccountSchemaManager


def createLegacyTransactionTable(engine: Engine) -> None:
    """创建不含 account_id 的旧版交易表并写入一笔历史记录。"""
    metadata = MetaData()
    legacyTransaction = Table(
        "il_transaction",
        metadata,
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("product_type", String(16), nullable=False),
        Column("product_name", String(100), nullable=False),
        Column("product_code", String(32), nullable=False),
        Column("transaction_price", Text, nullable=False),
        Column("transaction_quantity", Text, nullable=False),
        Column("fee", Text, nullable=True),
        Column("direction", String(16), nullable=False),
        Column("trade_date", Date, nullable=False),
        Column("created_at", DateTime, nullable=False),
    )
    metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            legacyTransaction.insert().values(
                product_type="FUND",
                product_name="历史基金",
                product_code="F001",
                transaction_price=str(Decimal("1.00")),
                transaction_quantity=str(Decimal("2")),
                fee=None,
                direction="BUY",
                trade_date=date(2024, 1, 1),
                created_at=datetime(2024, 1, 1),
            )
        )


def testUpgradeAccountSchemaPreservesLegacyTransactionsAndIsRepeatable(
    tempEngine: Engine,
):
    createLegacyTransactionTable(tempEngine)
    manager = AccountSchemaManager(tempEngine)

    manager.upgradeAccountSchema()
    manager.upgradeAccountSchema()

    inspector = inspect(tempEngine)
    accountColumns = {
        column["name"] for column in inspector.get_columns("il_account")
    }
    transactionColumns = {
        column["name"]
        for column in inspector.get_columns("il_transaction")
    }
    foreignKeys = inspector.get_foreign_keys("il_transaction")
    indexes = {
        index["name"] for index in inspector.get_indexes("il_transaction")
    }

    assert {"id", "name", "account_type", "is_active"} <= accountColumns
    assert "account_id" in transactionColumns
    assert any(
        foreignKey["referred_table"] == "il_account"
        and foreignKey["constrained_columns"] == ["account_id"]
        for foreignKey in foreignKeys
    )
    assert "ix_il_transaction_account_id" in indexes
    assert "ix_il_transaction_account_product" in indexes

    with tempEngine.connect() as connection:
        legacyRow = connection.execute(
            text(
                "SELECT product_code, account_id, confirmation_date "
                "FROM il_transaction WHERE product_code = 'F001'"
            )
        ).one()

    assert legacyRow == ("F001", None, "2024-01-02")


def testUpgradeAccountSchemaBackfillsOnlyMissingFundConfirmationDates(
    tempEngine: Engine,
):
    """回填缺失确认日，保留已有值且不处理非基金交易。"""
    Base.metadata.create_all(bind=tempEngine)
    with tempEngine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO il_transaction ("
                "product_type, product_name, product_code, transaction_price, "
                "transaction_quantity, fee, direction, trade_date, "
                "confirmation_date, created_at"
                ") VALUES ("
                ":product_type, :product_name, :product_code, :transaction_price, "
                ":transaction_quantity, :fee, :direction, :trade_date, "
                ":confirmation_date, :created_at"
                ")"
            ),
            [
                {
                    "product_type": "FUND",
                    "product_name": "周四基金",
                    "product_code": "F001",
                    "transaction_price": "1",
                    "transaction_quantity": "2",
                    "fee": None,
                    "direction": "BUY",
                    "trade_date": date(2024, 1, 4),
                    "confirmation_date": None,
                    "created_at": datetime(2024, 1, 4),
                },
                {
                    "product_type": "FUND",
                    "product_name": "周五基金",
                    "product_code": "F002",
                    "transaction_price": "1",
                    "transaction_quantity": "2",
                    "fee": None,
                    "direction": "BUY",
                    "trade_date": date(2024, 1, 5),
                    "confirmation_date": None,
                    "created_at": datetime(2024, 1, 5),
                },
                {
                    "product_type": "FUND",
                    "product_name": "已有确认日基金",
                    "product_code": "F003",
                    "transaction_price": "1",
                    "transaction_quantity": "2",
                    "fee": None,
                    "direction": "BUY",
                    "trade_date": date(2024, 1, 5),
                    "confirmation_date": date(2024, 1, 10),
                    "created_at": datetime(2024, 1, 5),
                },
                {
                    "product_type": "STOCK",
                    "product_name": "股票",
                    "product_code": "S001",
                    "transaction_price": "1",
                    "transaction_quantity": "2",
                    "fee": None,
                    "direction": "BUY",
                    "trade_date": date(2024, 1, 5),
                    "confirmation_date": None,
                    "created_at": datetime(2024, 1, 5),
                },
            ],
        )

    manager = AccountSchemaManager(tempEngine)
    manager.upgradeAccountSchema()
    manager.upgradeAccountSchema()

    with tempEngine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT product_code, confirmation_date "
                "FROM il_transaction ORDER BY product_code"
            )
        ).all()

    assert rows == [
        ("F001", "2024-01-05"),
        ("F002", "2024-01-08"),
        ("F003", "2024-01-10"),
        ("S001", None),
    ]


def testUpgradeAccountSchemaIsIdempotentForNewSchema(tempEngine: Engine):
    Base.metadata.create_all(bind=tempEngine)
    manager = AccountSchemaManager(tempEngine)

    manager.upgradeAccountSchema()
    manager.upgradeAccountSchema()

    inspector = inspect(tempEngine)
    assert "il_account" in inspector.get_table_names()
    assert "account_id" in {
        column["name"]
        for column in inspector.get_columns("il_transaction")
    }
