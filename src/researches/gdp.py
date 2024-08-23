import json
import os

import requests
import pandas as pd
import matplotlib.pyplot as plt

# GDP累计值
# GDP当季值
# GDP当季同比
# GDP当季环比

# 用累计值推算当季值会存在误差，因为累计值存在对新信息的调整。
# 比如前三季度的累计值可能会对前二季度数据里的遗漏、重复、误报做调整。

# 一般使用：当季GDP同比增速（不变价）

# 预计2024年中国GDP增长4.5%—5.0%


def read(dbcode, zb, sj, useLocal=True):
    filePath = f"./data/nbs_{dbcode}_{zb}_{sj}.json"
    if useLocal and os.path.exists(filePath):
        with open(filePath, "r") as f:
            data = json.load(f)
            f.close()
    else:
        res = requests.get(
            f"http://localhost:9988/api/nbs?dbcode={dbcode}&zb={zb}&sj={sj}"
        )
        with open(filePath, "w") as f:
            f.write(res.text)
            f.close()
        data = json.loads(res.text)
    return data


def plot(dbcode, zb, sj, col=None):
    data = read(dbcode, zb, sj)
    obj = {}
    for key in data:
        if col and col != key:
            continue
        else:
            indexes, arr = [], []
            for item in data[key]:
                arr.insert(0, item["value"])
                indexes.insert(0, item["date"])
            obj[key] = arr
    df = pd.DataFrame(obj, index=indexes)
    df.plot()
    plt.show()


if __name__ == "__main__":
    # data = read("hgjd", "A0102", "2000-")
    # print(data.keys())

    # plot("hgjd", "A0104", "2000-")

    # 各产业对GDP的拉动程度

    data0 = read("hgjd", "A0103", "2000-")  # 国内生产总值指数(上年同期=100)
    data = read("hgjd", "A0106", "2000-")   # 三次产业贡献率
    print(data.keys())

    growthRate = []
    index = []
    for item in data0['国内生产总值指数(上年同期=100)_当季值']:
        growthRate.insert(0, item['value'] - 100)
        index.insert(0, item['date'])
    
    keys = ['第一产业贡献率_当季值', '第二产业贡献率_当季值', '第三产业贡献率_当季值']
    dic = {}
    for key in keys:
        arr = []
        for item in data[key]:
            arr.insert(0, item['value'] / 100)
        dic[key] = arr
    contribution = pd.DataFrame(dic, index=index)
    print(contribution.head())