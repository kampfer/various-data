"""投资交易账本的数据访问函数。

本模块只负责构造和执行 SQL，不承担输入校验、分页或业务异常转换。
"""

from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal

from sqlalchemy import ColumnElement, and_, case, func, select, tuple_
from sqlalchemy.orm import Session

from app.investmentLedger import models
from app.investmentLedger.constants import SOURCE_PRIORITY, TradeDirection
from app.investmentLedger.schemas import TransactionCreate, TransactionQuery


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
    """插入并提交一笔交易；异常时回滚当前事务（需求 1.3、6.4）。

    ``fee`` 由服务层归一为非空 ``Decimal``（``None`` 已转为 ``Decimal(0)``）后随交易落库。
    """
    transaction = models.Transaction(
        product_type=payload.product_type.value,
        product_name=payload.product_name,
        product_code=payload.product_code,
        transaction_price=payload.transaction_price,
        transaction_quantity=payload.transaction_quantity,
        fee=payload.fee,
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


def getPositionQuantity(
    db: Session, productType: str, productCode: str
) -> Decimal:
    """只读查询同产品已落库持仓数量（Σ 买入数量 − Σ 卖出数量，需求 1.3 拦截前提）。

    以单条 SQL 聚合 ``transaction_quantity``：买入方向取正、卖出方向取负，
    无任何交易时返回 ``Decimal(0)``。本函数不写入、不抛业务异常，仅服务于
    服务层在创建卖出交易前的预演判定。

    :param productType: 产品类型英文码，与 ``Transaction.product_type`` 列值同口径。
    :param productCode: 产品代码，与 ``Transaction.product_code`` 列值同口径。
    :return: 已落库的累计买入数量减累计卖出数量；空结果为 ``Decimal(0)``。
    """
    deltaExpression = case(
        (
            models.Transaction.direction == TradeDirection.BUY.value,
            models.Transaction.transaction_quantity,
        ),
        else_=-models.Transaction.transaction_quantity,
    )
    statement = select(
        func.coalesce(func.sum(deltaExpression), 0)
    ).where(
        models.Transaction.product_type == productType,
        models.Transaction.product_code == productCode,
    )
    total = db.execute(statement).scalar_one()
    return total if isinstance(total, Decimal) else Decimal(total)


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


def _valuationSelectionKey(
    valuation: models.Valuation,
    sourcePriority: Mapping[str, int],
) -> tuple[int, int, str, int]:
    """返回同日估值的稳定选择键，不进行任何金额或浮点计算。

    已配置来源优先于未配置来源；配置值越小越优先。未配置来源统一置后，
    再按来源标识和内部主键排序，避免数据库返回顺序造成不确定结果。
    """
    configuredPriority = sourcePriority.get(valuation.source_id)
    if configuredPriority is None:
        return (1, 0, valuation.source_id, valuation.id or 0)
    return (0, configuredPriority, valuation.source_id, valuation.id or 0)


def getLatestValuations(
    db: Session,
    keys: list[tuple[str, str]],
    sourcePriority: Mapping[str, int] | None = None,
) -> dict[tuple[str, str], models.Valuation]:
    """只读批量读取各产品最新且来源确定的标准估值（需求 3.1）。

    查询先按产品键取得最大估值日期的全部候选，再按核心受控来源优先级
    选择同日单条记录。未配置来源不会被静默丢弃，但始终排在已配置来源后，
    并以 ``source_id`` 和主键作稳定的确定性决胜。无估值产品不返回；本函数
    只执行查询，不写入、覆盖或编排估值数据。
    """
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
    statement = (
        select(models.Valuation)
        .join(
            latestDates,
            and_(
                models.Valuation.product_type == latestDates.c.product_type,
                models.Valuation.product_code == latestDates.c.product_code,
                models.Valuation.valuation_date
                == latestDates.c.valuation_date,
            ),
        )
        .order_by(
            models.Valuation.product_type.asc(),
            models.Valuation.product_code.asc(),
            models.Valuation.source_id.asc(),
            models.Valuation.id.asc(),
        )
    )
    candidates = db.scalars(statement).all()
    priorities = SOURCE_PRIORITY if sourcePriority is None else sourcePriority
    selected: dict[tuple[str, str], models.Valuation] = {}
    for valuation in candidates:
        key = (valuation.product_type, valuation.product_code)
        current = selected.get(key)
        if current is None or _valuationSelectionKey(
            valuation, priorities
        ) < _valuationSelectionKey(current, priorities):
            selected[key] = valuation
    return selected
