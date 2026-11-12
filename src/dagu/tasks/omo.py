"""央行公开市场操作抓取：公告列表翻页 → 正文抓取 → 表格解析 → 入库。

由 Dagu 以独立进程执行：`python src/dagu/tasks/omo.py`。
不依赖 Web 端任何模块，数据库路径、表结构与入库语句均来自 `lib`。
"""

import re
import sys
from datetime import datetime
from pathlib import Path

# 允许以脚本方式直接运行：把 src/dagu 加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import logging

import requests
from pyquery import PyQuery as pq

from lib import config, db

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger("dagu.omo")

REQUEST_TIMEOUT = 30
LIST_URL = (
    "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html"
)
LATEST_DOC_COL = "latest_omo_doc"

# 交易有多种表头，解析时按标题匹配类型，再按列数映射字段
class OMOExtractor:
    __chineseNumbers = {
        "О": 0,
        "O": 0,
        "Ο": 0,
        "○": 0,
        "〇": 0,
        "一": 1,
        "二": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
        "十": None,  # 特别处理
    }

    # 仅支持两位数转换
    def parseDate(self, chineseNumber):
        if chineseNumber.isdigit():
            return int(chineseNumber)
        result = 0
        length = len(chineseNumber)
        for i, char in enumerate(chineseNumber):
            if char in self.__chineseNumbers:
                if char == "十":
                    if i == 0:  # 十在开头：十五 => 15
                        result += 1
                    elif i == length - 1:  # 十在结尾：二十 => 20
                        result = result * 10
                else:
                    result = result * 10 + self.__chineseNumbers[char]
            else:
                logger.warning("日期中存在错误字符 %s", char)
        return result

    def findPrevText(self, node):
        prevNodes = node.prevAll()
        for node in reversed(list(prevNodes.items())):
            text = node.text()
            if text:
                return text
        if node.parent():
            return self.findPrevText(node.parent())
        return None

    def extractTime(self, doc):
        zoom = doc.find("#zoom")
        lines = zoom.text().split()
        time = lines[len(lines) - 1]
        time = re.split("[年月日]", time)[:3]
        time = [self.parseDate(t) for t in time]

        return datetime(*time).strftime("%Y-%m-%d")

    # 提取指定公告中的央行公开市场操作
    def extract(self, html):
        doc = pq(html)
        # 页面标题，用于日志中标识是哪份公告（避免记录整页 HTML）
        pageTitle = doc.find("title").text().strip()
        time = self.extractTime(doc)
        tables = doc.find("#zoom table")
        deals = []

        for table in tables.items():
            if not table.find("table"):
                successFul = False  # 是否命中提取规则
                title = self.findPrevText(table)
                if title:
                    title = title.replace("\n", "")

                    if re.search(r"如下：", title):  # 只有一个表格，并且表格没有 title
                        if re.search(r"发行(.*)央行票据", title):
                            deals = self.extractYHPJ(table)
                            successFul = True
                        elif re.search(r"开展(.*)正回购", title):
                            deals = self.extractZHG(table)
                            successFul = True
                    else:
                        matches = re.search(
                            r"(.+)(?:发行|交易|操作|招标|到期续做|买断招标)情况$", title
                        )
                        if matches:
                            name = matches[1]

                            # 央行票据的名称中还包含期数，不需要
                            if name.find("央行票据") > -1:
                                name = "央行票据"

                            if name == "逆回购":
                                deals = self.extractNHG(table)
                                successFul = True
                            elif name == "正回购":
                                deals = self.extractZHG(table)
                                successFul = True
                            elif name == "MLF":
                                deals = self.extractMLF(table)
                                successFul = True
                            elif name == "TMLF":
                                deals = self.extractTMLF(table)
                                successFul = True
                            elif name == "央行票据":
                                deals = self.extractYHPJ(table)
                                successFul = True
                            elif name == "现券买断":
                                deals = self.extractGZ(table)
                                successFul = True

                if not successFul or not deals:
                    # 只记录公告标题和命中的表格标题，便于定位问题，避免刷屏
                    logger.info("提取失败: 公告=[%s] 表格标题=[%s]", pageTitle, title)

        # 子提取器在无有效行时会返回 None，统一兜底为空列表
        deals = deals or []
        for deal in deals:
            deal["time"] = time

        return deals

    # 央行票据
    def extractYHPJ(self, table):
        rows = table.find("tr")
        arr = []
        for i, row in enumerate(rows.items()):
            if i == 0:
                continue
            cells = row.find("td")
            d = {"type": "央行票据"}
            if len(cells) == 5:
                for i, k in enumerate(["name", "amount", "period", "price", "rate"]):
                    d[k] = cells.eq(i).text()
            elif len(cells) == 4:
                for i, k in enumerate(["name", "amount", "period", "rate"]):
                    d[k] = cells.eq(i).text()
                # 统一格式，便于操作数据库
                d["price"] = None
            else:
                d = None
            if d:
                arr.append(d)
        return arr if len(arr) > 0 else None

    # 逆回购
    def extractNHG(self, table):
        rows = table.find("tr")
        arr = []
        # 默认3列表头：期限、(交易/中标/招标)量、(中标/回购/招标)利率
        schema = ["period", "amount", "rate"]

        for i, row in enumerate(rows.items()):
            if i == 0:
                # 招标数量在前、且表头含"中标加权平均利率"的特殊3列格式
                if row.text() == "招标数量\n期限品种\n中标加权平均利率（%）":
                    schema = ["amount", "period", "rate"]
                # 2026年起出现的新4列格式：期限、操作利率、投标量、中标量
                elif row.text() == "期限\n操作利率\n投标量\n中标量":
                    schema = ["period", "rate", "bidAmount", "amount"]
                continue
            else:
                cells = row.find("td")
                d = {"type": "逆回购"}

                # 列数需与表头 schema 长度一致，否则视为异常行跳过
                if len(cells) == len(schema):
                    for i, k in enumerate(schema):
                        d[k] = cells.eq(i).text()
                else:
                    d = None

                if d:
                    arr.append(d)

        return arr if len(arr) > 0 else None

    # 正回购
    def extractZHG(self, table):
        return self.extractThreeColumns(table, "正回购")

    # MLF
    def extractMLF(self, table):
        return self.extractThreeColumns(table, "MLF")

    # 定向MLF
    def extractTMLF(self, table):
        return self.extractThreeColumns(table, "TMLF")

    def extractThreeColumns(self, table, typeName):
        rows = table.find("tr")
        arr = []

        for i, row in enumerate(rows.items()):
            if i == 0:
                continue

            cells = row.find("td")
            d = {"type": typeName}
            if len(cells) == 3:
                for i, k in enumerate(["period", "amount", "rate"]):
                    d[k] = cells.eq(i).text()
            else:
                d = None

            if d:
                arr.append(d)

        return arr if len(arr) > 0 else None

    # 国债
    def extractGZ(self, table):
        rows = table.find("tr")
        arr = []

        for i, row in enumerate(rows.items()):
            if i == 0:
                continue

            cells = row.find("td")
            d = {"type": "国债"}
            if len(cells) == 3:
                for i, k in enumerate(["period", "price", "amount"]):
                    d[k] = cells.eq(i).text()
            elif len(cells) == 4:
                for i, k in enumerate(["name", "period", "price", "amount"]):
                    d[k] = cells.eq(i).text()
            else:
                d = None

            if d:
                arr.append(d)

        return arr if len(arr) > 0 else None


