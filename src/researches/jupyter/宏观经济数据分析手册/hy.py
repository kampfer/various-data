import pandas as pd
import json


# 行业分类
def getHYFL():
    f = open("/home/liao/various-data/data/国民经济行业分类_2017.json", "r")
    cotnent = f.read()
    hyflJson = json.loads(cotnent)
    # 二级分类
    hyfl = {
        "codeToName": {},
        "nameToCode": {},
    }

    def iterHyfl(hy):
        for child in hy["children"]:
            iterHyfl(child)
        hyfl["codeToName"][hy["code"]] = hy["name"]
        hyfl["nameToCode"][hy["name"]] = hy["code"]

    for item in hyflJson:
        iterHyfl(item)

    return hyfl


# 行业代码前两位为06-46的企业就属于工业企业
def getIndustryHYCode():
    hyfl = getHYFL()
    ret = []
    for code in hyfl["codeToName"]:
        try:
            if int(code[:2]) >= 6 and int(code[:2]) <= 46:
                ret.append((code, hyfl["codeToName"][code]))
        except BaseException:
            pass
    return ret


# 从2020年投入产出表中计算工业企业在组内的占比
def getIndustryRatio():
    # 投入产出表
    # https://data.stats.gov.cn/files/html/quickSearch/trcc/trcc01.html
    # 2020年投入产出表 https://data.stats.gov.cn/files/html/quickSearch/trcc/2012/2020.xlsx
    inputOutputDf = pd.read_excel("/home/liao/various-data/data/2020.xlsx", header=4)
    rows = inputOutputDf[6:103]
    total = 0
    names = []
    codes = []

    for idx, row in rows.iterrows():
        total += row[-2]
        names.append(row[1])
        codes.append(row[2])

    gyzjzRatioByIndustrySeries = pd.Series(
        [row[-2] / total for idx, row in rows.iterrows()], [names, codes]
    )

    def groupByCode(code):
        return code[1][0:2]

    # 工业增加值分行业占比
    return (
        gyzjzRatioByIndustrySeries.groupby(by=groupByCode)
        .sum()
        .sort_values(ascending=False)
    )


# 工业企业中的上中下游分类
def getUpperAndLowerCooperation():
    # 上游
    upperIndustries = [
        "黑色金属矿采选业",
        "有色金属矿采选业",
        "煤炭开采和洗选业",
        "石油和天然气开采业",
        "非金属矿采选业",
    ]
    # 中游原材料
    middleIndustries1 = [
        "黑色金属冶炼和压延加工业",
        "有色金属冶炼和压延加工业",
        "石油、煤炭及其他燃料加工业",
        "非金属矿物制品业",
        "金属制品业",
        "橡胶和塑料制品业",
        "化学原料和化学制品制造业",
        "化学纤维制造业",
    ]
    # 中游机械设备
    middleIndustries2 = [
        "计算机、通信和其他电子设备制造业",
        "造纸和纸制品业",
        "仪器仪表制造业",
        "电气机械和器材制造业",
        "专用设备制造业",
        "通用设备制造业",
    ]
    # 下游行业
    lowerIndustries = [
        "汽车制造业",
        "铁路、船舶、航空航天和其他运输设备制造业",
        "木材加工和木、竹、藤、棕、草制品业",
        "家具制造业",
        "农副食品加工业",
        "食品制造业",
        "烟草制品业",
        "酒、饮料和精制茶制造业",
        "印刷和记录媒介复制业",
        "医药制造业",
        "纺织业",
        "纺织服装、服饰业",
        "皮革、毛皮、羽毛及其制品和制鞋业",
        "文教、工美、体育和娱乐用品制造业",
    ]
    return upperIndustries, middleIndustries1, middleIndustries2, lowerIndustries


def getExportIndustries():
    # 高出口依赖行业
    exportIndustries = [
        "计算机、通信和其他电子设备制造业",
        "金属制品、机械和设备修理业",
        "其他制造业",
        "文教、工美、体育和娱乐用品制造业",
        "皮革、毛皮、羽毛及其制品和制鞋业",
        "家具制造业",
        "纺织服装、服饰业",
        "铁路、船舶、航空航天和其他运输设备制造业",
        "电气机械和器材制造业",
        "仪器仪表制造业",
        "橡胶和塑料制品业",
        "通用设备制造业",
        "纺织业",
        "专用设备制造业",
        "金属制品业",
    ]
    return exportIndustries
