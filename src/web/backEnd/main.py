import akshare as ak
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import sys
import json
from importlib import import_module
import traceback

app = FastAPI()

DATA_PATH = os.path.join(os.path.dirname(__file__), "../../../data")
MODULE_PATH = os.path.join(os.path.dirname(__file__), "../../crawlers/python")

# 这样在运行时才能成功导入模块
sys.path.append(MODULE_PATH)

saveData = getattr(import_module("utils"), "saveData")
readData = getattr(import_module("utils"), "readData")

app.mount("/web", StaticFiles(directory="./dist/web"), name="web")

from . import db

sina7x24DB = db.SinaNews7x24DB()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/akshare")
def callAkshare(funcName, args):
    print(funcName, args)
    func = getattr(ak, funcName)
    if args:
        params = json.loads(args)
    else:
        params = {}
    df = func(**params)
    return {"code": 200, "data": json.loads(df.to_json(orient="records"))}


@app.get("/nbs")
def crawlerNBSData(dbcode, zb, sj):
    fetchStatsData = getattr(import_module("utils"), "fetchStatsData")
    extractStatsData = getattr(import_module("utils"), "extractStatsData")
    res = fetchStatsData(dbcode, zb, sj)
    data = extractStatsData(res)
    return {"code": 200, "data": data}


@app.get("/data/{name}")
def getMyData(name):
    targetPath = f"{os.path.join(DATA_PATH, name)}.json"
    if os.path.exists(targetPath):
        with open(targetPath, "r") as f:
            data = json.load(f)
        return {"code": 200, "data": data}
    else:
        return {"code": 404, "msg": "数据不存在"}


@app.get("/api/getCrawlers")
def getCrawlers():
    crawlers = [
        {
            "name": "国内生产总值",
            "moduleName": "gdp",
            "crawlerName": "crawlYearlyGDP",
            "fileName": "yearly_gdp",
            "note": "年度数据；1952年至今",
            "source": "https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A0201&sj=2021",
        },
        {
            "name": "国内生产总值（现价）",
            "moduleName": "gdp",
            "crawlerName": "crawlQuarterlyGDP",
            "fileName": "quarterly_gdp",
            "note": "季度数据；1992年第一季度至今",
            "source": "https://data.stats.gov.cn/easyquery.htm?cn=B01&zb=A0101&sj=2022C",
        },
        {
            "name": "国内生产总值指数（上年=100）",
            "moduleName": "gdp",
            "crawlerName": "crawlYearlyGDPIndex",
            "fileName": "yearly_gdp_index",
            "note": "年度数据；1953年至今",
            "source": "https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A020201&sj=2021",
        },
        {
            "name": "各种价格定基指数",
            "moduleName": "cpi",
            "crawlerName": "crawlYearlyPriceFixingIndex",
            "fileName": "yearly_price_fix_index",
            "source": "https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A0902&sj=2020",
        },
        {
            "name": "全国居民消费价格分类指数(上年同月=100)(2016-)",
            "moduleName": "cpi",
            "crawlerName": "crawlMonthlyCPIYoY2016_",
            "fileName": "monthly_cpi_yoy_2016_",
            "note": "月度数据;2016年至今",
            "source": "https://data.stats.gov.cn/easyquery.htm?cn=A01&zb=A010101",
        },
        {
            "name": "全国居民消费价格分类指数(上年同月=100)(-2015)",
            "moduleName": "cpi",
            "crawlerName": "crawlMonthlyCPIYoY_2015",
            "fileName": "monthly_cpi_yoy_2015",
            "note": "月度数据;2015年前",
            "source": "https://data.stats.gov.cn/easyquery.htm?cn=A01&zb=A010102",
        },
    ]
    for crawler in crawlers:
        fileName = crawler["fileName"]
        crawler["url"] = f"/data/{fileName}"
        filePath = f"{os.path.join(DATA_PATH, fileName)}.json"
        if os.path.exists(filePath):
            crawler["updateTime"] = os.path.getmtime(filePath) * 1000
    return {"code": 200, "data": crawlers}


@app.get("/api/exeCrawler")
def exeCrawler(moduleName, funcName):
    func = getattr(import_module(moduleName), funcName)
    try:
        func()
        return {"code": 200}
    except Exception as e:
        traceback.print_exc()
        return {"code": 500, "msg": "Unexpected Error: {}".format(e)}


@app.get("/api/pinEvent")
async def pinEvent(id: int):
    sina7x24DB.updateNewsSignificance(id, 1)
    return {"code": 200}


@app.get("/api/unpinEvent")
async def unpinEvent(id: int):
    sina7x24DB.updateNewsSignificance(id, 0)
    return {"code": 200}


@app.get("/api/stock/daily")
def getStockHqDaily(code):
    jsonPath = f"{os.path.join(DATA_PATH, code)}.json"
    if os.path.exists(jsonPath):
        data = readData(jsonPath)
    else:
        data = ak.stock_zh_index_daily(symbol=code).to_json(orient="records")
        saveData(jsonPath, data)


@app.get("/api/sina7x24/news")
async def getSina7x24News(
    page=0,
    pageSize=20,
    filterWords: str = None,
    startTime: int = None,
    endTime: int = None,
    priority: int = None,
    sortBy: int = 0,
    category: int = None,
):
    listInDB = sina7x24DB.selectNews(
        page=page,
        pageSize=pageSize,
        keyword=(filterWords if filterWords else None),
        startTime=startTime,
        endTime=endTime,
        significance=(priority if priority else None),
        sort=sortBy,
        category=(category if category else None),
    )
    news = []
    for d in listInDB:
        tags = []
        if len(d[4]) > 0:
            for x in d[4].split(","):
                tags.append(int(x))
        news.append(
            {
                "id": d[0],
                "createTime": d[1],
                "content": d[2],
                "tags": tags,
                "significance": d[3],
            }
        )

    total = sina7x24DB.newsCount(
        keyword=(filterWords if filterWords else None),
        startTime=startTime,
        endTime=endTime,
        significance=(priority if priority else None),
        category=(category if category else None),
    )

    return {"code": 200, "data": {"list": news, "total": total}}


@app.get("/api/sina7x24/tags")
async def getSina7x24Tags():
    tagsInDB = sina7x24DB.selectNewsTags()
    tags = [
        {"id": tag[0], "name": tag[1], "isSinaTag": True if tag[3] == "1" else False}
        for tag in tagsInDB
    ]
    return {"code": 200, "data": tags}
