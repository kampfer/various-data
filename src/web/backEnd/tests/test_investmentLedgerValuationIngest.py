"""受控估值摄取链路集成测试：只使用 fake collector 和临时 SQLite。"""

from contextlib import nullcontext
from datetime import date, datetime, timezone
from decimal import Decimal
import importlib
import json
from pathlib import Path
from typing import Sequence

import pytest
from sqlalchemy import select

from app.investmentLedger.models import Base, Valuation
from app.investmentLedger.valuation_ingest.cli import main
from app.investmentLedger.valuation_ingest.normalizer import (
    ValuationNormalizationError,
    ValuationNormalizer,
)
from app.investmentLedger.valuation_ingest.orchestrator import CollectorOrchestrator
from app.investmentLedger.valuation_ingest.protocol import CollectorManifest, StandardValuation
from app.investmentLedger.valuation_ingest.registry import (
    CollectorRegistrationError,
    CollectorRegistry,
)
from app.investmentLedger.valuation_ingest.tasks import OrchestratorIngestTask


class FakeCollector:
    """不访问网络的协议采集器，用固定标准候选模拟外部来源。"""

    def __init__(self, sourceId: str, price: str) -> None:
        self.manifest = CollectorManifest(
            plugin_id=f"fake.{sourceId}",
            version="1.0.0",
            source_id=sourceId,
            product_types=frozenset({"FUND"}),
            entrypoint="app.investmentLedger.collectors.fake:create",
        )
        self._price = Decimal(price)

    def collect(
        self,
        product_keys: Sequence[tuple[str, str]],
        *,
        timeout_seconds: float,
    ) -> list[StandardValuation]:
        return [
            StandardValuation(
                product_type=productType,
                product_code=productCode,
                valuation_date=date(2024, 6, 30),
                unit_price=self._price,
                source_id=self.manifest.source_id,
                collected_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
            )
            for productType, productCode in product_keys
        ]


def testCommandChainNormalizesAndIdempotentlyPersistsValues(dbSession, tempEngine) -> None:
    """注册表→编排器→标准化→仓储可重复执行且账本只读可读取。"""
    Base.metadata.create_all(bind=tempEngine)
    registry = CollectorRegistry([FakeCollector("preferred", "12.3")])
    orchestrator = CollectorOrchestrator(
        dbSession,
        registry,
        sourcePriority={"preferred": 1},
    )

    first = orchestrator.run([("FUND", "F-001")])
    second = orchestrator.run([("FUND", "F-001")])

    assert first.accepted == 1
    assert second.accepted == 1
    rows = dbSession.scalars(select(Valuation)).all()
    assert len(rows) == 1
    assert rows[0].unit_price == Decimal("12.30")
    assert rows[0].source_id == "preferred"


def testControlledCommandRunsRegisteredCollectorAndExposesReadOnlyValuation(
    dbSession, tempEngine, capsys
) -> None:
    """命令经任务装配完整摄取链路，账本仍仅由只读查询消费结果。"""
    Base.metadata.create_all(bind=tempEngine)
    sourcePriority = {"command-source": 1}
    task = OrchestratorIngestTask(
        sessionFactory=lambda: nullcontext(dbSession),
        registryFactory=lambda: CollectorRegistry(
            [FakeCollector("command-source", "15.20")],
            sourcePriority=sourcePriority,
        ),
        orchestratorFactory=lambda db, registry: CollectorOrchestrator(
            db,
            registry,
            sourcePriority=sourcePriority,
        ),
    )

    exitCode = main(
        ["--collector", "fake.command-source", "--product", "FUND:F-COMMAND"],
        task=task,
    )

    from app.investmentLedger.crud import getLatestValuations

    payload = json.loads(capsys.readouterr().out)
    selected = getLatestValuations(
        dbSession,
        [("FUND", "F-COMMAND")],
        sourcePriority,
    )
    assert exitCode == 0
    assert payload["accepted"] == 1
    assert selected[("FUND", "F-COMMAND")].source_id == "command-source"
    assert selected[("FUND", "F-COMMAND")].unit_price == Decimal("15.20")


def testSourcePriorityIsConsumedByReadPathWithoutChangingLedgerService(
    dbSession, tempEngine
) -> None:
    """新增来源只注册采集器；账本读取仍由既有来源优先级选择。"""
    Base.metadata.create_all(bind=tempEngine)
    registry = CollectorRegistry([
        FakeCollector("fallback", "10.00"),
        FakeCollector("preferred", "12.00"),
    ])
    CollectorOrchestrator(
        dbSession,
        registry,
        sourcePriority={"preferred": 1, "fallback": 2},
    ).run([("FUND", "F-002")])

    from app.investmentLedger.crud import getLatestValuations

    selected = getLatestValuations(
        dbSession,
        [("FUND", "F-002")],
        {"preferred": 1, "fallback": 2},
    )
    assert selected[("FUND", "F-002")].source_id == "preferred"
    assert selected[("FUND", "F-002")].unit_price == Decimal("12.00")


