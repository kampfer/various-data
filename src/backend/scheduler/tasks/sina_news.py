"""新浪财经快讯抓取任务。

行为与原 ``app/tasks/crawlSinaNews.py`` 一致，并补齐：请求超时、HTTP 状态码与
业务状态码校验、重复执行不产生重复记录。
"""

from __future__ import annotations

import json
import logging
from contextlib import closing
from datetime import datetime

import requests

from scheduler.config import Config
from scheduler.lib import db

FEED_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"
TIMEOUT = (30, 30)  # (连接, 读取) 秒
# 翻页保护：正常每页 100 条，1000 页可覆盖约一个月的停机补跑。
MAX_PAGES = 1000

logger = logging.getLogger("scheduler")


class SinaFeedError(RuntimeError):
    """新浪快讯接口返回异常。"""


def _base_params() -> dict:
    return {
        "callback": "jQuery123",
        "page": 1,
        "page_size": 100,
        "zhibo_id": 152,
        "tag_id": 0,
        "dire": "f",
        "dpc": 1,
        "pageSize": 100,
        "id": None,
        "type": None,
        "_": int(datetime.now().timestamp() * 1000),
    }


def _fetch(params: dict) -> dict:
    payload = dict(params)
    try:
        response = requests.get(FEED_URL, params=payload, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise SinaFeedError(f"请求新浪快讯接口失败: {exc}") from exc

    if not response.ok:
        raise SinaFeedError(f"新浪快讯接口返回 HTTP {response.status_code}")

    text = response.text.strip()
    start = text.find("(")
    if start < 0:
        raise SinaFeedError("新浪快讯接口响应不是预期的 JSONP 格式")

    # 响应形如 try{jQuery123({...});}catch(e){};，用 raw_decode 只取第一个 JSON 值，
    # 忽略 JSONP 包装与尾部的 ";}" 等字符。
    try:
        data, _ = json.JSONDecoder().raw_decode(text[start + 1 :])
    except json.JSONDecodeError as exc:
        raise SinaFeedError(f"新浪快讯接口响应无法解析: {exc}") from exc

    code = data.get("result", {}).get("status", {}).get("code")
    if code != 0:
        raise SinaFeedError(f"新浪快讯接口业务状态码非 0: {code}")

    feed = data.get("result", {}).get("data", {}).get("feed")
    if not isinstance(feed, dict):
        raise SinaFeedError("新浪快讯接口响应缺少 feed 数据")
    return feed


def crawl_latest() -> list[dict]:
    return list(_fetch(_base_params())["list"])


def crawl_after(min_id: int) -> list[dict]:
    """抓取 sina_id 大于 min_id 的快讯，翻页直到覆盖 min_id。"""

    items: list[dict] = []
    feed = _fetch(_base_params())
    pages = 0
    previous_min_id = None
    while feed["min_id"] > min_id:
        if previous_min_id is not None and feed["min_id"] >= previous_min_id:
            raise SinaFeedError(
                f"新浪快讯翻页未推进，min_id 停留在 {feed['min_id']}"
            )
        previous_min_id = feed["min_id"]
        items.extend(feed["list"])
        pages += 1
        if pages > MAX_PAGES:
            raise SinaFeedError(f"新浪快讯翻页超过 {MAX_PAGES} 页仍未追平")
        params = dict(_base_params())
        params["id"] = feed["min_id"]
        params["type"] = 1
        feed = _fetch(params)

    for item in feed["list"]:
        if item["id"] > min_id:
            items.append(item)
    return items


def _create_time_millis(raw: str) -> int:
    parsed = datetime.strptime(raw, "%Y-%m-%d %H:%M:%S")
    return int(parsed.timestamp() * 1000)


def _insert_feeds(conn, feeds: list[dict]) -> int:
    sina_ids = [int(item["id"]) for item in feeds]
    existing = db.get_existing_sina_ids(conn, sina_ids)
    inserted = 0

    for item in feeds:
        sina_id = int(item["id"])
        if sina_id in existing:
            continue

        news_id = db.insert_news(
            conn,
            sina_id=sina_id,
            create_time=_create_time_millis(item["create_time"]),
            content=item["rich_text"],
            url=item["docurl"],
            significance=0,
        )

        for tag in item.get("tag") or []:
            tag_name = tag["name"]
            tag_id = db.get_tag_id_by_name(conn, tag_name)
            if tag_id is None:
                tag_id = db.insert_tag(
                    conn,
                    name=tag_name,
                    is_sina_tag=True,
                    sina_id=str(tag.get("id", "")),
                )
            db.link_news_tag(conn, news_id, tag_id)

        existing.add(sina_id)
        inserted += 1

    return inserted


def run(config: Config) -> None:
    with closing(db.connect_business_db(config.db_path)) as conn:
        db.ensure_schema(conn)
        min_id = db.get_latest_sina_id(conn)
        feeds = crawl_latest() if min_id is None else crawl_after(int(min_id))
        inserted = _insert_feeds(conn, feeds)
        conn.commit()

    logger.info(
        "新浪快讯抓取完成: 抓取 %d 条, 新增 %d 条", len(feeds), inserted
    )
