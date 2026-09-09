import os

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.api import apiRouter
from app.investmentLedger.exceptions import registerLedgerExceptionHandlers
from app.models import initAppModels
from app.scheduler import startScheduler, stopScheduler


app = FastAPI()

# 开发时允许跨域（前端 devServer 端口 3000 访问 8000 端口）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 前端 devServer 地址
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


# 只有生产环境才托管静态文件
if os.getenv("APP_ENV") == "production":
    dist_path = os.path.join(os.path.dirname(__file__), "../../../dist/web")
    app.mount("/web", StaticFiles(directory=dist_path, html=True), name="static")
    print("生产模式：后端托管前端静态文件")
else:
    print("开发模式：仅提供 API，前端由 Webpack Dev Server 提供")