def testNormalizerPreservesValidDecimalDateAndUtcMetadata() -> None:
    """一位小数补零，日期与 UTC 采集时间保持为标准值对象字段。"""
    manifest = FakeCollector("source", "12.3").manifest
    normalized = ValuationNormalizer().normalize(
        StandardValuation(
            product_type="FUND",
            product_code="F-003",
            valuation_date=date(2024, 6, 30),
            unit_price=Decimal("12.3"),
            source_id="source",
            collected_at=datetime(2024, 7, 1),
            source_reference="https://example.test/value/F-003",
            raw_payload_hash="a" * 64,
        ),
        manifest,
        now=datetime(2024, 7, 2, tzinfo=timezone.utc),
    )

    assert normalized.unit_price == Decimal("12.30")
    assert normalized.valuation_date == date(2024, 6, 30)
    assert normalized.collected_at.tzinfo == timezone.utc


def testNormalizerRejectsExcessScaleAndInvalidAuditMetadata() -> None:
    """超过两位小数或带控制字符的审计字段必须逐条拒绝。"""
    manifest = FakeCollector("source", "12.3").manifest
    normalizer = ValuationNormalizer()
    with pytest.raises(ValuationNormalizationError, match="小数位"):
        normalizer.normalize(
            StandardValuation(
                product_type="FUND",
                product_code="F-004",
                valuation_date=date(2024, 6, 30),
                unit_price=Decimal("12.345"),
                source_id="source",
                collected_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
            ),
            manifest,
            now=datetime(2024, 7, 2, tzinfo=timezone.utc),
        )
    with pytest.raises(ValuationNormalizationError, match="控制字符"):
        normalizer.normalize(
            StandardValuation(
                product_type="FUND",
                product_code="F-004",
                valuation_date=date(2024, 6, 30),
                unit_price=Decimal("12.34"),
                source_id="source",
                collected_at=datetime(2024, 7, 1, tzinfo=timezone.utc),
                source_reference="reference\ninvalid",
            ),
            manifest,
            now=datetime(2024, 7, 2, tzinfo=timezone.utc),
        )


class InvalidCollector(FakeCollector):
    """返回非法三位小数，用于验证摄取前的写入边界。"""

    def __init__(self) -> None:
        super().__init__("invalid", "12.345")


class RecordingRepository:
    """若标准化失败后仍尝试写入，本测试替身会立即使测试失败。"""

    def ingestBatch(self, values: object, sourcePriority: object) -> object:
        raise AssertionError("非法估值不应触发仓储写入")


def testInvalidCollectorResultDoesNotCallRepository() -> None:
    """全部候选非法时，编排器只计跳过数，不调用受控仓储。"""
    collector = InvalidCollector()
    report = CollectorOrchestrator(
        None,  # type: ignore[arg-type]
        CollectorRegistry([collector]),
        repository=RecordingRepository(),  # type: ignore[arg-type]
    ).run([("FUND", "F-005")])

    assert report.accepted == 0
    assert report.results[0].skipped == 1


def _writeTrustedPlugin(directory: Path, *, sourceId: str = "trusted") -> None:
    """构造最小受信包和静态 manifest，不访问任何外部服务。"""
    (directory / "manifests").mkdir(parents=True)
    (directory / "__init__.py").write_text("", encoding="utf-8")
    (directory / "collector.py").write_text(
        "from app.investmentLedger.valuation_ingest.protocol import CollectorManifest\n"
        "\n"
        "class Plugin:\n"
        "    manifest = CollectorManifest(\n"
        "        plugin_id='trusted.plugin', version='1.0.0', source_id='"
        + sourceId
        + "', product_types=frozenset({'FUND'}), "
        "entrypoint='trusted_plugins.collector:create'\n"
        "    )\n"
        "    def collect(self, product_keys, *, timeout_seconds):\n"
        "        return []\n"
        "\n"
        "def create():\n"
        "    return Plugin()\n",
        encoding="utf-8",
    )
    (directory / "manifests" / "trusted.json").write_text(
        json.dumps(
            {
                "plugin_id": "trusted.plugin",
                "version": "1.0.0",
                "source_id": sourceId,
                "product_types": ["FUND"],
                "entrypoint": "trusted_plugins.collector:create",
            }
        ),
        encoding="utf-8",
    )


