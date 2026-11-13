"""任务注册表：cron 表达式、可补属性与重试参数。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Callable

from apscheduler.triggers.cron import CronTrigger

from scheduler.config import Config, TZ
from scheduler.tasks import db_backup, omo, sina_news

CATCHUP_BACKFILL = "backfill"
CATCHUP_NONE = "none"
VALID_CATCHUP = (CATCHUP_BACKFILL, CATCHUP_NONE)


@dataclass(frozen=True)
class JobSpec:
    id: str
    name: str
    cron: dict
    catchup: str
    func: Callable[[], None]
    max_attempts: int
    retry_interval_seconds: int

    def __post_init__(self) -> None:
        if self.catchup not in VALID_CATCHUP:
            raise ValueError(
                f"任务 {self.id} 的 catchup 必须显式声明为 {VALID_CATCHUP}，"
                f"当前为 {self.catchup!r}"
            )
        if self.max_attempts < 1:
            raise ValueError(f"任务 {self.id} 的 max_attempts 必须不小于 1")

    def build_trigger(self) -> CronTrigger:
        return CronTrigger(timezone=TZ, **self.cron)

    def describe(self) -> str:
        return (
            f"{self.id}({self.name}) cron={self.cron} catchup={self.catchup} "
            f"重试={self.max_attempts} 次/{self.retry_interval_seconds} 秒"
        )


def build_registry(config: Config) -> list[JobSpec]:
    """三个任务的注册项；catchup 全部显式声明。"""

    retry = dict(
        max_attempts=config.retry_max_attempts,
        retry_interval_seconds=config.retry_interval_seconds,
    )
    return [
        JobSpec(
            id="sina_news",
            name="新浪财经快讯",
            cron={"minute": 0},
            catchup=CATCHUP_BACKFILL,
            func=partial(sina_news.run, config),
            **retry,
        ),
        JobSpec(
            id="omo",
            name="央行公开市场公告",
            cron={"hour": 12, "minute": 0},
            catchup=CATCHUP_BACKFILL,
            func=partial(omo.run, config),
            **retry,
        ),
        JobSpec(
            id="db_backup",
            name="数据库备份",
            cron={"day": 1, "hour": 0, "minute": 0},
            catchup=CATCHUP_BACKFILL,
            func=partial(db_backup.run, config),
            **retry,
        ),
    ]


def find_spec(registry: list[JobSpec], job_id: str) -> JobSpec:
    for spec in registry:
        if spec.id == job_id:
            return spec
    raise KeyError(f"未注册的任务: {job_id}（可选: {', '.join(s.id for s in registry)}）")
