"""投资交易账本的数据访问函数。

本模块只负责构造和执行 SQL，不承担输入校验、分页或业务异常转换。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ColumnElement, and_, func, select, tuple_
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from sqlalchemy.orm import Session

from app.investmentLedger import models
from app.investmentLedger.schemas import (
    TransactionCreate,
    TransactionQuery,
    ValuationUpsert,
)


def _transactionPredicates(query: TransactionQuery) -> list[ColumnElement[bool]]:
    """把已启用的交易查询条件转换为按逻辑与组合的 SQL 谓词。"""
    predicates: list[ColumnElement[bool]] = []

    if query.product_type is not None:
        predicates.append(models.Transaction.product_type == query.product_type)
    if query.direction is not None:
        predicates.append(models.Transaction.direction == query.direction)
    if query.start_date is not None:
        predicates.append(models.Transaction.trade_date >= query.start_date)
    if query.end_date is not None:
        predicates.append(models.Transaction.trade_date <= query.end_date)
    if query.product_name is not None:
        predicates.append(
            models.Transaction.product_name.contains(
                query.product_name, autoescape=True
            )
        )
    if query.product_code is not None:
        predicates.append(
            models.Transaction.product_code.contains(
                query.product_code, autoescape=True
            )
        )
    if query.scope_product_type is not None:
        predicates.append(
            models.Transaction.product_type == query.scope_product_type
        )
    if query.scope_product_code is not None:
        predicates.append(
            models.Transaction.product_code == query.scope_product_code
        )

    return predicates

def queryTransactions(
    db: Session, query: TransactionQuery
) -> list[models.Transaction]:
    """查询满足全部已启用条件的交易，并返回稳定的有序结果集。

    日期范围使用闭区间；名称和代码使用转义通配符后的 ``LIKE %v%``
    包含匹配。指定日期排序时，同一日期内以 ``id`` 升序作为稳定次序；
    未指定日期排序时直接按 ``id`` 升序。
    """
    statement = select(models.Transaction).where(
        *_transactionPredicates(query)
    )

    if query.trade_date_order == "asc":
        statement = statement.order_by(
            models.Transaction.trade_date.asc(), models.Transaction.id.asc()
        )
    elif query.trade_date_order == "desc":
        statement = statement.order_by(
            models.Transaction.trade_date.desc(), models.Transaction.id.asc()
        )
    else:
        statement = statement.order_by(models.Transaction.id.asc())

    return list(db.scalars(statement).all())


def countTransactions(db: Session) -> int:
    """统计交易全表行数；空表返回 ``0``。"""
    statement = select(func.count(models.Transaction.id))
    return db.execute(statement).scalar_one()


def addTransaction(
    db: Session, payload: TransactionCreate
) -> models.Transaction:
    """插入并提交一笔交易；异常时回滚当前事务（需求 1.3）。"""
    transaction = models.Transaction(
        product_type=payload.product_type.value,
        product_name=payload.product_name,
        product_code=payload.product_code,
        unit_price=payload.unit_price,
        quantity=payload.quantity,
        direction=payload.direction.value,
        trade_date=payload.trade_date,
    )
    try:
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction
    except Exception:
        db.rollback()
        raise


def removeTransaction(
    db: Session, transactionId: int
) -> models.Transaction | None:
    """按主键删除交易；记录不存在时返回 ``None``（需求 1.5）。"""
    transaction = db.get(models.Transaction, transactionId)
    if transaction is None:
        return None

    try:
        db.delete(transaction)
        db.commit()
        return transaction
    except Exception:
        db.rollback()
        raise


def getLatestValuations(
    db: Session, keys: list[tuple[str, str]]
) -> dict[tuple[str, str], models.Valuation]:
    """批量返回各产品估值日期最大的记录；无估值产品不返回（需求 3.4）。"""
    uniqueKeys = list(dict.fromkeys(keys))
    if not uniqueKeys:
        return {}

    latestDates = (
        select(
            models.Valuation.product_type.label("product_type"),
            models.Valuation.product_code.label("product_code"),
            func.max(models.Valuation.valuation_date).label("valuation_date"),
        )
        .where(
            tuple_(
                models.Valuation.product_type,
                models.Valuation.product_code,
            ).in_(uniqueKeys)
        )
        .group_by(
            models.Valuation.product_type,
            models.Valuation.product_code,
        )
        .subquery()
    )
    statement = select(models.Valuation).join(
        latestDates,
        and_(
            models.Valuation.product_type == latestDates.c.product_type,
            models.Valuation.product_code == latestDates.c.product_code,
            models.Valuation.valuation_date == latestDates.c.valuation_date,
        ),
    )
    valuations = db.scalars(statement).all()
    return {
        (valuation.product_type, valuation.product_code): valuation
        for valuation in valuations
    }


def upsertValuation(
    db: Session, payload: ValuationUpsert
) -> models.Valuation:
    """以产品类型、代码和估值日期为键写入或覆盖估值（需求 3.3）。"""
    statement = (
        sqlite_upsert(models.Valuation)
        .values(
            product_type=payload.product_type.value,
            product_code=payload.product_code,
            valuation_date=payload.valuation_date,
            unit_price=payload.unit_price,
        )
        .on_conflict_do_update(
            index_elements=[
                models.Valuation.product_type,
                models.Valuation.product_code,
                models.Valuation.valuation_date,
            ],
            set_={
                "unit_price": payload.unit_price,
                "updated_at": datetime.now(),
            },
        )
        .returning(models.Valuation)
    )
    try:
        valuation = db.scalars(statement).one()
        db.commit()
        return valuation
    except Exception:
        db.rollback()
        raise
