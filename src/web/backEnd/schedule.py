from sinaNews import crawlSinaNews
from apscheduler.schedulers.blocking import BlockingScheduler

def crawlSinaJob():
    crawlSinaNews()
    print(f'')

scheduler = BlockingScheduler()
scheduler.add_job(crawlSinaJob, 'interval', hours=1)
# scheduler.add_job(crawlSinaJob, 'interval', minutes=1)
scheduler.start()
