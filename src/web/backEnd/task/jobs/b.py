def job():
  print('job1')

def addJob(scheduler):
  scheduler.add_job(job, "interval", seconds=20, id="test3", replace_existing=True)