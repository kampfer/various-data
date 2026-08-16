"""估值采集任务编排：能力匹配、超时、重试、失败隔离和仓储提交。"""

from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from time import monotonic, sleep
from uuid import uuid4

from sqlalchemy.orm import Session

from .normalizer import ValuationNormalizer
from .protocol import StandardValuation, ValuationCollector
from .registry import CollectorRegistry
from .repository import ValuationRepository

logger = logging.getLogger(__name__)


class CollectorExecutionTimeoutError(TimeoutError):
    """采集器未在核心规定的有限时间内完成时抛出的隔离错误。"""


class CollectorExecutionFailure(Exception):
    """保留最终采集错误和实际尝试次数，供隔离报告记录。"""

    def __init__(self, error: Exception, attempts: int) -> None:
        super().__init__(str(error))
        self.error = error
        self.attempts = attempts


@dataclass(frozen=True, slots=True)
class CollectorRunResult:
    """单个采集器的隔离执行结果；次数和耗时便于内部审计。"""

    plugin_id: str
    accepted: int = 0
    skipped: int = 0
    error: str | None = None
    attempts: int = 0
    duration_seconds: float = 0.0


@dataclass(frozen=True, slots=True)
class IngestRunReport:
    """一次命令触发的全局结果；一个插件失败不影响其它插件。"""

    results: tuple[CollectorRunResult, ...] = field(default_factory=tuple)

    @property
    def accepted(self) -> int:
        """返回所有采集器成功落库的结果数。"""
        return sum(result.accepted for result in self.results)


