"""估值摄取专用仓储；公开账本服务和路由不能调用本模块写入。"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
import logging

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqliteInsert
from sqlalchemy.orm import Session

from app.investmentLedger import models
from app.investmentLedger.constants import SOURCE_PRIORITY
from .protocol import StandardValuation

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestReport:
    """一次受控摄取批次的写入统计。"""

    accepted: int
    skipped: int
    conflicts: int = 0


class ValuationRepository:
    """唯一估值写入仓储；只接受核心 ``StandardValuation``。"""

    def __init__(self, db: Session) -> None:
        """绑定内部任务使用的会话，不暴露 HTTP 依赖。"""
        self._db = db

    @staticmethod
    def _assertStandardValues(values: Sequence[StandardValuation]) -> None:
        """在开始事务前拒绝非标准结果，避免未校验对象部分落库。"""
        if any(not isinstance(value, StandardValuation) for value in values):
            raise TypeError("估值仓储只接受 StandardValuation")

    def _hasSamePriorityConflict(
        self,
        value: StandardValuation,
        sourcePriority: Mapping[str, int],
    ) -> bool:
        """判断同产品、日期的其它受控来源是否与本值构成平级单价冲突。"""
        incomingPriority = sourcePriority.get(value.source_id)
        if incomingPriority is None:
            return False

        existingValues = self._db.scalars(
            select(models.Valuation)
            .where(
                models.Valuation.product_type == value.product_type,
                models.Valuation.product_code == value.product_code,
                models.Valuation.valuation_date == value.valuation_date,
                models.Valuation.source_id != value.source_id,
            )
            .order_by(models.Valuation.id.asc())
        ).all()
        return any(
            sourcePriority.get(existing.source_id) == incomingPriority
            and existing.unit_price != value.unit_price
            for existing in existingValues
        )

    @staticmethod
    def _logPriorityConflict(value: StandardValuation, priority: int) -> None:
        """记录可检索的结构化冲突日志，不泄露原始采集载荷。"""
        logger.warning(
            "valuation_priority_conflict product_type=%s product_code=%s "
            "valuation_date=%s source_id=%s source_priority=%s",
            value.product_type,
            value.product_code,
            value.valuation_date.isoformat(),
            value.source_id,
            priority,
        )

    def ingestBatch(
        self,
        values: Sequence[StandardValuation],
        sourcePriority: Mapping[str, int] | None = None,
    ) -> IngestReport:
        """在一个受控事务中幂等写入，并隔离同优先级的跨来源冲突。

        同一产品/日期/来源使用数据库唯一键更新审计字段和最新的合法值，因而重复
        批次不会创建重复记录。不同来源可并存，账本读取层据相同核心优先级选择
        生效记录；若两个已配置来源优先级相同且单价冲突，则保留先前记录并写日志。
        """
        self._assertStandardValues(values)
        priorities = SOURCE_PRIORITY if sourcePriority is None else sourcePriority
        accepted = 0
        skipped = 0
        conflicts = 0

        try:
            for value in values:
                priority = priorities.get(value.source_id)
                if self._hasSamePriorityConflict(value, priorities):
                    if priority is not None:
                        self._logPriorityConflict(value, priority)
                    skipped += 1
                    conflicts += 1
                    continue

                statement = sqliteInsert(models.Valuation).values(
                    product_type=value.product_type,
                    product_code=value.product_code,
                    valuation_date=value.valuation_date,
                    unit_price=value.unit_price,
                    source_id=value.source_id,
                    collected_at=value.collected_at,
                    source_reference=value.source_reference,
                    raw_payload_hash=value.raw_payload_hash,
                    updated_at=datetime.now(),
                )
                statement = statement.on_conflict_do_update(
                    index_elements=[
                        "product_type",
                        "product_code",
                        "valuation_date",
                        "source_id",
                    ],
                    set_={
                        "unit_price": value.unit_price,
                        "collected_at": value.collected_at,
                        "source_reference": value.source_reference,
                        "raw_payload_hash": value.raw_payload_hash,
                        "updated_at": datetime.now(),
                    },
                )
                self._db.execute(statement)
                accepted += 1
            self._db.commit()
        except Exception:
            self._db.rollback()
            raise

        return IngestReport(accepted=accepted, skipped=skipped, conflicts=conflicts)
