"""基金最新净值服务。

本模块只保留持仓查询所需的基金日净值能力，历史净值代理接口已移除。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.investmentLedger.cache_proxy import CacheManager, CacheProxy

if TYPE_CHECKING:
    import pandas as pd


class AkshareFundQuoteClient:
    """从 akshare 获取基金最新净值并归一化字段名称。"""

    def fetchFundInfo(self):
        """获取基金日净值数据，转换为持仓查询使用的英文键名。"""
        import akshare as ak
        import pandas as pd

        df = ak.fund_open_fund_daily_em()

        if not isinstance(df, pd.DataFrame) or df.empty:
            return []

        def renameFundColumns(df: pd.DataFrame) -> pd.DataFrame:
            """统一基金静态字段及动态日期净值字段的名称。"""
            import re

            staticMap = {
                "基金代码": "fund_code",
                "基金简称": "fund_name",
                "日增长值": "daily_change",
                "日增长率": "daily_change_rate",
                "申购状态": "purchase_status",
                "赎回状态": "redemption_status",
                "手续费": "fee_rate",
            }
            pattern = re.compile(r"^(\d{4}-\d{2}-\d{2})-(单位净值|累计净值)$")
            navList = []
            accNavList = []
            allDates = []

            for column in df.columns:
                match = pattern.match(column)
                if match:
                    dateText, navType = match.groups()
                    dateValue = pd.to_datetime(dateText)
                    allDates.append(dateValue)
                    if navType == "单位净值":
                        navList.append((dateValue, column))
                    else:
                        accNavList.append((dateValue, column))

            navList.sort(key=lambda item: item[0], reverse=True)
            accNavList.sort(key=lambda item: item[0], reverse=True)

            dynamicMap = {}
            if len(navList) >= 1:
                dynamicMap[navList[0][1]] = "nav"
            if len(navList) >= 2:
                dynamicMap[navList[1][1]] = "pre_nav"
            if len(accNavList) >= 1:
                dynamicMap[accNavList[0][1]] = "acc_nav"
            if len(accNavList) >= 2:
                dynamicMap[accNavList[1][1]] = "pre_acc_nav"

            allMap = {**staticMap, **dynamicMap}
            existingMap = {
                key: value for key, value in allMap.items() if key in df.columns
            }
            renamedDf = df.rename(columns=existingMap)
            latestDate = max(allDates).strftime("%Y-%m-%d") if allDates else None
            renamedDf["update_date"] = latestDate
            return renamedDf

        return renameFundColumns(df).to_dict(orient="records")


class FundQuoteService:
    """为持仓查询提供基金最新净值。"""

    def __init__(self, client: AkshareFundQuoteClient | None = None) -> None:
        """装配可替换的 akshare 客户端并缓存日净值结果。"""
        self._client = CacheProxy(
            client or AkshareFundQuoteClient(),
            CacheManager(),
            {"fetchFundInfo": 24 * 60 * 60},
        )

    def getLatestNav(self, fundCodes):
        """返回指定基金的最新单位净值和净值日期。"""
        rows = self._client.fetchFundInfo()
        return [
            {
                "fund_code": row.get("fund_code"),
                "unit_nav": row.get("nav"),
                "accumulated_nav": row.get("acc_nav"),
                "update_date": row.get("update_date"),
            }
            for row in rows
            if row.get("fund_code") in fundCodes
        ]
