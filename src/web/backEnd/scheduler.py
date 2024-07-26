from datetime import datetime
import glob
import importlib
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_SCHEDULER_STARTED

from backEnd.database import SQLALCHEMY_DATABASE_URL


def initScheduler():
    job_defaults = {"coalesce": False, "max_instances": 3}
    # 使用默认store：MemoryJobStore
    # 使用默认executor：ThreadPoolExecutor
    scheduler = BackgroundScheduler(job_defaults=job_defaults)

    def startHint(e):
        print("apscheduler启动成功")

    # https://apscheduler.readthedocs.io/en/stable/modules/events.html#event-codes
    scheduler.add_listener(startHint, EVENT_SCHEDULER_STARTED)

    # 启动任务：调用tasks目录下的所有模块的addJob方法
    # 定义要调用的函数名
    function_name = "addJob"
    # 获取当前目录下所有Python模块
    module_files = [
        f
        for f in os.listdir(os.path.join(os.path.dirname(__file__), "tasks"))
        if not f.startswith("__")
    ]
    modules = [importlib.import_module(f"backEnd.tasks.{f[:-3]}") for f in module_files]
    # 调用所有模块中的同名函数
    for module in modules:
        func = getattr(module, function_name, None)
        if func:
            func(scheduler)

    return scheduler


myScheduler = initScheduler()


def startScheduler():
    myScheduler.start()


def stopScheduler():
    myScheduler.shutdown(wait=False)
