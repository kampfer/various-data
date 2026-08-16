"""受控估值摄取任务适配器；可由命令或后续后台调度器复用。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
import logging
from typing import Protocol

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.investmentLedger.constants import MAX_PRODUCT_CODE_LENGTH, SOURCE_PRIORITY
from .orchestrator import CollectorOrchestrator, IngestRunReport
from .protocol import ProductKey
from .registry import CollectorRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class IngestTaskRequest:
    """命令或后台任务可提交的受控采集请求；不包含单价、来源或数据库能力。"""

    product_keys: tuple[ProductKey, ...]
    collector_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        """拒绝空目标、未知产品类型和超长/空白产品代码。"""
        supportedTypes = {"WEALTH", "FUND", "STOCK"}
        if not self.product_keys:
            raise ValueError("至少指定一个产品键")
        for productType, productCode in self.product_keys:
            if productType not in supportedTypes:
                raise ValueError("产品类型必须是 WEALTH、FUND 或 STOCK")
            if not productCode or productCode != productCode.strip():
                raise ValueError("产品代码不能为空或包含首尾空白")
            if len(productCode) > MAX_PRODUCT_CODE_LENGTH:
                raise ValueError(f"产品代码长度不能超过 {MAX_PRODUCT_CODE_LENGTH}")
        if self.collector_ids is not None and not self.collector_ids:
            raise ValueError("采集器筛选不能为空")


class ValuationIngestTask(Protocol):
    """可替换任务抽象；调度器只需调用 run，不需要了解 CLI 或数据库细节。"""

    def run(self, request: IngestTaskRequest) -> IngestRunReport:
        """执行一次受控采集并返回可审计报告。"""
        ...


class OrchestratorIngestTask:
    """把受控任务请求装配为白名单发现和编排器执行。"""

    def __init__(
        self,
        *,
        sessionFactory: Callable[[], AbstractContextManager[Session]] = SessionLocal,
        registryFactory: Callable[[], CollectorRegistry] | None = None,
        orchestratorFactory: Callable[[Session, CollectorRegistry], CollectorOrchestrator]
        | None = None,
    ) -> None:
        """注入基础设施工厂，以便命令和后台运行器共享同一链路并可独立测试。"""
        self._sessionFactory = sessionFactory
        self._registryFactory = registryFactory or self._buildRegistry
        self._orchestratorFactory = orchestratorFactory or self._buildOrchestrator

    @staticmethod
    def _buildRegistry() -> CollectorRegistry:
        """以与读取层一致的核心来源优先级创建白名单注册表。"""
        return CollectorRegistry(sourcePriority=SOURCE_PRIORITY)

    @staticmethod
    def _buildOrchestrator(
        db: Session,
        registry: CollectorRegistry,
    ) -> CollectorOrchestrator:
        """使用核心来源优先级构造内部编排器，不接受调用方覆盖。"""
        return CollectorOrchestrator(db, registry, sourcePriority=SOURCE_PRIORITY)

    def run(self, request: IngestTaskRequest) -> IngestRunReport:
        """发现受信插件后运行采集；发现错误只记录，不加载非受信插件。"""
        registry = self._registryFactory()
        registry.discover()
        for error in registry.errors:
            logger.warning("valuation_collector_discovery_rejected error=%s", error)
        with self._sessionFactory() as db:
            return self._orchestratorFactory(db, registry).run(
                request.product_keys,
                request.collector_ids,
            )
