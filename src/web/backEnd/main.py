from typing import Union
import akshare as ak
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import sys
import json
from importlib import import_module
import traceback

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
def callAkshare(funcName, params):
    df = ak[funcName](**params)
    return df.to_json()

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
    return {
        'code': 200,
        'data': [
            { 
                'name': '国内生产总值',
                'moduleName': 'gdp',
                'crawlerName': 'crawlYearlyGDP',
                'source': 'https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A0201&sj=2021'
            },
            {
                'name': '国内生产总值指数（上年=100）', 
                'moduleName': 'gdp', 
                'crawlerName': 'crawlYearlyGDPIndex',
                'source': 'https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A020201&sj=2021'
            },
            { 
                'name': '国内生产总值（现价）', 
                'moduleName': 'gdp', 
                'crawlerName': 'crawlQuarterlyGDP',
                'source': 'https://data.stats.gov.cn/easyquery.htm?cn=B01&zb=A0101&sj=2022C'
            },
            {
                'name': '各种价格定基指数',
                'moduleName': 'cpi',
                'crawlerName': 'crawlYearlyPriceFixingIndex',
                'source': 'https://data.stats.gov.cn/easyquery.htm?cn=C01&zb=A0902&sj=2020',
                'url': '/data/yearly_price_fix_index'
            }
        ]
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
