# 方便调试
if __name__ == "__main__":
    import os

    os.sys.path.append(os.path.realpath(os.path.join(__file__, "../../../")))

import time
import json
from datetime import datetime

import requests
from sqlalchemy import select, text, desc

from app.logger import logger
from app.sinaFinanceNews import models, schemas
from app.sinaFinanceNews.crud import addManyNews
from app.database import SessionLocal


def crawlFeed(type=None, id=None):
    payload = {
        "callback": "jQuery123",
        "page": 1,
        "page_size": 100,
        "zhibo_id": 152,
        "tag_id": 0,
        "dire": "f",
        "dpc": 1,
        "pageSize": 100,
        "id": id,
        "type": type,
        "_": int(time.time() * 1000),
    }
    r = requests.get("https://zhibo.sina.com.cn/api/zhibo/feed", params=payload)
    logger.info(f"请求{r.url}")
    jsonStr = r.text[14 : len(r.text) - 14]
    data = json.loads(jsonStr)
    if data["result"]["status"]["code"] == 0:
        return data["result"]["data"]
    else:
        return None


# id：从大到小=》从新到旧
# 爬取id大于minid的新闻
def crawlFeedAfterMinId(minId):
    list = []
    res = crawlFeed()
    while res["feed"]["min_id"] > minId:
        for item in res["feed"]["list"]:
            list.append(item)
        res = crawlFeed(1, res["feed"]["min_id"])
    for item in res["feed"]["list"]:
        if item["id"] > minId:
            list.append(item)
    return list


def crawLatest():
    res = crawlFeed()
    return [item for item in res["feed"]["list"]]


def job():
    with SessionLocal() as session:
        stmt = (
            select(models.SFNews.sina_id)
            .order_by(desc(models.SFNews.create_time))
            .limit(1)
        )
        result = session.execute(stmt)
        minId = result.scalar()

        if minId:
            feeds = crawlFeedAfterMinId(minId)
        else:
            feeds = crawLatest()

        sNewsNeedAdded = []
        for item in feeds:
            sNews = schemas.SFNews(
                sina_id=item["id"],
                create_time=int(
                    datetime.strptime(
                        item["create_time"], "%Y-%m-%d %H:%M:%S"
                    ).timestamp()
                    * 1000
                ),
                content=item["rich_text"],
                url=item["docurl"],
                tags=[],
            )
            for d in item["tag"]:
                sNews.tags.append(
                    schemas.SFTag(name=d["name"], is_sina_tag=True, sina_id=d["id"])
                )
            sNewsNeedAdded.append(sNews)
        addManyNews(session, sNewsNeedAdded)


def addJob(scheduler):
    # 任务类型有：
    # https://apscheduler.readthedocs.io/en/stable/modules/triggers/interval.html
    # https://apscheduler.readthedocs.io/en/stable/modules/triggers/cron.html
    #
    # 持久化任务需要`id`和`replace_existing=True`
    # `coalesce=True` 如果前一个任务实例还在执行中，则下一个任务实例会被放弃执行，直到前一个实例完成。
    # `__name__` 在模块被导入时会被设置为该模块的名字。如果模块是被直接执行，__name__会被设置为字符串'__main__'
    scheduler.add_job(job, "interval", hours=1, id=__name__, coalesce=True)
    logger.info(f'添加任务{__name__}')


if __name__ == "__main__":
    job()
