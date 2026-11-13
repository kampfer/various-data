"""main() 装配顺序的单元测试：用假实现替换调度器与消费者。"""

from __future__ import annotations

import logging
from types import SimpleNamespace

import pytest

import scheduler.main as main_module


class FakeRunner:
    def __init__(self, store, registry, notifier, logger, events=None):
        self.events = events

    def start(self) -> None:
        assert self.events is not None
        self.events.append("runner.start")

    def stop(self) -> None:
        assert self.events is not None
        self.events.append("runner.stop")

    def wake(self) -> None:
        pass


class FakeSpec:
    id = "sina_news"
    name = "测试任务"
    max_attempts = 3
    retry_interval_seconds = 300

    def build_trigger(self) -> object:
        return object()

    def describe(self) -> str:
        return "测试任务"


class FakeScheduler:
    def __init__(self, job_defaults=None, timezone=None, events=None):
        self.events = events

    def add_job(self, *args, **kwargs) -> None:
        pass

    def start(self) -> None:
        assert self.events is not None
        self.events.append("scheduler.start")
        raise KeyboardInterrupt

    def shutdown(self, wait: bool = False) -> None:
        assert self.events is not None
        self.events.append("scheduler.shutdown")


class FakeStore:
    def __init__(self, path):
        self.path = path

    def recover_interrupted(self, at, error):
        return 0, 0

    def cleanup(self, cutoff, at):
        return 0

    def count_pending_retries(self):
        return 0


def _patch(monkeypatch: pytest.MonkeyPatch, events: list[str], captured: dict, admin_enabled: bool):
    def fake_build_config(mode, admin=None):
        from scheduler.config import AdminSettings, build_config as real_build_config

        return real_build_config(mode, AdminSettings(enabled=admin_enabled))

    monkeypatch.setattr(main_module, "Store", FakeStore)
    monkeypatch.setattr(
        main_module, "Runner", lambda *args, **kwargs: FakeRunner(*args, events=events, **kwargs)
    )
    monkeypatch.setattr(main_module, "Notifier", lambda smtp: object())
    monkeypatch.setattr(
        main_module, "run_catchup", lambda store, registry, notifier, at: SimpleNamespace(backfilled=0, lost=0)
    )
    monkeypatch.setattr(main_module, "build_registry", lambda config: [FakeSpec()])
    monkeypatch.setattr(
        main_module,
        "BlockingScheduler",
        lambda **kwargs: FakeScheduler(events=events, **kwargs),
    )
    monkeypatch.setattr(main_module, "setup_logging", lambda log_dir: logging.getLogger("test-main"))

    class FakeAdminServer:
        def __init__(self, app, settings, logger):
            captured["app"] = app
            captured["settings"] = settings
            self.events = events

        def start(self) -> None:
            self.events.append("admin.start")

        def stop(self) -> None:
            self.events.append("admin.stop")

    monkeypatch.setattr(main_module, "AdminServer", FakeAdminServer)
    monkeypatch.setattr(
        main_module,
        "create_app",
        lambda ctx: captured.update(context=ctx) or object(),
    )
    monkeypatch.setattr(
        main_module, "build_config", fake_build_config
    )


def test_main_starts_and_stops_components_in_order(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    captured: dict = {}
    _patch(monkeypatch, events, captured, admin_enabled=True)

    exit_code = main_module.main(["--mode", "dev"])

    assert exit_code == 0
    assert events == [
        "runner.start",
        "admin.start",
        "scheduler.start",
        "scheduler.shutdown",
        "runner.stop",
        "admin.stop",
    ]
    assert captured["context"].static_dir.name == "dist"
    assert captured["context"].static_dir.parent.name == "frontEnd"
    assert captured["settings"].port == 8787


def test_main_no_admin_skips_admin_server(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    captured: dict = {}
    _patch(monkeypatch, events, captured, admin_enabled=False)

    exit_code = main_module.main(["--mode", "dev", "--no-admin"])

    assert exit_code == 0
    assert "admin.start" not in events
    assert "context" not in captured
