"""央行公开市场业务公告抓取与解析。

解析规则源自冻结实现 ``app/tasks/crawlOMO.py``，并按 spec 修正：
- 请求带超时与状态码校验；
- 交易类型按关键字归类，兼容期限前缀、隔夜品种与标题正文合并；
- 中文落款日期正确解析（"十月"不再被解析为 1 月）；
- 有新公告但解析为空时判失败。
"""

from __future__ import annotations

import logging
import re
from contextlib import closing
from datetime import datetime

import requests
from pyquery import PyQuery as pq

from scheduler.config import Config
from scheduler.lib import db

INDEX_URL = (
    "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html"
)
BASE_URL = "http://www.pbc.gov.cn"
TIMEOUT = (30, 30)
MAX_PAGES = 50

logger = logging.getLogger("scheduler")

_DIGITS = {
    "О": 0,
    "O": 0,
    "Ο": 0,
    "○": 0,
    "〇": 0,
    "零": 0,
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
}


def parse_chinese_number(text: str) -> int:
    """解析中文或阿拉伯数字，支持到两位数与年份写法。"""

    text = text.strip()
    if not text:
        raise ValueError("日期片段为空")
    if text.isdigit():
        return int(text)

    if "十" not in text:
        value = 0
        for char in text:
            if char not in _DIGITS:
                raise ValueError(f"日期中存在无法识别的字符: {char}")
            value = value * 10 + _DIGITS[char]
        return value

    tens_text, _, ones_text = text.partition("十")

    tens = 0
    for char in tens_text:
        if char not in _DIGITS:
            raise ValueError(f"日期中存在无法识别的字符: {char}")
        tens = tens * 10 + _DIGITS[char]
    if not tens_text:
        tens = 1

    ones = 0
    for char in ones_text:
        if char not in _DIGITS:
            raise ValueError(f"日期中存在无法识别的字符: {char}")
        ones = ones * 10 + _DIGITS[char]

    return tens * 10 + ones


