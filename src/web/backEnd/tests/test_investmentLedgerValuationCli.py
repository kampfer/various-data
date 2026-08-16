"""受控估值命令与可替换后台任务的单元测试。"""

from __future__ import annotations

from contextlib import AbstractContextManager
import json
import logging

import pytest

from app.investmentLedger.valuation_ingest.cli import main
from app.investmentLedger.valuation_ingest.orchestrator import (
    CollectorRunResult,
    IngestRunReport,
)
from app.investmentLedger.valuation_ingest.tasks import (
    IngestTaskRequest,
    OrchestratorIngestTask,
)


class FakeTask:
    """记录 CLI 请求并返回预设报告的可替换后台任务实现。"""

    def __init__(self, report: IngestRunReport) -> None:
        self.report = report
        self.requests: list[IngestTaskRequest] = []

    def run(self, request: IngestTaskRequest) -> IngestRunReport:
        """保存请求以验证 CLI 仅传递受控字段。"""
        self.requests.append(request)
        return self.report


def testCliRunsTaskWithControlledKeysLogsJsonAndReturnsSuccess(caplog, capsys) -> None:
    """命令将产品/采集器标识交给任务，并输出不含原始载荷的审计结果。"""
    task = FakeTask(IngestRunReport((CollectorRunResult("trusted.fund", accepted=2),)))

    with caplog.at_level(logging.INFO):
        exitCode = main(
            ["--collector", "trusted.fund", "--product", "FUND:F-001"],
            task=task,
        )

    payload = json.loads(capsys.readouterr().out)
    assert exitCode == 0
    assert task.requests == [
        IngestTaskRequest((("FUND", "F-001"),), ("trusted.fund",))
    ]
    assert payload == {
        "accepted": 2,
        "collectors": [{
            "accepted": 2,
            "attempts": 0,
            "durationSeconds": 0.0,
            "error": None,
            "pluginId": "trusted.fund",
            "skipped": 0,
        }],
        "failed": 0,
        "skipped": 0,
    }
    assert "valuation_ingest_completed accepted=2 skipped=0 failed=0" in caplog.text


def testCliReturnsFailureWhenAnyCollectorIsIsolated(capsys) -> None:
    """编排器隔离失败会反映为非零命令状态，供运维或调度器重试。"""
    task = FakeTask(
        IngestRunReport((CollectorRunResult("trusted.fund", error="upstream timeout"),))
    )

    exitCode = main(["--product", "FUND:F-002"], task=task)

    assert exitCode == 1
    assert json.loads(capsys.readouterr().out)["failed"] == 1


def testCliRejectsUncontrolledAndMalformedArguments() -> None:
    """CLI 不接受单价覆盖参数，且产品键只能使用受控 TYPE:CODE 形式。"""
    with pytest.raises(SystemExit) as unknownOption:
        main(["--product", "FUND:F-003", "--unit-price", "99.99"])
    with pytest.raises(SystemExit) as malformedProduct:
        main(["--product", "FUND:F:003"])

    assert unknownOption.value.code == 2
    assert malformedProduct.value.code == 2


class FakeSession(AbstractContextManager[object]):
    """无数据库副作用的任务会话上下文，用于验证后台适配器装配顺序。"""

    def __init__(self) -> None:
        self.closed = False

    def __enter__(self) -> object:
        """返回仅供假编排器识别的会话对象。"""
        return self

    def __exit__(self, *args: object) -> None:
        """记录任务执行完成后会话已关闭。"""
        self.closed = True


class FakeRegistry:
    """记录受信发现步骤，且不提供任意路径加载能力。"""

    def __init__(self) -> None:
        self.discovered = False
        self.errors = ("rejected untrusted manifest",)

    def discover(self) -> list[object]:
        """模拟白名单发现。"""
        self.discovered = True
        return []


class FakeOrchestrator:
    """记录后台适配器传给编排器的受控运行参数。"""

    def __init__(self, registry: FakeRegistry) -> None:
        self.registry = registry
        self.calls: list[tuple[tuple[tuple[str, str], ...], tuple[str, ...] | None]] = []

    def run(
        self,
        productKeys: tuple[tuple[str, str], ...],
        collectorIds: tuple[str, ...] | None,
    ) -> IngestRunReport:
        """断言先完成受信发现，再模拟成功批次。"""
        assert self.registry.discovered is True
        self.calls.append((productKeys, collectorIds))
        return IngestRunReport((CollectorRunResult("trusted.fund", accepted=1),))


def testReplaceableTaskDiscoversTrustedCollectorsBeforeOrchestrating(caplog) -> None:
    """后台调度器可复用任务协议，而任务仍强制执行白名单发现和核心编排。"""
    session = FakeSession()
    registry = FakeRegistry()
    orchestrator = FakeOrchestrator(registry)
    task = OrchestratorIngestTask(
        sessionFactory=lambda: session,  # type: ignore[arg-type]
        registryFactory=lambda: registry,  # type: ignore[arg-type]
        orchestratorFactory=lambda db, registered: orchestrator,  # type: ignore[arg-type]
    )

    with caplog.at_level(logging.WARNING):
        report = task.run(IngestTaskRequest((("FUND", "F-004"),), None))

    assert report.accepted == 1
    assert session.closed is True
    assert orchestrator.calls == [((("FUND", "F-004"),), None)]
    assert "valuation_collector_discovery_rejected" in caplog.text
