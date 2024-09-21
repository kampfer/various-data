import shutil
import os
from datetime import date


# 方便调试
if __name__ == "__main__":
    os.sys.path.append(os.path.realpath(os.path.join(__file__, "../../../")))

from app.logger import logger
from app.database import DB_FILE_PATH


# 每月备份一次数据库
def job():
    backupDir = os.path.normpath(
        os.path.join(os.path.dirname(__file__), f"../../../../../backup")
    )
    # 递归的创建目录，如果子目录已经存在不报错（`exist_ok=True`）
    os.makedirs(backupDir, exist_ok=True)
    dbName, ext = os.path.splitext(os.path.basename(DB_FILE_PATH))
    today = date.today().strftime("%Y%m%d")
    backupPath = f"{backupDir}/{dbName}_{today}.db"
    shutil.copy2(DB_FILE_PATH, backupPath)


def addJob(scheduler):
    scheduler.add_job(job, "cron", day=1, id=__name__, coalesce=True)
    logger.info(f"添加任务{__name__}")


if __name__ == "__main__":
    job()
