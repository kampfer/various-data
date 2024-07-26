from backEnd.database import SessionLocal

# 每天爬一次公开市场操作
def job():
  db = SessionLocal()

def addJob(scheduler):
  # 任务类型有：
  # https://apscheduler.readthedocs.io/en/stable/modules/triggers/interval.html
  # https://apscheduler.readthedocs.io/en/stable/modules/triggers/cron.html
  scheduler.add_job(job, "interval", seconds=10, id=__name__, replace_existing=True)