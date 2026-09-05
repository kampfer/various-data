"""基金收益计算所需的行情与公司行为数据服务。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.investmentLedger.cache_proxy import CacheManager, CacheProxy
from app.investmentLedger.fund_performance import FundDividend, FundSplit


@dataclass(frozen=True, slots=True)
class FundPerformanceData:
    """由基金详情接口提供的收益计算输入。"""

    unit_nav: Decimal | None
    valuation_date: date | None
    dividends: tuple[FundDividend, ...] = ()
    splits: tuple[FundSplit, ...] = ()


class AkshareFundQuoteClient:
    """调用 akshare 基金详情接口。"""

    def fetchFundInfoEm(
        self,
        symbol: str,
        indicator: str,
        period: str = "成立来",
    ) -> Any:
        """读取基金单位净值走势、分红或拆分详情。"""
        import akshare as ak

        return ak.fund_open_fund_info_em(
            symbol=symbol,
            indicator=indicator,
            period=period,
        )


class FundQuoteService:
    """从基金详情接口装配 FundPerformanceCalculator 所需的数据。"""

    UNIT_NAV_INDICATOR = "单位净值走势"
    DIVIDEND_INDICATOR = "分红送配详情"
    SPLIT_INDICATOR = "拆分详情"

    def __init__(self, client: AkshareFundQuoteClient | None = None) -> None:
        """装配可替换的 akshare 客户端并缓存详情接口结果。"""
        self._client = CacheProxy(
            client or AkshareFundQuoteClient(),
            CacheManager(),
            {"fetchFundInfoEm": 6 * 60 * 60},
        )

    def getPerformanceData(
        self,
        fundCodes: list[str],
    ) -> dict[str, FundPerformanceData]:
        """读取并标准化指定基金的最新净值、分红和拆分数据。"""
        result: dict[str, FundPerformanceData] = {}
        for fundCode in dict.fromkeys(fundCodes):
            unitNav, valuationDate = self._normalizeUnitNav(
                self._fetchIndicator(fundCode, self.UNIT_NAV_INDICATOR)
            )
            dividends = tuple(
                self._normalizeDividends(
                    self._fetchIndicator(fundCode, self.DIVIDEND_INDICATOR)
                )
            )
            splits = tuple(
                self._normalizeSplits(
                    self._fetchIndicator(fundCode, self.SPLIT_INDICATOR)
                )
            )
            result[fundCode] = FundPerformanceData(
                unit_nav=unitNav,
                valuation_date=valuationDate,
                dividends=dividends,
                splits=splits,
            )
        return result

    def _fetchIndicator(self, fundCode: str, indicator: str) -> Any:
        """获取单项基金详情并收敛第三方异常。"""
        try:
            return self._client.fetchFundInfoEm(fundCode, indicator)
        except Exception:
            return []

    @staticmethod
    def _records(value: Any) -> list[dict[str, Any]]:
        """将 akshare DataFrame 或测试替身转换成字典列表。"""
        if value is None:
            return []
        if hasattr(value, "to_dict"):
            value = value.to_dict(orient="records")
        elif isinstance(value, dict):
            value = [value]
        if not isinstance(value, (list, tuple)):
            return []
        return [item for item in value if isinstance(item, dict)]

    @staticmethod
    def _firstValue(row: dict[str, Any], keys: tuple[str, ...]) -> Any:
        """按字段别名读取第一个非空值。"""
        for key in keys:
            if key in row and row[key] is not None:
                return row[key]
        return None

    @classmethod
    def _normalizeUnitNav(cls, value: Any) -> tuple[Decimal | None, date | None]:
        """从单位净值走势中选取日期最新且数据完整的一条记录。"""
        candidates: list[tuple[date, Decimal]] = []
        for row in cls._records(value):
            valuationDate = cls._dateValue(
                cls._firstValue(row, ("净值日期", "日期", "valuation_date"))
            )
            unitNav = cls._decimalValue(
                cls._firstValue(row, ("单位净值", "unit_nav", "nav"))
            )
            if valuationDate is not None and unitNav is not None:
                candidates.append((valuationDate, unitNav))
        if not candidates:
            return None, None
        valuationDate, unitNav = max(candidates, key=lambda item: item[0])
        return unitNav, valuationDate

    @staticmethod
    def _dateValue(value: Any) -> date | None:
        """解析 akshare 日期字段。"""
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if value is None:
            return None
        text = str(value).strip().replace("/", "-")
        if not text or text in {"-", "nan", "NaT", "None"}:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None

    @staticmethod
    def _decimalValue(value: Any) -> Decimal | None:
        """将第三方金额或比例转换成有限 Decimal。"""
        if value is None:
            return None
        try:
            parsed = Decimal(str(value).strip().replace("%", ""))
        except (InvalidOperation, ValueError):
            return None
        return parsed if parsed.is_finite() else None

    @classmethod
    def _normalizeDividends(cls, value: Any) -> list[FundDividend]:
        """标准化分红事件并转换为每份金额。"""
        result: list[FundDividend] = []
        for row in cls._records(value):
            exDate = cls._dateValue(
                cls._firstValue(row, ("除息日", "ex_date"))
            )
            perTenSharesAmount = row.get("每10份分红")
            amountPerShareSource = (
                perTenSharesAmount
                if perTenSharesAmount is not None
                else cls._firstValue(
                    row,
                    ("每份分红", "分红金额", "amount_per_share"),
                )
            )
            amountPerShare = cls._decimalValue(amountPerShareSource)
            if exDate is None or amountPerShare is None:
                continue
            if perTenSharesAmount is not None:
                amountPerShare /= Decimal("10")
            reinvestNav = cls._decimalValue(
                cls._firstValue(row, ("再投资净值", "红利再投资净值", "reinvest_nav"))
            )
            result.append(
                FundDividend(
                    ex_date=exDate,
                    pay_date=cls._dateValue(
                        cls._firstValue(row, ("分红发放日", "pay_date"))
                    ),
                    amount_per_share=amountPerShare,
                    reinvest_nav=reinvestNav,
                )
            )
        return sorted(result, key=lambda item: item.ex_date)

    @classmethod
    def _normalizeSplits(cls, value: Any) -> list[FundSplit]:
        """标准化分拆事件；ratio 表示每一份拆分后的份数。"""
        result: list[FundSplit] = []
        for row in cls._records(value):
            splitDate = cls._dateValue(
                cls._firstValue(row, ("拆分折算日", "拆分日期", "split_date"))
            )
            ratio = cls._decimalValue(
                cls._firstValue(row, ("拆分折算比例", "拆分比例", "ratio"))
            )
            if splitDate is None or ratio is None or ratio <= 0:
                continue
            result.append(FundSplit(effective_date=splitDate, ratio=ratio))
        return sorted(result, key=lambda item: item.effective_date)
