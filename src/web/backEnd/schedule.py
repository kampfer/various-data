from sinaNews import crawlSinaNews, closeSinaDB
from apscheduler.schedulers.blocking import BlockingScheduler
import signal


def crawlSinaJob():
    crawlSinaNews()


def closeDB():
    print("Closing database connection...")
    closeSinaDB()


def schedule_task():
    scheduler = BlockingScheduler()
    signal.signal(signal.SIGINT, signal_handler)
    try:
        # 详见：https://apscheduler.readthedocs.io/en/3.x/modules/schedulers/base.html#apscheduler.schedulers.base.BaseScheduler.add_job
        # misfire_grace_time
        # coalesce
        # replace_existing
        # max_instances
        scheduler.add_job(
            crawlSinaJob,
            "interval",
            hours=1,
            misfire_grace_time=60,
            replace_existing=True,
        )
        crawlSinaJob()  # 立即执行一次抓取
        scheduler.start()
        while True:
            pass
    except KeyboardInterrupt:
        print("捕获到键盘中断，正在执行清理操作...")
        closeDB()
        scheduler.shutdown()
    finally:
        print("程序结束")


def signal_handler(signal, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    schedule_task()
