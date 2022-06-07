from typing import Union
import akshare as ak
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

app = FastAPI()

app.mount("/static", StaticFiles(directory="src/web/static"), name="static")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get('/stock/{stockId}')
def getStockDetail(stockId: str):
    df = ak.stock_zh_index_daily(symbol=stockId)
    df.set_index('date', inplace=True)
    return df.to_json(orient='split')