class CollectorOrchestrator:
    """内部估值摄取编排器，不依赖 FastAPI 路由或采集器数据库能力。"""

    def __init__(
        self,
        db: Session,
        registry: CollectorRegistry,
        *,
        sourcePriority: dict[str, int] | None = None,
        normalizer: ValuationNormalizer | None = None,
        repository: ValuationRepository | None = None,
        timeoutSeconds: float = 10.0,
        maxRetries: int = 2,
        retryBackoffSeconds: float = 0.1,
        sleepFn: Callable[[float], None] = sleep,
    ) -> None:
        """装配受控依赖和有限的超时/重试策略。

        ``sleepFn`` 仅是内部退避策略的可替换时钟，不会传递给采集器；采集器仍只
        接收协议中定义的产品键与 ``timeout_seconds``，因而不能获得数据库写能力。
        """
        if timeoutSeconds <= 0:
            raise ValueError("采集超时时间必须大于 0")
        if maxRetries < 0:
            raise ValueError("采集重试次数不能小于 0")
        if retryBackoffSeconds < 0:
            raise ValueError("采集重试退避时间不能小于 0")
        self._registry = registry
        self._sourcePriority = sourcePriority or {}
        self._normalizer = normalizer or ValuationNormalizer()
        self._repository = repository or ValuationRepository(db)
        self._timeoutSeconds = timeoutSeconds
        self._maxRetries = maxRetries
        self._retryBackoffSeconds = retryBackoffSeconds
        self._sleepFn = sleepFn

    def _collectWithinTimeout(
        self,
        collector: ValuationCollector,
        productKeys: Sequence[tuple[str, str]],
    ) -> list[StandardValuation]:
        """用独立工作线程施加硬超时，不允许失效插件阻断后续批次。

        ``Future.cancel`` 无法终止已经开始的第三方 I/O；因此采集器还必须使用核心
        传入的 ``timeout_seconds`` 限制自身 HTTP 请求。这里的超时保护确保编排线程
        立即继续调度其它受信采集器，不等待失效插件结束。
        """
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="valuation-collector")
        future: Future[list[StandardValuation]] = executor.submit(
            collector.collect,
            productKeys,
            timeout_seconds=self._timeoutSeconds,
        )
        try:
            values = future.result(timeout=self._timeoutSeconds)
        except FutureTimeoutError as error:
            future.cancel()
            raise CollectorExecutionTimeoutError(
                f"采集器超过 {self._timeoutSeconds:g} 秒未完成"
            ) from error
        finally:
            # 不等待无法取消的外部 I/O；其结果从不进入后续标准化或写入阶段。
            executor.shutdown(wait=False, cancel_futures=True)
        if not isinstance(values, list):
            raise TypeError("采集器返回值必须是 list")
        return values

    @staticmethod
    def _isRetryable(error: Exception) -> bool:
        """仅将暂时性网络/超时错误纳入有限重试，解析和校验错误不会重试。"""
        return isinstance(error, (CollectorExecutionTimeoutError, ConnectionError, OSError))

    def _collectWithRetries(
        self,
        collector: ValuationCollector,
        productKeys: Sequence[tuple[str, str]],
        *,
        runId: str,
    ) -> tuple[list[StandardValuation], int]:
        """执行一个插件的有限次数采集，并只对暂时性错误执行线性退避。"""
        maxAttempts = self._maxRetries + 1
        for attempt in range(1, maxAttempts + 1):
            try:
                return self._collectWithinTimeout(collector, productKeys), attempt
            except Exception as error:
                if not self._isRetryable(error) or attempt == maxAttempts:
                    raise CollectorExecutionFailure(error, attempt) from error
                delay = self._retryBackoffSeconds * attempt
                logger.warning(
                    "collector_retry run_id=%s plugin_id=%s phase=collect attempt=%s "
                    "max_attempts=%s delay_seconds=%s error=%s",
                    runId,
                    collector.manifest.plugin_id,
                    attempt,
                    maxAttempts,
                    delay,
                    error,
                )
                if delay:
                    self._sleepFn(delay)
        raise RuntimeError("采集器重试流程未返回结果")

    def _runCollector(
        self,
        collector: ValuationCollector,
        supportedKeys: Sequence[tuple[str, str]],
        *,
        now: datetime,
        runId: str,
    ) -> CollectorRunResult:
        """隔离一个插件从采集、标准化到独立事务写入的全部失败。"""
        pluginId = collector.manifest.plugin_id
        startedAt = monotonic()
        attempts = 0
        logger.info(
            "collector_batch_start run_id=%s plugin_id=%s phase=collect target_count=%s",
            runId,
            pluginId,
            len(supportedKeys),
        )
        try:
            rawValues, attempts = self._collectWithRetries(
                collector,
                supportedKeys,
                runId=runId,
            )
            normalized: list[StandardValuation] = []
            skipped = 0
            for rawValue in rawValues:
                try:
                    normalized.append(
                        self._normalizer.normalize(rawValue, collector.manifest, now=now)
                    )
                except Exception as error:
                    skipped += 1
                    logger.warning(
                        "collector_value_rejected run_id=%s plugin_id=%s phase=normalize "
                        "source_reference=%s error=%s",
                        runId,
                        pluginId,
                        getattr(rawValue, "source_reference", None),
                        error,
                    )
            if not normalized:
                return CollectorRunResult(
                    plugin_id=pluginId,
                    skipped=skipped,
                    attempts=attempts,
                    duration_seconds=monotonic() - startedAt,
                )
            ingest = self._repository.ingestBatch(normalized, self._sourcePriority)
            return CollectorRunResult(
                plugin_id=pluginId,
                accepted=ingest.accepted,
                skipped=skipped + ingest.skipped,
                attempts=attempts,
                duration_seconds=monotonic() - startedAt,
            )
        except CollectorExecutionFailure as failure:
            logger.exception(
                "collector_batch_failed run_id=%s plugin_id=%s phase=collect "
                "attempts=%s error=%s",
                runId,
                pluginId,
                failure.attempts,
                failure.error,
            )
            return CollectorRunResult(
                plugin_id=pluginId,
                error=str(failure.error),
                attempts=failure.attempts,
                duration_seconds=monotonic() - startedAt,
            )
        except Exception as error:
            logger.exception(
                "collector_batch_failed run_id=%s plugin_id=%s phase=normalize-or-ingest "
                "attempts=%s error=%s",
                runId,
                pluginId,
                attempts,
                error,
            )
            return CollectorRunResult(
                plugin_id=pluginId,
                error=str(error),
                attempts=attempts,
                duration_seconds=monotonic() - startedAt,
            )
        finally:
            logger.info(
                "collector_batch_end run_id=%s plugin_id=%s duration_seconds=%.6f",
                runId,
                pluginId,
                monotonic() - startedAt,
            )

    def run(
        self,
        productKeys: Sequence[tuple[str, str]],
        collectorIds: Iterable[str] | None = None,
    ) -> IngestRunReport:
        """按 manifest 能力派发目标，隔离每个采集器的失败并继续后续批次。"""
        now = datetime.now(timezone.utc)
        runId = uuid4().hex
        results: list[CollectorRunResult] = []
        for collector in self._registry.select(collectorIds):
            supportedKeys = [
                key for key in productKeys if key[0] in collector.manifest.product_types
            ]
            if not supportedKeys:
                results.append(CollectorRunResult(collector.manifest.plugin_id))
                continue
            results.append(
                self._runCollector(collector, supportedKeys, now=now, runId=runId)
            )
        return IngestRunReport(results=tuple(results))
