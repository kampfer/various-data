import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import apiRouter
from app.investmentLedger.exceptions import registerLedgerExceptionHandlers
from app.models import initAppModels
from app.scheduler import startScheduler, stopScheduler


app = FastAPI()

app.mount(
    "/web",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../../../dist/web")),
    name="web",
)

initAppModels()
app.include_router(apiRouter)
registerLedgerExceptionHandlers(app)  # 注册投资交易账本的统一异常处理器


@app.on_event("startup")
def startUp():
    startScheduler()


@app.on_event("shutdown")
def shutDown():
    stopScheduler()


if __name__ == "__main__":
    import uvicorn

    # 常规启动方法
    uvicorn.run(app, host="127.0.0.1", port=8888)
