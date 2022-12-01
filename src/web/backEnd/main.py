from typing import Union
import akshare as ak
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import json

app = FastAPI()
DATA_PATH = os.path.join(os.path.dirname(__file__), '../../data')

app.mount("/web", StaticFiles(directory="./dist/web"), name="web")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get('/akshare/{funcName}')
def callAkshare(funcName, params):
    df = ak[funcName](**params)
    return df.to_json()

@app.get('/mine/{name}')
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
            { 'name': 'yearlyGDP', 'apiName': 'crawlYearlyGDP' },
            { 'name': 'crawlYearlyGDPIndex', 'apiName': 'crawlYearlyGDPIndex' },
            { 'name': 'crawlQuarterlyGDP', 'apiName': 'crawlQuarterlyGDP' }
        ]
    }
