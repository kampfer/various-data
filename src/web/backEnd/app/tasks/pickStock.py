# 股票数据怎么取？走网络慢，而且容易失败；存本地怎么存？新建一个数据库？
import os

import akshare as ak
import pandas as pd
from tqdm import tqdm

if __name__ == "__main__":
    # https://akshare.akfamily.xyz/data/stock/stock.html#id224
    # stockCodes = ak.stock_info_a_code_name()
    # stockCodes.to_json('./stock_code.json')

    # https://akshare.akfamily.xyz/data/index/index.html#id3
    # ak.stock_zh_index_daily(symbol=code)

    # stockMapPath = './stock_code.json'
    # if os.path.exists(stockMapPath):
    #     stockCodeDf = pd.read_json(stockMapPath, dtype=False)
    #     # print(stockCodeDf.head(10))
    #     for row in stockCodeDf.itertuples():
    #         if row.Index == 0:
    #             stockDf = ak.index_zh_a_hist(symbol=row.code)
    #             print(stockDf.tail())

    # https://akshare.akfamily.xyz/data/stock/stock.html#id225
    df = ak.stock_info_sh_name_code()
    for row in tqdm(df.itertuples()):
        stockDf = ak.stock_zh_index_daily(symbol=f"sh{row.证券代码}")
        price = stockDf["close"]
        price = price[-7:]
        # 单调递增
        if not price.empty and price.is_monotonic_increasing:
            print(row)

    # https://akshare.akfamily.xyz/data/stock/stock.html#id226
    # stock_info_sz_name_code

    # https://akshare.akfamily.xyz/data/stock/stock.html#id227
    # stock_info_bj_name_code
