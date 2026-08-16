"""估值采集器的稳定协议和值对象；本模块不依赖数据库。"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, Sequence, TypeAlias

from app.investmentLedger.constants import ProductType

# 产品键只由产品类型和代码组成；协议刻意不携带 Session、连接或写入回调。
ProductKey: TypeAlias = tuple[str, str]


@dataclass(frozen=True, slots=True)
class CollectorManifest:
    """采集器静态能力声明；plugin_id 和 version 组成注册身份。"""

    plugin_id: str
    version: str
    source_id: str
    product_types: frozenset[str]
    entrypoint: str
    enabled: bool = True


@dataclass(frozen=True, slots=True)
class StandardValuation:
    """经采集器返回、待核心再次标准化校验的估值值对象。"""

    product_type: str
    product_code: str
    valuation_date: date
    unit_price: Decimal
    source_id: str
    collected_at: datetime
    source_reference: str | None = None
    raw_payload_hash: str | None = None


class ValuationCollector(Protocol):
    """采集器协议；参数不包含 SQLAlchemy Session 或数据库对象。"""

    manifest: CollectorManifest

    def collect(
        self,
        product_keys: Sequence[ProductKey],
        *,
        timeout_seconds: float,
    ) -> list[StandardValuation]:
        """采集目标产品的原始标准候选结果。"""
        ...


SUPPORTED_PRODUCT_TYPES = frozenset(item.value for item in ProductType)
