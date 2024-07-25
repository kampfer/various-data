from datetime import datetime
import glob
import importlib
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_SCHEDULER_STARTED

from backEnd.database import SQLALCHEMY_DATABASE_URL

jobstores = {"default": SQLAlchemyJobStore(url=SQLALCHEMY_DATABASE_URL)}
executors = {
    "default": ThreadPoolExecutor(20),
}
job_defaults = {"coalesce": False, "max_instances": 3}
scheduler = BackgroundScheduler(
    jobstores=jobstores, executors=executors, job_defaults=job_defaults
)


# https://apscheduler.readthedocs.io/en/stable/modules/triggers/interval.html
# https://apscheduler.readthedocs.io/en/stable/modules/triggers/cron.html
# scheduler.add_job(job1, "interval", seconds=2, id="test", replace_existing=True)


def startHint(e):
    print("hi")


# https://apscheduler.readthedocs.io/en/stable/modules/events.html#event-codes
scheduler.add_listener(startHint, EVENT_SCHEDULER_STARTED)


# 定义要调用的函数名
function_name = "addJob"
# 获取当前目录下所有Python模块
module_files = [
    f
    for f in os.listdir(os.path.join(os.path.dirname(__file__), 'jobs'))
    if not f.startswith("__")
]
modules = [importlib.import_module(f'backEnd.task.jobs.{f[:-3]}') for f in module_files]
# 调用所有模块中的同名函数
for module in modules:
    getattr(module, function_name, None)(scheduler)