def fetchPage(url: str) -> str:
    response = requests.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    response.encoding = "utf-8"
    return response.text


def crawlOMOUrl(latest: str | None) -> list[dict]:
    """从列表页开始翻页，收集比最新公告更新的条目（新→旧）。"""
    target_url = LIST_URL
    newList = []

    while target_url:
        logger.info("爬取分页：%s", target_url)
        doc = pq(fetchPage(target_url))

        target_url = None
        for item in doc.find("#r_con a").items():
            title = item.text()
            if title == "下一页":
                target_path = item.attr("tagname")
                if target_path != "[NEXTPAGE]":
                    target_url = f"http://www.pbc.gov.cn{target_path}"
            elif title != "首页" and title != "上一页" and title != "尾页":
                if latest and latest == title:
                    break
                else:
                    newList.append(
                        {
                            "title": title,
                            "url": f"http://www.pbc.gov.cn{item.attr('href')}",
                        }
                    )

    return newList


def saveHtml(title: str, html: str) -> None:
    """保存 HTML 到本地，便于离线分析与回归测试。"""
    config.OMO_HTML_DIR.mkdir(parents=True, exist_ok=True)
    htmlPath = config.OMO_HTML_DIR / f"{title}.html"
    try:
        htmlPath.write_text(html, encoding="utf-8")
    except Exception as error:  # 仅告警：辅助产物，不影响入库
        logger.warning("保存 HTML 失败: %s %s", htmlPath, error)


