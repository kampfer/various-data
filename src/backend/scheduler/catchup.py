"""启动补账：按水位计算错过的触发，可补的合并补跑，不可补的记丢失。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from apscheduler.triggers.cron import CronTrigger

from scheduler.alert import Notifier
from scheduler.config import TZ, to_iso
from scheduler.registry import CATCHUP_BACKFILL, JobSpec
from scheduler.store import Store

MAX_MISSED_ENUMERATION = 1000
CATCHUP_SCAN_DAYS = 40

logger = logging.getLogger("scheduler")


@dataclass
class CatchupResult:
    backfilled: int = 0
    lost: int = 0
    first_start: int = 0
    truncated: int = 0
    warnings: list[str] = field(default_factory=list)


def previous_trigger(trigger: CronTrigger, at: datetime) -> datetime | None:
    """返回 at 之前（含）最近一次触发时间。"""

    cursor = at - timedelta(days=CATCHUP_SCAN_DAYS)
    last: datetime | None = None
    for _ in range(MAX_MISSED_ENUMERATION * 2):
        nxt = trigger.get_next_fire_time(cursor, at)
        if nxt is None or nxt > at:
            break
        last = nxt
        cursor = nxt
    return last


def missed_triggers(
    trigger: CronTrigger, last: datetime, at: datetime, cap: int = MAX_MISSED_ENUMERATION
) -> list[datetime]:
    """枚举 last 之后、at 之前（含）的全部触发时间，最多 cap 次。"""

    missed: list[datetime] = []
    cursor = last
    while len(missed) < cap:
        nxt = trigger.get_next_fire_time(cursor, at)
        if nxt is None or nxt > at:
            break
        missed.append(nxt)
        cursor = nxt
    return missed


def _parse_state(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=TZ)
    return parsed


def run_catchup(
    store: Store,
    registry: list[JobSpec],
    notifier: Notifier,
    at: datetime,
) -> CatchupResult:
    result = CatchupResult()
    at_iso = to_iso(at)

    for spec in registry:
        trigger = spec.build_trigger()
        state = store.get_state(spec.id)

        if state is None:
            previous = previous_trigger(trigger, at)
            if previous is not None:
                store.advance_state(spec.id, to_iso(previous), at_iso)
            result.first_start += 1
            logger.info(
                "任务 %s 首次启动，水位初始化为 %s，不回放历史触发",
                spec.id,
                to_iso(previous) if previous else "无",
            )
            continue

        missed = missed_triggers(trigger, _parse_state(state), at)
        if not missed:
            continue

        if len(missed) >= MAX_MISSED_ENUMERATION:
            result.truncated += 1
            message = (
                f"任务 {spec.id} 错过的触发达到枚举上限 {MAX_MISSED_ENUMERATION}，"
                "本次按上限截断，水位推进到截断点"
            )
            result.warnings.append(message)
            logger.error(message)

        last_missed = missed[-1]
        count = len(missed)
        scheduled_at = to_iso(last_missed)

        if spec.catchup == CATCHUP_BACKFILL:
            inserted = store.enqueue(
                job_id=spec.id,
                scheduled_at=scheduled_at,
                trigger_kind="catchup",
                max_attempts=spec.max_attempts,
                missed_count=count,
                created_at=at_iso,
            )
            if inserted:
                result.backfilled += 1
            logger.warning(
                "任务 %s 停机期间错过 %d 次触发，已合并为一次补跑（scheduled_at=%s）",
                spec.id,
                count,
                scheduled_at,
            )
        else:
            run_id = store.insert_lost(
                job_id=spec.id,
                scheduled_at=scheduled_at,
                missed_count=count,
                max_attempts=spec.max_attempts,
                error=f"停机期间错过 {count} 次触发，数据不可补",
                created_at=at_iso,
            )
            if run_id is not None:
                result.lost += 1
                delivery = notifier.notify_lost(spec, scheduled_at, count)
                if delivery.ok:
                    store.mark_alerted(run_id, at_iso)
                else:
                    store.mark_alert_failed(run_id, delivery.error or "发送失败")
            logger.error(
                "任务 %s 停机期间错过 %d 次触发，已标记丢失并告警", spec.id, count
            )

        store.advance_state(spec.id, scheduled_at, at_iso)

    return result