def testRegistryDiscoversOnlyTrustedManifestAndRecordsMetadata(tmp_path, monkeypatch) -> None:
    """显式受信目录可加载且登记路径/优先级；目录外入口会被拒绝。"""
    directory = tmp_path / "trusted_plugins"
    _writeTrustedPlugin(directory)
    monkeypatch.syspath_prepend(str(tmp_path))
    importlib.invalidate_caches()
    registry = CollectorRegistry(
        trustedDirectories=[directory],
        sourcePriority={"trusted": 1},
    )

    discovered = registry.discover()

    assert [item.manifest.plugin_id for item in discovered] == ["trusted.plugin"]
    assert registry.metadata[0].manifest_path == (directory / "manifests" / "trusted.json")
    assert registry.metadata[0].source_priority == 1
    assert registry.get("trusted.plugin").manifest.source_id == "trusted"


def testRegistryRejectsDuplicateActiveSourcePriorities() -> None:
    """不同启用来源共享核心优先级会在注册阶段失败。"""
    registry = CollectorRegistry(sourcePriority={"one": 1, "two": 1})
    registry.register(FakeCollector("one", "1.00"))

    with pytest.raises(CollectorRegistrationError, match="优先级冲突"):
        registry.register(FakeCollector("two", "1.00"))


class RecordingCollector(FakeCollector):
    """记录核心按 manifest 能力筛选后实际派发的产品键。"""

    def __init__(self, sourceId: str, price: str) -> None:
        super().__init__(sourceId, price)
        self.receivedKeys: list[tuple[str, str]] = []

    def collect(
        self,
        product_keys: Sequence[tuple[str, str]],
        *,
        timeout_seconds: float,
    ) -> list[StandardValuation]:
        self.receivedKeys.extend(product_keys)
        return super().collect(product_keys, timeout_seconds=timeout_seconds)


class TransientFailureCollector(FakeCollector):
    """前一次网络异常、后一次成功，用于验证有限重试。"""

    def __init__(self, sourceId: str, price: str) -> None:
        super().__init__(sourceId, price)
        self.calls = 0

    def collect(
        self,
        product_keys: Sequence[tuple[str, str]],
        *,
        timeout_seconds: float,
    ) -> list[StandardValuation]:
        self.calls += 1
        if self.calls == 1:
            raise ConnectionError("temporary network failure")
        return super().collect(product_keys, timeout_seconds=timeout_seconds)


class ParseFailureCollector(FakeCollector):
    """不可恢复的解析异常不应重试，但必须被单插件隔离。"""

    def __init__(self, sourceId: str, price: str) -> None:
        super().__init__(sourceId, price)
        self.calls = 0

    def collect(
        self,
        product_keys: Sequence[tuple[str, str]],
        *,
        timeout_seconds: float,
    ) -> list[StandardValuation]:
        self.calls += 1
        raise ValueError("invalid upstream payload")


class TimeoutCollector(FakeCollector):
    """故意忽略建议超时，验证编排器的硬超时仍可继续其它批次。"""

    def __init__(self, sourceId: str, price: str) -> None:
        super().__init__(sourceId, price)
        self.calls = 0

    def collect(
        self,
        product_keys: Sequence[tuple[str, str]],
        *,
        timeout_seconds: float,
    ) -> list[StandardValuation]:
        from time import sleep

        self.calls += 1
        sleep(0.2)
        return super().collect(product_keys, timeout_seconds=timeout_seconds)


def testOrchestratorRetriesTimeoutsAndIsolatesFailedCollectors(dbSession, tempEngine) -> None:
    """能力匹配、有限重试、超时和解析失败均不得阻断其它批次落库。"""
    from time import monotonic

    Base.metadata.create_all(bind=tempEngine)
    successful = RecordingCollector("success", "10.00")
    transient = TransientFailureCollector("retry", "11.00")
    parseFailure = ParseFailureCollector("parse", "12.00")
    timeout = TimeoutCollector("timeout", "13.00")
    orchestrator = CollectorOrchestrator(
        dbSession,
        CollectorRegistry([successful, transient, parseFailure, timeout]),
        timeoutSeconds=0.005,
        maxRetries=1,
        retryBackoffSeconds=0,
    )

    startedAt = monotonic()
    report = orchestrator.run([("FUND", "F-006"), ("STOCK", "S-001")])
    elapsed = monotonic() - startedAt
    results = {result.plugin_id: result for result in report.results}

    assert successful.receivedKeys == [("FUND", "F-006")]
    assert report.accepted == 2
    assert results[successful.manifest.plugin_id].accepted == 1
    assert results[transient.manifest.plugin_id].accepted == 1
    assert results[transient.manifest.plugin_id].attempts == 2
    assert transient.calls == 2
    assert results[parseFailure.manifest.plugin_id].error == "invalid upstream payload"
    assert results[parseFailure.manifest.plugin_id].attempts == 1
    assert parseFailure.calls == 1
    assert "超过" in (results[timeout.manifest.plugin_id].error or "")
    assert results[timeout.manifest.plugin_id].attempts == 2
    assert timeout.calls == 2
    assert elapsed < 0.1
    assert len(dbSession.scalars(select(Valuation)).all()) == 2
