"""新浪财经快讯抓取：接口分页 → 解析 JSON → 入库。

由 Dagu 以独立进程执行：`python src/dagu/tasks/sina_news.py`。
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path

# 允许以脚本方式直接运行：把 src/dagu 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging

import requests

from lib import config, db

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("dagu.sina_news")

REQUEST_TIMEOUT = 30
FEED_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"


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
    response = requests.get(FEED_URL, params=payload, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    logger.info("请求 %s", response.url)
    # 响应被 JSONP 包裹，去掉固定长度的前后缀
    jsonStr = response.text[14 : len(response.text) - 14]
    data = json.loads(jsonStr)
    statusCode = data["result"]["status"]["code"]
    if statusCode != 0:
        raise RuntimeError(f"新浪接口返回非 0 状态码: {statusCode}")
    return data["result"]["data"]


# id：从大到小 => 从新到旧
# 爬取 id 大于 minId 的新闻
def crawlFeedAfterMinId(minId):
    items = []
    res = crawlFeed()
    while res["feed"]["min_id"] > minId:
        for item in res["feed"]["list"]:
            items.append(item)
        res = crawlFeed(1, res["feed"]["min_id"])
    for item in res["feed"]["list"]:
        if item["id"] > minId:
            items.append(item)
    return items


def crawLatest():
    res = crawlFeed()
    return [item for item in res["feed"]["list"]]


def job() -> None:
    logger.info(config.describe())
    connection = db.connect()
    try:
        db.ensureSchema(connection)
        minId = db.getLatestNewsSinaId(connection)
        feeds = crawlFeedAfterMinId(minId) if minId else crawLatest()

        for item in feeds:
            createTime = int(
                datetime.strptime(item["create_time"], "%Y-%m-%d %H:%M:%S").timestamp()
                * 1000
            )
            newsId = db.insertNews(
                connection,
                item["id"],
                createTime,
                item["rich_text"],
                item["docurl"],
            )
            for tag in item["tag"]:
                tagId = db.getOrCreateTag(connection, tag["name"], True, tag["id"])
                db.linkNewsTag(connection, newsId, tagId)

        connection.commit()
        logger.info("本次写入快讯 %s 条", len(feeds))
    finally:
        connection.close()


if __name__ == "__main__":
    job()
