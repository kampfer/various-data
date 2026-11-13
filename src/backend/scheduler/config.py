"""运行配置：仓库路径、数据库、账本、日志、重试默认值与 SMTP。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

# src/backend/scheduler/config.py -> scheduler -> backend -> src -> 仓库根
REPO_ROOT = Path(__file__).resolve().parents[3]

TZ = ZoneInfo("Asia/Shanghai")

DEFAULT_RETRY_MAX_ATTEMPTS = 3
DEFAULT_RETRY_INTERVAL_SECONDS = 300

DEFAULT_ADMIN_HOST = "127.0.0.1"
DEFAULT_ADMIN_PORT = 8787
ADMIN_ROOT_PATH = "src/frontEnd/dist"

LOCAL_CONFIG_PATH = REPO_ROOT / "src" / "backend" / "scheduler" / "config.local.yaml"


@dataclass(frozen=True)
class AdminSettings:
    """进程内管理服务配置；默认启用并仅绑定回环地址。"""

    enabled: bool = True
    host: str = DEFAULT_ADMIN_HOST
    port: int = DEFAULT_ADMIN_PORT

    @property
    def is_loopback(self) -> bool:
        return self.host in ("127.0.0.1", "localhost", "::1")

    def describe(self) -> str:
        if not self.enabled:
            return "已关闭"
        return f"http://{self.host}:{self.port}"


@dataclass(frozen=True)
class SmtpSettings:
    """邮件告警配置，全部来自未提交的本地配置文件。"""

    host: str
    port: int
    use_ssl: bool
    username: str
    password: str
    recipients: tuple[str, ...]
    sender_name: str = "various-data scheduler"
    timeout_seconds: int = 10


@dataclass(frozen=True)
class Config:
    mode: str
    repo_root: Path
    db_path: Path
    ledger_path: Path
    log_dir: Path
    backup_dir: Path
    retry_max_attempts: int
    retry_interval_seconds: int
    smtp: SmtpSettings | None
    admin: AdminSettings = AdminSettings()


def now() -> datetime:
    """返回东八区当前时间，所有账本时间统一使用该时区。"""

    return datetime.now(TZ)


def to_iso(value: datetime) -> str:
    return value.isoformat(timespec="seconds")


def now_iso() -> str:
    return to_iso(now())


def _load_local_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"本地配置格式错误，应为映射: {path}")
    return data


def _build_smtp(raw: object) -> SmtpSettings | None:
    """缺少必要字段时返回 None，由告警模块降级为只记日志。"""

    if not isinstance(raw, dict):
        return None

    host = str(raw.get("host") or "").strip()
    username = str(raw.get("username") or "").strip()
    password = str(raw.get("password") or "")
    recipients = raw.get("recipients") or []
    if not isinstance(recipients, (list, tuple)):
        recipients = [recipients]
    recipients = tuple(str(item).strip() for item in recipients if str(item).strip())

    if not host or not username or not password or not recipients:
        return None

    try:
        port = int(raw.get("port", 465))
        timeout_seconds = int(raw.get("timeout_seconds", 10))
    except (TypeError, ValueError):
        return None

    return SmtpSettings(
        host=host,
        port=port,
        use_ssl=bool(raw.get("use_ssl", True)),
        username=username,
        password=password,
        recipients=recipients,
        sender_name=str(raw.get("sender_name") or "various-data scheduler"),
        timeout_seconds=timeout_seconds,
    )


def build_config(mode: str, admin: AdminSettings | None = None) -> Config:
    """按运行模式解析路径，规则与现有代码一致。"""

    if mode not in ("dev", "pro"):
        raise ValueError(f"不支持的运行模式: {mode}")

    data_dir = REPO_ROOT / "data"
    db_path = data_dir / ("various_data.db" if mode == "pro" else "various_data_dev.db")
    ledger_path = data_dir / (
        "scheduler.db" if mode == "pro" else "scheduler_dev.db"
    )

    local = _load_local_settings(LOCAL_CONFIG_PATH)

    retry_raw = local.get("retry")
    retry = retry_raw if isinstance(retry_raw, dict) else {}
    try:
        max_attempts = int(retry.get("max_attempts", DEFAULT_RETRY_MAX_ATTEMPTS))
        interval_seconds = int(
            retry.get("interval_seconds", DEFAULT_RETRY_INTERVAL_SECONDS)
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"本地配置 retry 字段格式错误: {exc}") from exc
    if max_attempts < 1:
        raise ValueError("retry.max_attempts 必须不小于 1")
    if interval_seconds < 0:
        raise ValueError("retry.interval_seconds 不能为负数")

    return Config(
        mode=mode,
        repo_root=REPO_ROOT,
        db_path=db_path,
        ledger_path=ledger_path,
        log_dir=REPO_ROOT / "log",
        backup_dir=REPO_ROOT / "backup",
        retry_max_attempts=max_attempts,
        retry_interval_seconds=interval_seconds,
        smtp=_build_smtp(local.get("smtp")),
        admin=admin or AdminSettings(),
    )


def describe_config(config: Config) -> str:
    """启动时打印的配置摘要，便于确认运行环境。"""

    smtp_state = "已配置" if config.smtp else "未配置（不发信）"
    return (
        f"mode={config.mode} 业务库={config.db_path} 账本={config.ledger_path} "
        f"日志目录={config.log_dir} 备份目录={config.backup_dir} "
        f"重试={config.retry_max_attempts} 次/{config.retry_interval_seconds} 秒 "
        f"SMTP={smtp_state} 管理服务={config.admin.describe()}"
    )
