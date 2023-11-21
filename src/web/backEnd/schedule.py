from sinaNews import crawlSinaNews
from apscheduler.schedulers.blocking import BlockingScheduler

def crawlSinaJob():
    crawlSinaNews()

scheduler = BlockingScheduler()
scheduler.add_job(crawlSinaJob, 'interval', hours=1, misfire_grace_time=60)
# scheduler.add_job(crawlSinaJob, 'interval', minutes=1)
crawlSinaJob()
scheduler.start()
