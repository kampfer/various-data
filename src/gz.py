# import requests
# import pandas as pd
# import numpy as np
# import os

# # 创业板收益率
# r = requests.get('http://127.0.0.1:3000/api/getIndicator?id=3b065983-7795-40dc-b104-48c072803d33')
# data = r.json()
# df = pd.DataFrame(data['data'])
# df[['date']] = df[['date']].apply(pd.to_datetime, unit='ms')
# df[['open', 'close', 'top', 'bottom']] = df[['open', 'close', 'top', 'bottom']].apply(pd.to_numeric)
# df.set_index('date', inplace=True)
# yearly = df.resample('BA').ffill()  # resample之前必须保证索引是datetime类型
# shiftedClosePrices = yearly.close.shift(1)
# shiftedClosePrices.iloc[0] = df.iloc[0].open
# returns = (yearly.close - shiftedClosePrices) / shiftedClosePrices
# returns.index = returns.index.year  # 索引需要对齐

# # 年化cpi
# cpiRes = requests.get('http://127.0.0.1:3000/api/getIndicator?id=875ee100-a14e-41aa-8c22-ea3fdc106792')
# cpiData = cpiRes.json()
# cpiDf = pd.DataFrame(cpiData['data'])
# cpiDf[['date']] = cpiDf[['date']].apply(pd.to_datetime, unit='ms')
# cpiDf.set_index('date', inplace=True)
# cpis = (cpiDf.cpi - 100) / 100
# cpis.sort_index(inplace=True, ascending=True)
# cpis.index = cpis.index.year    # 索引需要对齐

# # 隔夜国债收益率
# xlsxFilenames = [
#     'data/国债及其他债券收益率曲线/2011年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2012年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2013年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2014年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2015年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2016年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2017年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2018年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2019年中债国债收益率曲线标准期限信息.xlsx',
#     'data/国债及其他债券收益率曲线/2020年中债国债收益率曲线标准期限信息.xlsx',
# ];
# overnightAvgReturns = []
# overnightReturnIndices = []
# rootPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../')
# for xlsxFilename in xlsxFilenames:
#     df = pd.read_excel(os.path.join(rootPath, xlsxFilename), index_col=0, parse_dates=True)
#     overnightReturns = df[df['标准期限说明'] == '0d']['收益率(%)'] / 100
#     overnightAvgReturn = overnightReturns.mean()
#     overnightAvgReturns.append(overnightAvgReturn)
#     overnightReturnIndices.append(overnightReturns.index[0].year)   # 索引需要对齐
# overnightReturnSerie = pd.Series(overnightAvgReturns, overnightReturnIndices, name='nationDebt')

# # print(returns)
# # print(cpis)
# # print(overnightReturnSerie)

# # 计算前保证series是对齐的（index要相同）
# excessReturns = returns[1:returns.size - 1] - cpis[1:] - overnightReturnSerie
# print(excessReturns.describe())

import akshare as ak

sz399006Df = ak.stock_zh_index_daily(symbol="sz399006")
bondChinaYieldDf = ak.bond_china_yield(start_date="20210201", end_date="20220201")

print(sz399006Df.describe())