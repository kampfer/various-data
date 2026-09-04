"""投资台账数据库结构升级。"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import Engine, inspect, text
from sqlalchemy.engine import Connection

from app.investmentLedger.models import Account, Transaction


class AccountSchemaMigrationError(RuntimeError):
    """账户结构与预期不一致且无法安全自动修复时抛出的异常。"""


class AccountSchemaManager:
    """执行账户表及交易账户外键的可重复 SQLite 结构升级。"""

    _ACCOUNT_TABLE = Account.__tablename__
    _TRANSACTION_TABLE = Transaction.__tablename__
    _REQUIRED_ACCOUNT_COLUMNS = frozenset(
        {
            "id",
            "name",
            "account_type",
            "institution",
            "is_active",
            "remark",
            "created_at",
            "updated_at",
        }
    )

    def __init__(self, engine: Engine) -> None:
        """绑定目标数据库引擎；不创建独立数据库连接池。"""
        self._engine = engine

    def upgradeAccountSchema(self) -> None:
        """幂等升级账户表、交易账户列、外键和索引。"""
        with self._engine.begin() as connection:
            self._ensureAccountTable(connection)
            if not self._hasTable(connection, self._TRANSACTION_TABLE):
                return
            self._ensureTransactionAccountColumn(connection)
            self._ensureTransactionIndexes(connection)
            self._validateTransactionAccountForeignKey(connection)

    def _hasTable(self, connection: Connection, tableName: str) -> bool:
        """返回目标数据库中是否存在指定表。"""
        return tableName in inspect(connection).get_table_names()

    def _ensureAccountTable(self, connection: Connection) -> None:
        """创建账户表或验证已有账户表包含完整字段。"""
        if not self._hasTable(connection, self._ACCOUNT_TABLE):
            Account.__table__.create(bind=connection)
            return

        actualColumns = {
            column["name"]
            for column in inspect(connection).get_columns(self._ACCOUNT_TABLE)
        }
        missingColumns = self._REQUIRED_ACCOUNT_COLUMNS - actualColumns
        if missingColumns:
            missing = ", ".join(sorted(missingColumns))
            raise AccountSchemaMigrationError(
                f"账户表 {self._ACCOUNT_TABLE} 缺少必要字段：{missing}"
            )

    def _ensureTransactionAccountColumn(self, connection: Connection) -> None:
        """为旧交易表增加可空账户外键列；已有列不重复修改。"""
        columns = {
            column["name"]
            for column in inspect(connection).get_columns(self._TRANSACTION_TABLE)
        }
        if "account_id" in columns:
            return

        connection.execute(
            text(
                'ALTER TABLE "il_transaction" '
                'ADD COLUMN "account_id" INTEGER '
                'REFERENCES "il_account" ("id") ON DELETE RESTRICT'
            )
        )

    def _ensureTransactionIndexes(self, connection: Connection) -> None:
        """补建账户单列索引和账户产品复合索引。"""
        actualIndexNames = {
            index["name"]
            for index in inspect(connection).get_indexes(self._TRANSACTION_TABLE)
        }
        for index in self._accountIndexes():
            if index.name not in actualIndexNames:
                index.create(bind=connection, checkfirst=True)

    def _accountIndexes(self) -> Iterable:
        """返回模型中声明的账户相关索引。"""
        return (
            index
            for index in Transaction.__table__.indexes
            if "account_id" in {column.name for column in index.columns}
        )

    def _validateTransactionAccountForeignKey(self, connection: Connection) -> None:
        """确认交易账户列指向账户主键且删除策略为 RESTRICT。"""
        foreignKeys = inspect(connection).get_foreign_keys(self._TRANSACTION_TABLE)
        for foreignKey in foreignKeys:
            if (
                foreignKey.get("constrained_columns") == ["account_id"]
                and foreignKey.get("referred_table") == self._ACCOUNT_TABLE
            ):
                onDelete = (foreignKey.get("options") or {}).get("ondelete")
                if onDelete is None or onDelete.upper() == "RESTRICT":
                    return

        raise AccountSchemaMigrationError(
            "交易表 account_id 缺少指向 il_account.id 的 RESTRICT 外键"
        )


def upgradeAccountSchema(engine: Engine) -> None:
    """升级指定数据库中的账户结构。"""
    AccountSchemaManager(engine).upgradeAccountSchema()
