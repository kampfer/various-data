from typing import Union
import akshare as ak
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import sys
import json
from importlib import import_module
import traceback
# from ..crawlers.python.utils import fetchStatsData, extractStatsData

app = FastAPI()
DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data')
MODULE_PATH = os.path.join(os.path.dirname(__file__), '../../crawlers/python')

# 这样在运行时才能成功导入模块
sys.path.append(MODULE_PATH)

app.mount("/web", StaticFiles(directory="./dist/web"), name="web")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get('/akshare/{funcName}')
def callAkshare(funcName, p = None):
    func = getattr(ak, funcName)
    # print(funcName, json.loads(p))
    if (p):
        params = json.loads(p)
    else:
        params = {}
    df = func(**params)
    return df.to_json()

@app.get('/nbs')
def crawlerNBSData(dbcode, zb, sj):
    fetchStatsData = getattr(import_module('utils'), 'fetchStatsData')
    extractStatsData = getattr(import_module('utils'), 'extractStatsData')
    res = fetchStatsData(dbcode, zb, sj)
    data = extractStatsData(res)
    return {
        'code': 200,
        'data': data
    }

@app.get('/data/{name}')
def getMyData(name):
    targetPath = f'{os.path.join(DATA_PATH, name)}.json'
    if os.path.exists(targetPath):
        with open(targetPath, 'r') as f:
            data = json.load(f)
        return {
            'code': 200,
            'data': data
        }
    else:
        return { 'code': 404, 'msg': '数据不存在' }

@app.get('/api/getCrawlers')
def getCrawlers():
    crawlers = [
        { 
            'name': '国内生产总值',
            'moduleName': 'gdp',
            'crawlerName': 'crawlYearlyGDP',
            'fileName': 'yearly_gdp',
            'note': '年度数据；1952年至今',
            'source': 'https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A0201&sj=2021'
        },
        { 
            'name': '国内生产总值（现价）', 
            'moduleName': 'gdp', 
            'crawlerName': 'crawlQuarterlyGDP',
            'fileName': 'quarterly_gdp',
            'note': '季度数据；1992年第一季度至今',
            'source': 'https://data.stats.gov.cn/easyquery.htm?cn=B01&zb=A0101&sj=2022C',
        },
        {
            'name': '国内生产总值指数（上年=100）', 
            'moduleName': 'gdp', 
            'crawlerName': 'crawlYearlyGDPIndex',
            'fileName': 'yearly_gdp_index',
            'note': '年度数据；1953年至今',
            'source': 'https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A020201&sj=2021'
        },
        {
            'name': '各种价格定基指数',
            'moduleName': 'cpi',
            'crawlerName': 'crawlYearlyPriceFixingIndex',
            'fileName': 'yearly_price_fix_index',
            'source': 'https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A0902&sj=2020',
        },
        {
            'name': '全国居民消费价格分类指数(上年同期)(2016-)',
            'moduleName': 'cpi',
            'crawlerName': 'crawlMonthlyCPIYoY2016_',
            'fileName': 'monthly_cpi_yoy_2016_',
            'source': 'https://data.stats.gov.cn/easyquery.htm?cn=A01&zb=A010202&sj=202211',
        },
        {
            'name': '全国居民消费价格分类指数(上年同期)(-2015)',
            'moduleName': 'cpi',
            'crawlerName': 'crawlMonthlyCPIYoY_2015',
            'fileName': 'monthly_cpi_yoy_2015',
            'source': 'https://data.stats.gov.cn/easyquery.htm?cn=A01&zb=A010202&sj=202211',
        }
    ]
    for crawler in crawlers:
        fileName= crawler['fileName']
        crawler['url'] = f'/data/{fileName}'
        filePath = f'{os.path.join(DATA_PATH, fileName)}.json'
        if os.path.exists(filePath):
            crawler['updateTime'] = os.path.getmtime(filePath)
    return {
        'code': 200,
        'data': crawlers
    }

@app.get('/api/exeCrawler')
def exeCrawler(moduleName, funcName):
    func = getattr(import_module(moduleName), funcName)
    try:
        func()
        return { 'code': 200 }
    except Exception as e:
        traceback.print_exc()
        return { 'code': 500, 'msg': 'Unexpected Error: {}'.format(e) }
