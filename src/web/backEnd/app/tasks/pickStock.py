# 股票数据怎么取？走网络慢，而且容易失败；存本地怎么存？新建一个数据库？
import os

import akshare as ak
import pandas as pd
from tqdm import tqdm


def traverse(s, func):
    for code in tqdm(s):
        stockDf = ak.stock_zh_index_daily(symbol=code)
        func(stockDf, code)


if __name__ == "__main__":
    # https://akshare.akfamily.xyz/data/stock/stock.html#id224
    # stockCodes = ak.stock_info_a_code_name()
    # stockCodes.to_json('./stock_code.json')

    # https://akshare.akfamily.xyz/data/index/index.html#id3
    # ak.stock_zh_index_daily(symbol=code)

    # https://akshare.akfamily.xyz/data/stock/stock.html#id225
    shDf = ak.stock_info_sh_name_code()
    # https://akshare.akfamily.xyz/data/stock/stock.html#id226
    szDf = ak.stock_info_sz_name_code()
    # https://akshare.akfamily.xyz/data/stock/stock.html#id227
    bjDf = ak.stock_info_bj_name_code()

    stocks = []

    def strategy1(df, stock):
        price = df["close"]
        price = price[-7:]
        # 单调递增
        if not price.empty and price.is_monotonic_increasing:
            stocks.append(stock)

    # traverse(shDf['证券代码'].apply(lambda code: f"sh{code}"), strategy1)
    # traverse(szDf["A股代码"].apply(lambda code: f"sz{code}"), strategy1)
    traverse(bjDf["证券代码"].apply(lambda code: f"bj{code}"), strategy1)

    print(stocks)
    # print(bjDf.head())