def extract_time(doc) -> str:
    zoom = doc.find("#zoom")
    lines = zoom.text().split()
    if not lines:
        raise ValueError("公告正文为空，无法提取落款日期")

    raw = lines[-1]
    parts = re.split("[年月日]", raw)[:3]
    if len(parts) < 3:
        raise ValueError(f"无法识别的落款日期: {raw}")

    try:
        year, month, day = (parse_chinese_number(part) for part in parts)
        return datetime(year, month, day).strftime("%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"无法解析的落款日期: {raw} ({exc})") from exc


def find_prev_text(node) -> str | None:
    """向上、向前查找表格之前最近的一段非空文本，作为表格标题。"""

    prev_nodes = node.prevAll()
    for sibling in reversed(list(prev_nodes.items())):
        text = sibling.text()
        if text:
            return text
    if node.parent():
        return find_prev_text(node.parent())
    return None


def _extract_cb(table) -> list[dict]:
    """央行票据。"""

    deals = []
    for index, row in enumerate(table.find("tr").items()):
        if index == 0:
            continue
        cells = row.find("td")
        deal = {"type": "央行票据"}
        if len(cells) == 5:
            for i, key in enumerate(["name", "amount", "period", "price", "rate"]):
                deal[key] = cells.eq(i).text()
        elif len(cells) == 4:
            for i, key in enumerate(["name", "amount", "period", "rate"]):
                deal[key] = cells.eq(i).text()
            deal["price"] = None
        else:
            deal = None
        if deal:
            deals.append(deal)
    return deals


def _extract_rrp(table) -> list[dict]:
    """逆回购，表头存在多种历史格式。"""

    schema = ["period", "amount", "rate"]
    deals = []

    for index, row in enumerate(table.find("tr").items()):
        if index == 0:
            header = row.text()
            if header == "招标数量\n期限品种\n中标加权平均利率（%）":
                schema = ["amount", "period", "rate"]
            elif header == "期限\n操作利率\n投标量\n中标量":
                schema = ["period", "rate", "bidAmount", "amount"]
            continue

        cells = row.find("td")
        deal = {"type": "逆回购"}
        if len(cells) == len(schema):
            for i, key in enumerate(schema):
                deal[key] = cells.eq(i).text()
        else:
            deal = None
        if deal:
            deals.append(deal)
    return deals


def _extract_three_column(table, deal_type: str) -> list[dict]:
    deals = []
    for index, row in enumerate(table.find("tr").items()):
        if index == 0:
            continue
        cells = row.find("td")
        deal = {"type": deal_type}
        if len(cells) == 3:
            for i, key in enumerate(["period", "amount", "rate"]):
                deal[key] = cells.eq(i).text()
        else:
            deal = None
        if deal:
            deals.append(deal)
    return deals


def _extract_nb(table) -> list[dict]:
    """国债（现券买断）。"""

    deals = []
    for index, row in enumerate(table.find("tr").items()):
        if index == 0:
            continue
        cells = row.find("td")
        deal = {"type": "国债"}
        if len(cells) == 3:
            for i, key in enumerate(["period", "price", "amount"]):
                deal[key] = cells.eq(i).text()
        elif len(cells) == 4:
            for i, key in enumerate(["name", "period", "price", "amount"]):
                deal[key] = cells.eq(i).text()
        else:
            deal = None
        if deal:
            deals.append(deal)
    return deals


def _classify(name: str) -> str | None:
    """按关键字归类，TMLF 必须先于 MLF 判断。"""

    if "央行票据" in name:
        return "央行票据"
    if "TMLF" in name:
        return "TMLF"
    if "MLF" in name:
        return "MLF"
    if "逆回购" in name:
        return "逆回购"
    if "正回购" in name:
        return "正回购"
    if "现券买断" in name:
        return "现券买断"
    return None


def _extract_table(table, title: str) -> list[dict]:
    if not title:
        return []

    if re.search(r"如下[：:]", title):
        if re.search(r"发行(.*)央行票据", title):
            return _extract_cb(table)
        if re.search(r"开展(.*)正回购", title):
            return _extract_three_column(table, "正回购")
        return []

    matched = re.search(r"(.+)(?:发行|交易|操作|招标|到期续做|买断招标)情况$", title)
    if not matched:
        return []

    name = matched.group(1)
    deal_type = _classify(name)
    if deal_type == "央行票据":
        return _extract_cb(table)
    if deal_type == "逆回购":
        return _extract_rrp(table)
    if deal_type == "正回购":
        return _extract_three_column(table, "正回购")
    if deal_type == "MLF":
        return _extract_three_column(table, "MLF")
    if deal_type == "TMLF":
        return _extract_three_column(table, "TMLF")
    if deal_type == "现券买断":
        return _extract_nb(table)
    return []


def extract(html: str) -> list[dict]:
    """从公告 HTML 中解析全部交易记录；解析不到时返回空列表。"""

    doc = pq(html)
    page_title = doc.find("title").text().strip()
    time = extract_time(doc)

    deals: list[dict] = []
    for table in doc.find("#zoom table").items():
        if table.find("table"):
            # 跳过外层嵌套表格，只解析叶子表格
            continue
        title = find_prev_text(table)
        if title:
            title = title.replace("\n", "").strip()
        table_deals = _extract_table(table, title)
        if not table_deals:
            logger.info("公告表格未命中提取规则: 公告=[%s] 表格标题=[%s]", page_title, title)
        deals.extend(table_deals)

    for deal in deals:
        deal["time"] = time
    return deals


def crawl_announcements(latest: str | None) -> list[dict]:
    """从索引页向前翻页，收集比 latest 更新的公告（新 -> 旧）。"""

    target_url = INDEX_URL
    seen: set[str] = set()
    announcements: list[dict] = []

    while target_url:
        if target_url in seen:
            raise RuntimeError(f"公告分页出现循环: {target_url}")
        seen.add(target_url)
        if len(seen) > MAX_PAGES:
            raise RuntimeError(f"公告分页超过 {MAX_PAGES} 页")

        logger.info("爬取 OMO 分页: %s", target_url)
        try:
            response = requests.get(target_url, timeout=TIMEOUT)
        except requests.RequestException as exc:
            raise RuntimeError(f"请求公告列表失败: {exc}") from exc
        if not response.ok:
            raise RuntimeError(f"公告列表返回 HTTP {response.status_code}")
        response.encoding = "utf-8"

        doc = pq(response.text)
        target_url = None
        for item in doc.find("#r_con a").items():
            title = item.text().strip()
            if title == "下一页":
                path = item.attr("tagname")
                if path and path != "[NEXTPAGE]":
                    target_url = f"{BASE_URL}{path}"
            elif title not in ("首页", "上一页", "尾页"):
                if latest and latest == title:
                    return announcements
                announcements.append(
                    {"title": title, "url": f"{BASE_URL}{item.attr('href')}"}
                )

    return announcements


def fetch_html(url: str) -> str:
    try:
        response = requests.get(url, timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise RuntimeError(f"请求公告正文失败: {url} ({exc})") from exc
    if not response.ok:
        raise RuntimeError(f"公告正文返回 HTTP {response.status_code}: {url}")
    response.encoding = "utf-8"
    return response.text


def run(config: Config) -> None:
    with closing(db.connect_business_db(config.db_path)) as conn:
        db.ensure_schema(conn)
        latest = db.get_app_state(conn, db.LATEST_OMO_DOC)
        announcements = crawl_announcements(latest)
        if not announcements:
            logger.info("OMO：没有新公告")
            return

        deals: list[dict] = []
        empty_titles: list[str] = []
        for announcement in announcements:
            html = fetch_html(announcement["url"])
            announcement_deals = extract(html)
            if not announcement_deals:
                empty_titles.append(announcement["title"])
            deals.extend(announcement_deals)

        if empty_titles:
            raise RuntimeError(
                "发现新公告但未解析出任何交易记录: " + "; ".join(empty_titles)
            )

        inserted = sum(1 for deal in deals if db.insert_omo_deal(conn, deal))
        db.set_app_state(conn, db.LATEST_OMO_DOC, announcements[0]["title"])
        conn.commit()

    logger.info(
        "OMO 抓取完成: 新公告 %d 份, 解析交易 %d 条, 新增 %d 条",
        len(announcements),
        len(deals),
        inserted,
    )