def crawlOMOHtml(doc: dict) -> str:
    docUrl = doc["url"]
    logger.info("爬取公告内容：%s", docUrl)
    html = fetchPage(docUrl)
    saveHtml(doc["title"], html)
    return html


def storeDeal(connection, deal: dict) -> None:
    """按交易类型写入对应表，主键冲突忽略。"""
    if deal["type"] == "正回购":
        db.upsertOmoRow(
            connection,
            "omo_repo",
            ["time", "period", "amount", "rate"],
            [deal["time"], deal["period"], deal["amount"], deal["rate"]],
            ["time", "period"],
        )
    elif deal["type"] == "逆回购":
        db.upsertOmoRow(
            connection,
            "omo_rrp",
            ["time", "period", "amount", "rate"],
            [deal["time"], deal["period"], deal["amount"], deal["rate"]],
            ["time", "period"],
        )
    elif deal["type"] == "MLF":
        db.upsertOmoRow(
            connection,
            "omo_mlf",
            ["time", "period", "amount", "rate"],
            [deal["time"], deal["period"], deal["amount"], deal["rate"]],
            ["time", "period"],
        )
    elif deal["type"] == "TMLF":
        db.upsertOmoRow(
            connection,
            "omo_tmlf",
            ["time", "period", "amount", "rate"],
            [deal["time"], deal["period"], deal["amount"], deal["rate"]],
            ["time", "period"],
        )
    elif deal["type"] == "央行票据":
        db.upsertOmoRow(
            connection,
            "omo_cb",
            ["time", "name", "amount", "period", "price", "rate"],
            [
                deal["time"],
                deal["name"],
                deal["amount"],
                deal["period"],
                deal["price"],
                deal["rate"],
            ],
            ["time", "name"],
        )
    elif deal["type"] == "国债":
        db.upsertOmoRow(
            connection,
            "omo_nb",
            ["time", "period", "amount", "price"],
            [deal["time"], deal["period"], deal["amount"], deal["price"]],
            ["time", "period"],
        )


def job() -> None:
    """每天爬一次公开市场操作。"""
    logger.info(config.describe())
    extractor = OMOExtractor()
    connection = db.connect()
    try:
        db.ensureSchema(connection)
        latestDocName = db.getAppState(connection, LATEST_DOC_COL)
        urlList = crawlOMOUrl(latestDocName)

        totalDeals = 0
        for doc in urlList:
            html = crawlOMOHtml(doc)
            if not html:
                logger.info("content empty: %s", doc["url"])
                continue
            deals = extractor.extract(html)
            totalDeals += len(deals)
            for deal in deals:
                storeDeal(connection, deal)

        # 有新公告却一条记录都没解析出来，说明页面结构可能变化，直接失败
        if urlList and totalDeals == 0:
            raise RuntimeError(
                f"发现 {len(urlList)} 份新公告，但未解析出任何公开市场操作记录"
            )

        # 记录最新的公告名称；urlList 中元素排列顺序是：新→旧
        if urlList:
            db.upsertAppState(connection, LATEST_DOC_COL, urlList[0]["title"])

        connection.commit()
        logger.info("本次新增公告 %s 份，解析记录 %s 条", len(urlList), totalDeals)
    finally:
        connection.close()


if __name__ == "__main__":
    job()
