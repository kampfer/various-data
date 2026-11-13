"""单线程消费者：串行执行、失败重试、按可补属性分级告警。"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta

from scheduler.alert import Notifier
from scheduler.config import now, now_iso, to_iso
from scheduler.registry import CATCHUP_NONE, JobSpec
from scheduler.store import Store


class Runner:
    def __init__(
        self,
        store: Store,
        registry: list[JobSpec],
        notifier: Notifier,
        logger: logging.Logger,
    ):
        self.store = store
        self.registry = {spec.id: spec for spec in registry}
        self.notifier = notifier
        self.logger = logger
        self._condition = threading.Condition()
        self._stop = False
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(
            target=self._loop, name="scheduler-runner", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        with self._condition:
            self._stop = True
            self._condition.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=30)

    def wake(self) -> None:
        with self._condition:
            self._condition.notify_all()

    def _loop(self) -> None:
        while True:
            with self._condition:
                if self._stop:
                    return
            run = self.store.claim_next(now_iso())
            if run is None:
                self._wait()
                continue
            self.execute(run)

    def _wait(self) -> None:
        with self._condition:
            if self._stop:
                return
            timeout = 30.0
            wake_at = self.store.next_wakeup()
            if wake_at:
                try:
                    delta = (datetime.fromisoformat(wake_at) - now()).total_seconds()
                    timeout = max(0.0, min(timeout, delta))
                except ValueError:
                    pass
            self._condition.wait(timeout=timeout)

    def execute(self, run: dict) -> None:
        """执行一条已置为 running 的记录，并完成状态流转。"""

        spec = self.registry.get(run["job_id"])
        if spec is None:
            error = f"未注册的任务: {run['job_id']}"
            self.store.mark_failure(run["id"], error, None, now_iso())
            self.logger.error(error)
            return

        started = time.monotonic()
        self.logger.info(
            "开始执行任务 job=%s run=%s attempt=%s/%s trigger=%s scheduled_at=%s",
            spec.id,
            run["id"],
            run["attempt"],
            run["max_attempts"],
            run["trigger_kind"],
            run["scheduled_at"],
        )

        try:
            spec.func()
        except Exception as exc:  # 任务失败进入重试/终态
            error = f"{type(exc).__name__}: {exc}"
            self.logger.exception(
                "任务执行失败 job=%s run=%s 耗时=%.2fs",
                spec.id,
                run["id"],
                time.monotonic() - started,
            )
            self._handle_failure(spec, run, error)
        else:
            self.store.mark_success(run["id"], now_iso())
            self.logger.info(
                "任务执行成功 job=%s run=%s 耗时=%.2fs",
                spec.id,
                run["id"],
                time.monotonic() - started,
            )

    def _handle_failure(self, spec: JobSpec, run: dict, error: str) -> None:
        at = now()
        at_iso = to_iso(at)
        remaining = run["attempt"] < run["max_attempts"]
        next_retry_at = None
        if remaining:
            next_retry_at = to_iso(
                at + timedelta(seconds=spec.retry_interval_seconds)
            )

        self.store.mark_failure(run["id"], error, next_retry_at, at_iso)
        self.logger.warning(
            "任务 job=%s run=%s 进入%s%s",
            spec.id,
            run["id"],
            "重试等待" if remaining else "最终失败",
            f"，下次尝试 {next_retry_at}" if remaining else "",
        )

        # 不可回溯任务每次失败都告警；可回溯任务仅在重试耗尽后告警。
        should_alert = spec.catchup == CATCHUP_NONE or not remaining
        if not should_alert:
            return

        delivery = self.notifier.notify_failure(
            spec, run, error, is_final=not remaining, next_retry_at=next_retry_at
        )
        if delivery.ok:
            self.store.mark_alerted(run["id"], at_iso)
        else:
            self.store.mark_alert_failed(run["id"], delivery.error or "发送失败")
