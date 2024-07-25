def job():
  print('job1')

def addJob(scheduler):
  scheduler.add_job(job, "interval", seconds=2, id="test2", replace_existing=True)
