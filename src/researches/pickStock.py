import akshare as ak
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import os
import pandas as pd
from io import StringIO

# 1.为何要复权：由于股票存在配股、分拆、合并和发放股息等事件，会导致股价出现较大的缺口。 若使用不复权的价格处理数据、计算各种指标，将会导致它们失去连续性，且使用不复权价格计算收益也会出现错误。 为了保证数据连贯性，常通过前复权和后复权对价格序列进行调整。

# 2.前复权：保持当前价格不变，将历史价格进行增减，从而使股价连续。 前复权用来看盘非常方便，能一眼看出股价的历史走势，叠加各种技术指标也比较顺畅，是各种行情软件默认的复权方式。 这种方法虽然很常见，但也有两个缺陷需要注意。

# 2.1 为了保证当前价格不变，每次股票除权除息，均需要重新调整历史价格，因此其历史价格是时变的。 这会导致在不同时点看到的历史前复权价可能出现差异。

# 2.2 对于有持续分红的公司来说，前复权价可能出现负值。

# 3.后复权：保证历史价格不变，在每次股票权益事件发生后，调整当前的股票价格。 后复权价格和真实股票价格可能差别较大，不适合用来看盘。 其优点在于，可以被看作投资者的长期财富增长曲线，反映投资者的真实收益率情况。

# 4.在量化投资研究中普遍采用后复权数据。


# 移动平均
def MAFilter(s, n):
    return s.rolling(window=n).mean()


def calculateSlope2(s):
    return s.rolling(3).apply(lambda s: s.iloc[2] - s.iloc[0])


def calculateSlope(s):
    windowSize = 3
    rollingTrend = s.rolling(windowSize)

    def cal(window):
        x = np.arange(windowSize)
        y = window.values
        slope, _ = np.polyfit(x, y, 1)
        return slope

    return rollingTrend.apply(cal)


def oneYearAgo(format="%Y%m%d"):
    now = datetime.now()
    one_year_ago = now - timedelta(days=365)
    return one_year_ago.strftime(format)


# stock_zh_a_hist_df = ak.stock_zh_a_hist(
#     symbol="000001",
#     period="daily",
#     start_date="20170301",
#     end_date="20240528",
#     adjust="hfq",
# )
# date = stock_zh_a_hist_df["日期"]
# price = stock_zh_a_hist_df["收盘"]
# ma30 = MAFilter(price, 30)
# ma30Slopes = calculateSlopes(ma30)

# ax1 = plt.gca()
# ax1.plot(date, price, label="pirce")
# ax1.plot(date, MAFilter(price, 30), label="MA30")

# ax2 = ax1.twinx()
# ax2.plot(date, ma30Slopes, 'r-', label="slope")

# plt.show()


# endTime = datetime.now().strftime("%Y%m%d")
# startTime = oneYearAgo()
# https://akshare.akfamily.xyz/data/stock/stock.html#id223
# dfStockCode = ak.stock_info_a_code_name()
# print(dfStockCode.count())
# dfStockCode.to_csv('./data/a.csv')
# for index, row in dfStockCode.iterrows():
#     stockDf = ak.stock_zh_a_hist(
#         symbol=row["code"],
#         period="daily",
#         start_date=startTime,
#         end_date=endTime,
#         adjust="hfq",
#     )
#     price = stockDf["收盘"]
#     ma30 = MAFilter(price, 30)
#     slopes = calculateSlopes(ma30)
#     lastTwoRows = slopes.iloc[-2:]
#     if lastTwoRows.iloc[0] <=0 and lastTwoRows.iloc[1] > 0:
#         print(f"{row['code']} {row['name']}")


def walkAMarket(func):
    aPath = "./data/A股"
    for item in os.listdir(aPath):
        filePath = os.path.join(aPath, item)
        if os.path.isfile(filePath):
            with open(filePath, "r", encoding="gbk") as f:
                text = f.read()
                text = text.split("\n")[1:-2]
                text = "\n".join(text)
                df = pd.read_csv(StringIO(text), sep="[\t\s]+", engine="python")
                func(df, filePath)


hit = []


def s1(df, filePath):
    price = df["收盘"]
    # 排除待上市的股票
    if price.count() > 60:
        ma30 = MAFilter(price, 30)
        slopes = calculateSlope(ma30)
        gap = slopes.max() - slopes.min()
        lastTwoRows = slopes.iloc[-2:]
        if lastTwoRows.iloc[1] - lastTwoRows.iloc[0] >= gap * 0.1:
            # print(filePath)
            hit.append(os.path.basename(filePath))


walkAMarket(s1)
print(hit)
print(len(hit))
