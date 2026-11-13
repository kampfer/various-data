"""邮件告警：按任务可补属性分级发送，发送失败不影响任务。"""

from __future__ import annotations

import logging
import smtplib
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.utils import formataddr

from scheduler.config import SmtpSettings
from scheduler.registry import CATCHUP_BACKFILL, JobSpec

logger = logging.getLogger("scheduler")


@dataclass
class DeliveryResult:
    ok: bool
    error: str | None = None


def _catchup_text(catchup: str) -> str:
    if catchup == CATCHUP_BACKFILL:
        return "backfill（可补跑）"
    return "none（不可回溯，错过即丢失）"


class Notifier:
    def __init__(self, settings: SmtpSettings | None):
        self.settings = settings
        self._warned = False
        if settings is None:
            self._warn_missing()

    def _warn_missing(self) -> None:
        if self._warned:
            return
        self._warned = True
        logger.warning(
            "未配置 SMTP（src/backend/scheduler/config.local.yaml），"
            "邮件告警降级为仅记录日志，任务执行不受影响"
        )

    def send(self, subject: str, body: str) -> DeliveryResult:
        if self.settings is None:
            self._warn_missing()
            return DeliveryResult(False, "SMTP 未配置")

        settings = self.settings
        message = MIMEText(body, "plain", "utf-8")
        message["From"] = formataddr((settings.sender_name, settings.username))
        message["To"] = ", ".join(settings.recipients)
        message["Subject"] = subject

        try:
            if settings.use_ssl:
                server = smtplib.SMTP_SSL(
                    settings.host, settings.port, timeout=settings.timeout_seconds
                )
            else:
                server = smtplib.SMTP(
                    settings.host, settings.port, timeout=settings.timeout_seconds
                )
                server.starttls()
            try:
                server.login(settings.username, settings.password)
                server.sendmail(
                    settings.username, list(settings.recipients), message.as_string()
                )
            finally:
                server.quit()
        except Exception as exc:  # 告警失败只记录，不改变任务结果
            logger.warning("邮件告警发送失败: %s", exc)
            return DeliveryResult(False, f"{type(exc).__name__}: {exc}")

        return DeliveryResult(True)

    def notify_failure(
        self,
        spec: JobSpec,
        run: dict,
        error: str,
        is_final: bool,
        next_retry_at: str | None,
    ) -> DeliveryResult:
        if is_final:
            follow_up = "否，重试次数已用尽，该次运行已最终失败"
        else:
            follow_up = f"是，将于 {next_retry_at} 自动重试"

        body = "\n".join(
            [
                f"任务标识: {spec.id}",
                f"任务名称: {spec.name}",
                f"计划触发时间: {run['scheduled_at']}",
                f"触发类型: {run['trigger_kind']}",
                f"本次尝试: {run['attempt']}/{run['max_attempts']}",
                f"可补属性: {_catchup_text(spec.catchup)}",
                f"是否还有补跑机会: {follow_up}",
                "",
                "错误摘要:",
                error,
            ]
        )
        subject = f"[various-data][失败] {spec.name} ({spec.id})"
        return self.send(subject, body)

    def notify_lost(
        self, spec: JobSpec, scheduled_at: str, missed_count: int
    ) -> DeliveryResult:
        body = "\n".join(
            [
                f"任务标识: {spec.id}",
                f"任务名称: {spec.name}",
                f"计划触发时间: {scheduled_at}",
                f"错过次数: {missed_count}",
                f"可补属性: {_catchup_text(spec.catchup)}",
                "说明: 停机期间错过的触发已无法补齐，对应时刻的数据已丢失。",
            ]
        )
        subject = f"[various-data][丢失] {spec.name} ({spec.id})"
        return self.send(subject, body)
