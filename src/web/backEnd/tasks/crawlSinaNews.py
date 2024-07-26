# 方便调试
if __name__ == "__main__":
    import os

    os.sys.path.append(os.path.realpath(os.path.join(__file__, "../../../")))

import requests
import time
import json
import logging
from datetime import datetime
from backEnd.sinaFinanceNews.models import SFNews, SFTag
from backEnd.sinaFinanceNews.crud import addNews
from backEnd.dependencies import get_db
from sqlalchemy import select, text, desc

logger = logging.getLogger(__name__)


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
    print(f"请求{r.url}")
    jsonStr = r.text[14 : len(r.text) - 14]
    data = json.loads(jsonStr)
    if data["result"]["status"]["code"] == 0:
        return data["result"]["data"]
    else:
        return None


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


def job():
    g = get_db()
    db = next(g)
    stmt = select(SFNews).order_by(desc(SFNews.create_time)).limit(1)
    result = db.execute(stmt)
    minId = result.first()[0].sina_id
    feeds = crawlFeedAfterMinId(minId)
    for item in feeds:
        news = {
            "sina_id": item["id"],
            "create_time": int(
                datetime.strptime(item["create_time"], "%Y-%m-%d %H:%M:%S").timestamp()
                * 1000
            ),
            "content": item["rich_text"],
            "url": item["docurl"],
            "tags": [],
        }
        for d in item["tag"]:
            news["tags"].append({"name": d["name"], "is_sina_tag": True, "sina_id": d["id"]})
        addNews(db, news)
    next(g)


def addJob(scheduler):
    # 持久化任务需要id和replace_existing=True
    scheduler.add_job(job, "interval", seconds=1, id=__name__, replace_existing=True)


if __name__ == "__main__":
    job()
