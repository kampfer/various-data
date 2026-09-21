import importlib
import os

from apscheduler.schedulers.base import BaseScheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import EVENT_SCHEDULER_STARTED


def _registerJobs(scheduler: BaseScheduler) -> None:
    """扫描 tasks 目录下的所有模块并调用其 addJob 方法注册定时任务。"""
    # 定义要调用的函数名
    function_name = "addJob"
    # 获取 tasks 目录下所有 Python 模块（排除 __ 开头的文件）
    module_files = [
        f
        for f in os.listdir(os.path.join(os.path.dirname(__file__), "tasks"))
        if not f.startswith("__")
    ]
    modules = [importlib.import_module(f"app.tasks.{f[:-3]}") for f in module_files]
    # 调用所有模块中的同名函数
    for module in modules:
        func = getattr(module, function_name, None)
        if func:
            func(scheduler)


def initScheduler(blocking: bool = False) -> BaseScheduler:
    """初始化调度器并注册所有定时任务。

    :param blocking: 为 True 时使用 BlockingScheduler（用于独立服务，阻塞主线程运行）；
                     为 False 时使用 BackgroundScheduler（用于随 Web 服务在后台运行）。
    """
    job_defaults = {"coalesce": False, "max_instances": 3}
    # 使用默认store：MemoryJobStore
    # 使用默认executor：ThreadPoolExecutor
    scheduler = BlockingScheduler(job_defaults=job_defaults) if blocking else BackgroundScheduler(job_defaults=job_defaults)

    def startHint(e):
        print("apscheduler启动成功")

    # https://apscheduler.readthedocs.io/en/stable/modules/events.html#event-codes
    scheduler.add_listener(startHint, EVENT_SCHEDULER_STARTED)

    # 注册 tasks 目录下的所有定时任务
    _registerJobs(scheduler)

    return scheduler
