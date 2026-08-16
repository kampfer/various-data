"""估值结果标准化和业务边界校验；本模块不访问仓储或数据库。"""

from datetime import date, datetime, timezone
from decimal import Decimal

from app.investmentLedger.constants import MAX_PRODUCT_CODE_LENGTH, MAX_VALUATION_UNIT_PRICE
from .protocol import CollectorManifest, StandardValuation, SUPPORTED_PRODUCT_TYPES


class ValuationNormalizationError(ValueError):
    """单条估值结果不符合核心标准时抛出的可隔离异常。"""


class ValuationNormalizer:
    """把采集器候选结果转换为可写入的标准值对象（需求 3.12）。"""

    MAX_REFERENCE_LENGTH = 512
    MAX_HASH_LENGTH = 128

    @staticmethod
    def _validateAuditText(
        value: object,
        *,
        fieldName: str,
        maximumLength: int,
    ) -> str | None:
        """验证可空审计文本：必须是非空、无控制字符且未超长的字符串。"""
        if value is None:
            return None
        if not isinstance(value, str) or not value.strip():
            raise ValuationNormalizationError(f"{fieldName}格式无效")
        if len(value) > maximumLength:
            raise ValuationNormalizationError(f"{fieldName}过长")
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValuationNormalizationError(f"{fieldName}包含控制字符")
        return value

    @staticmethod
    def _normalizeCollectedAt(collectedAt: object, now: datetime) -> datetime:
        """把采集时间转换为 UTC 感知时间，并拒绝未来时间或错误类型。"""
        if not isinstance(collectedAt, datetime):
            raise ValuationNormalizationError("采集时间格式无效")
        normalized = (
            collectedAt.replace(tzinfo=timezone.utc)
            if collectedAt.tzinfo is None
            else collectedAt.astimezone(timezone.utc)
        )
        current = now.replace(tzinfo=timezone.utc) if now.tzinfo is None else now.astimezone(timezone.utc)
        if normalized > current:
            raise ValuationNormalizationError("采集时间不能晚于当前时间")
        return normalized

    def normalize(
        self,
        value: StandardValuation,
        manifest: CollectorManifest,
        *,
        now: datetime | None = None,
    ) -> StandardValuation:
        """逐字段校验候选结果，绝不静默舍入超过两位的小数。"""
        if not isinstance(value, StandardValuation):
            raise ValuationNormalizationError("采集器返回值必须是 StandardValuation")
        if not isinstance(manifest, CollectorManifest):
            raise ValuationNormalizationError("采集器 manifest 类型无效")
        if value.product_type not in SUPPORTED_PRODUCT_TYPES:
            raise ValuationNormalizationError("不支持的产品类型")
        if value.product_type not in manifest.product_types:
            raise ValuationNormalizationError("采集器不具备该产品类型能力")
        if (
            not isinstance(value.product_code, str)
            or not value.product_code.strip()
            or len(value.product_code) > MAX_PRODUCT_CODE_LENGTH
        ):
            raise ValuationNormalizationError("产品代码长度无效")
        if value.source_id != manifest.source_id:
            raise ValuationNormalizationError("估值来源与采集器声明不一致")
        if type(value.valuation_date) is not date:
            raise ValuationNormalizationError("估值日期无效")
        if not isinstance(value.unit_price, Decimal) or not value.unit_price.is_finite():
            raise ValuationNormalizationError("估值单价必须是有限十进制数")
        if value.unit_price <= 0 or value.unit_price > Decimal(MAX_VALUATION_UNIT_PRICE):
            raise ValuationNormalizationError("估值单价超出有效范围")
        if value.unit_price.as_tuple().exponent < -2:
            raise ValuationNormalizationError("估值单价的小数位不能超过两位")
        current = now or datetime.now(timezone.utc)
        collectedAt = self._normalizeCollectedAt(value.collected_at, current)
        reference = self._validateAuditText(
            value.source_reference,
            fieldName="来源引用",
            maximumLength=self.MAX_REFERENCE_LENGTH,
        )
        payloadHash = self._validateAuditText(
            value.raw_payload_hash,
            fieldName="原始数据摘要",
            maximumLength=self.MAX_HASH_LENGTH,
        )
        return StandardValuation(
            product_type=value.product_type,
            product_code=value.product_code,
            valuation_date=value.valuation_date,
            unit_price=value.unit_price.quantize(Decimal("0.01")),
            source_id=value.source_id,
            collected_at=collectedAt,
            source_reference=reference,
            raw_payload_hash=payloadHash,
        )
