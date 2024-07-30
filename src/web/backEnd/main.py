# import akshare as ak
import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.sinaFinanceNews.router import router as router1
from app.sinaFinanceNews.models import Base as SinaNewsBase
from app.omo.models import Base as OMOBase
from app.database import engine
from app.scheduler import startScheduler, stopScheduler

SinaNewsBase.metadata.create_all(bind=engine)
OMOBase.metadata.create_all(bind=engine)

app = FastAPI()

app.mount(
    "/web",
    StaticFiles(directory=os.path.join(os.path.dirname(__file__), "../../../dist/web")),
    name="web",
)

app.include_router(router1)


@app.on_event("startup")
def startUp():
    startScheduler()


@app.on_event("shutdown")
def shutDown():
    stopScheduler()


if __name__ == "__main__":
    import uvicorn

    mode = os.getenv("mode")

    # reload=True 在代码发生变化后自动重启服务
    # 此时第一个参数必须是字符串形式
    # uvicorn.run("main:app", host="127.0.0.1", port=9988, reload=mode != "pro")

    # 常规启动方法
    uvicorn.run(app, host="127.0.0.1", port=9988)
