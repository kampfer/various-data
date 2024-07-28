# 方便调试
if __name__ == "__main__":
    import os

    os.sys.path.append(os.path.realpath(os.path.join(__file__, "../../../")))

import requests
import time
import json
import logging
from backEnd.logger import logger
from datetime import datetime
from backEnd.sinaFinanceNews import models, schemas
from backEnd.sinaFinanceNews.crud import addManyNews
from backEnd.database import SessionLocal
from sqlalchemy import select, text, desc


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
    # 持久化任务需要id和replace_existing=True
    scheduler.add_job(job, "interval", seconds=1, id=__name__, replace_existing=True)


if __name__ == "__main__":
    job()
