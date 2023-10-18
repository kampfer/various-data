import requests
import time
import json

from db import SinaNews7x24DB
from datetime import datetime

dbInstance = SinaNews7x24DB()


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


def crawlSinaNews():
    last = dbInstance.latestNews()
    minId = last[1]
    feeds = crawlFeedAfterMinId(minId)

    news = []
    relationMap = {}
    for item in feeds:
        sina_id = item["id"]
        create_time = int(
            datetime.strptime(item["create_time"], "%Y-%m-%d %H:%M:%S").timestamp()
            * 1000
        )
        content = item["rich_text"]
        url = item["docurl"]
        significance = 0
        news.append((sina_id, create_time, content, url, significance))
        for d in item["tag"]:
            tagId = dbInstance.insertTag(d["name"], d["id"], True)
            if sina_id in relationMap:
                relationMap[sina_id].append(tagId)
            else:
                relationMap[sina_id] = [tagId]
    dbInstance.insertManyNews(list(reversed(news)))

    seq = ','.join(['?'] * len(news))
    sql = f'SELECT id, sina_id FROM sina_news_7x24 WHERE sina_id IN ({seq})'
    cursor = dbInstance.conn.execute(
        sql,
        [d[0] for d in news],
    )
    rNews = cursor.fetchall()
    idMap = {}
    relationList = []
    for r in rNews:
        idMap[r[1]] = r[0]
    for sina_id in relationMap:
        for tagId in relationMap[sina_id]:
            relationList.append((idMap[sina_id], tagId))
    dbInstance.insertManyRelations(relationList)

    time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f'{time}本次新增{len(feeds)}条新闻')


if __name__ == "__main__":
    crawlSinaNews()

# crawlSinaNews()
# dbInstance.recoverFromJson("data/sina7x24.json", "data/pinedEvents.json")
