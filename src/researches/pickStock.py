import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, AutoMinorLocator
import numpy as np
from datetime import datetime, timedelta
import os
import pandas as pd
from io import StringIO
from tqdm import tqdm


# 1.为何要复权：由于股票存在配股、分拆、合并和发放股息等事件，会导致股价出现较大的缺口。 若使用不复权的价格处理数据、计算各种指标，将会导致它们失去连续性，且使用不复权价格计算收益也会出现错误。 为了保证数据连贯性，常通过前复权和后复权对价格序列进行调整。

# 2.前复权：保持当前价格不变，将历史价格进行增减，从而使股价连续。 前复权用来看盘非常方便，能一眼看出股价的历史走势，叠加各种技术指标也比较顺畅，是各种行情软件默认的复权方式。 这种方法虽然很常见，但也有两个缺陷需要注意。

# 2.1 为了保证当前价格不变，每次股票除权除息，均需要重新调整历史价格，因此其历史价格是时变的。 这会导致在不同时点看到的历史前复权价可能出现差异。

# 2.2 对于有持续分红的公司来说，前复权价可能出现负值。

# 3.后复权：保证历史价格不变，在每次股票权益事件发生后，调整当前的股票价格。 后复权价格和真实股票价格可能差别较大，不适合用来看盘。 其优点在于，可以被看作投资者的长期财富增长曲线，反映投资者的真实收益率情况。

# 4.在量化投资研究中普遍采用后复权数据。


# 移动平均
def MAFilter(s, n):
    return s.rolling(window=n).mean()


# (y2 - y1) / 1
def calculateSlope2(s):
    return s.rolling(3).apply(lambda s: s.iloc[2] - s.iloc[0])


# polyfit拟合一次多项式
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


def walkAMarket(func):
    aPath = "./data/A股"
    for item in tqdm(os.listdir(aPath)):
        filePath = os.path.join(aPath, item)
        if os.path.isfile(filePath):
            with open(filePath, "r", encoding="gbk") as f:
                text = f.read()
                text = text.split("\n")[1:-2]
                text = "\n".join(text)
                df = pd.read_csv(StringIO(text), sep="[\t\s]+", engine="python")
                func(df, filePath)


def analyseAllStocks(func):
    result = []

    def callback(df, filePath):
        if func(df, filePath):
            result.append(os.path.basename(filePath))

    walkAMarket(callback)
    return result


def analyseSingleStock(code, func):
    filePath = f"./data/A股/{code}.txt"
    with open(filePath, "r", encoding="gbk") as f:
        text = f.read()
        text = text.split("\n")[1:-2]
        text = "\n".join(text)
        df = pd.read_csv(StringIO(text), sep="[\t\s]+", engine="python")
        func(df)


def isFlat(s):
    return s.std() < s.mean() * 0.0025


if __name__ == "__main__":
    print(pd.__version__)

    # 先平后涨
    # 先跌后涨

    def s(df, filePath):
        price = df["收盘"]
        # 只处理上市超过60天的股票，排除待上市或刚上市的股票
        if price.count() > 60:
            ma30 = MAFilter(price, 30)
            if (ma30.iloc[-1] - ma30.iloc[-2]) / ma30.iloc[-2] > 0.02:
                return True
        return False

    def s2(df):
        dates = df["日期"]
        prices = df["收盘"]
        pole = prices.iloc[1]
        poles = [pole]
        indexes = [dates.iloc[1]]
        for i, v in prices.items():
            if abs((v - pole) / pole) > 0.2:
                poles.append(v)
                indexes.append(dates.iloc[i])
                pole = v

        plt.plot(df["日期"], df["收盘"])
        plt.plot(indexes, poles)

        y_major_locator = MultipleLocator(80)
        x_minor_locator = AutoMinorLocator()

        # 调整刻度的数量可以通过设置刻度的间隔大小来实现
        ax = plt.gca()
        ax.xaxis.set_major_locator(y_major_locator)
        ax.xaxis.set_minor_locator(x_minor_locator)

        plt.show()

    def s3(df, filePath=None):
        price = df["收盘"]
        price = price[-7:]
        # 单调递增
        return not price.empty and price.is_monotonic_increasing

    stocks = analyseAllStocks(s3)
    print(stocks)
    # analyseSingleStock("SH#600185", s3)
