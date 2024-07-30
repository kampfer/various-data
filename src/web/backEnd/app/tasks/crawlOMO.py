# 方便调试
if __name__ == "__main__":
    import os

    os.sys.path.append(os.path.realpath(os.path.join(__file__, "../../../")))

import re
from datetime import datetime

import requests
from pyquery import PyQuery as pq

from app.logger import logger
from app.database import SessionLocal
from app.omo.crud import (
    getLatestDocName,
    addCB,
    addNB,
    addMLF,
    addTMLF,
    addRepo,
    addRRP,
    setLatestDocName,
)


# 交易有多种head
# {
#   "逆回购": {
#     "期限\n中标量\n中标利率": 1,
#     "期限\n交易量\n中标利率": 1,
#     "期限\n交易量\n回购利率": 1,
#     "期限\n交易量\n招标利率": 1,
#     "期限品种\n招标数量\n招标利率": 1,
#     "招标数量\n期限品种\n中标加权平均利率（%）": 1
#   },
#   "MLF": {
#     "期限\n操作量\n中标利率": 1,
#     "期限\n操作量\n操作利率": 1,
#     "期限\n中标量\n中标利率": 1
#   },
#   "现券买断": { "券种\n买入价格（元）\n招标量（亿元）": 1 },
#   "TMLF": { "期限\n操作量\n操作利率": 1 },
#   "正回购": {
#     "期限\n交易量\n中标利率": 1,
#     "期限\n交易量\n加权平均中标利率": 1
#   },
#   "央行票据": {
#     "名称\n续做量\n期限\n利率": 1,
#     "名称\n发行量\n期限\n价格\n参考收益率": 1,
#     "名称\n发行量\n期限\n中标利率": 1,
#     "名称\n发行量\n期限\n价格(元)\n参考收益率": 1,
#     "名称\n发行量\n期限\n发行价格\n参考收益率": 1,
#     "名称\n发行量\n期限\n票面利率": 1,
#     "名称\n发行量\n期限\n招标价格\n参考收益率": 1,
#     "名称\n发行量\n期限\n加权平均价格\n参考收益率": 1
#   }
# }
class OMOExtOMOractor:
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
        l = len(chineseNumber)
        for i, char in enumerate(chineseNumber):
            if char in self.__chineseNumbers:
                if char == "十":
                    if i == 0:  # 十在开头：十五 =》 15
                        result += 1
                    elif i == l - 1:  # 十在结尾：二十 =》 20
                        result = result * 10
                else:
                    result = result * 10 + self.__chineseNumbers[char]
            else:
                logger.warn(f"日期中存在错误字符 {char}")
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
        time = self.extractTime(doc)
        tables = doc.find("#zoom table")
        deals = []

        for table in tables.items():
            if not table.find("table"):
                successFul = False  # 是否命中提取规则
                title = self.findPrevText(table)
                if title:
                    title = title.replace("\n", "")

                    if re.search(r"如下：", title):  # 只有一个表格，并且表格没有title
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

                            # head = table.find("tr").eq(0).text()
                            # if name not in d:
                            #     d[name] = {}
                            # d[name][head] = 1

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

                if not successFul:
                    logger.info(f"提取失败: {html}")

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
        schema = ["period", "amount", "rate"]

        for i, row in enumerate(rows.items()):
            if i == 0:
                if row.text() == "招标数量\n期限品种\n中标加权平均利率（%）":
                    schema = ["amount", "period", "rate"]
                continue
            else:
                cells = row.find("td")
                d = {"type": "逆回购"}

                if len(cells) == 3:
                    for i, k in enumerate(schema):
                        d[k] = cells.eq(i).text()
                else:
                    d = None

                if d:
                    arr.append(d)

        return arr if len(arr) > 0 else None

    # 正回购
    def extractZHG(self, table):
        rows = table.find("tr")
        arr = []

        for i, row in enumerate(rows.items()):
            if i == 0:
                continue

            cells = row.find("td")
            d = {"type": "正回购"}
            if len(cells) == 3:
                for i, k in enumerate(["period", "amount", "rate"]):
                    d[k] = cells.eq(i).text()
            else:
                d = None

            if d:
                arr.append(d)

        return arr if len(arr) > 0 else None

    # MLF
    def extractMLF(self, table):
        rows = table.find("tr")
        arr = []

        for i, row in enumerate(rows.items()):
            if i == 0:
                continue

            cells = row.find("td")
            d = {"type": "MLF"}
            if len(cells) == 3:
                for i, k in enumerate(["period", "amount", "rate"]):
                    d[k] = cells.eq(i).text()
            else:
                d = None

            if d:
                arr.append(d)

        return arr if len(arr) > 0 else None

    # 定向MLF
    def extractTMLF(self, table):
        rows = table.find("tr")
        arr = []

        for i, row in enumerate(rows.items()):
            if i == 0:
                continue

            cells = row.find("td")
            d = {"type": "TMLF"}
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
            else:
                d = None

            if d:
                arr.append(d)

        return arr if len(arr) > 0 else None


def crawlOMOUrl(latest):
    # 开发调试时读取本地文件
    # if os.getenv('mode') == 'dev':
    #     import json

    #     with open("./data/omo/announcements.json") as f:
    #         data = json.loads(f.read())
    #         f.close()
    #         return data

    target_url = (
        "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html"
    )
    newList = []

    while target_url:
        logger.info(f"爬取分页：{target_url}")
        res = requests.get(target_url)
        res.encoding = "utf-8"

        doc = pq(res.text)

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


def crawlOMOHtml(doc):
    # if os.getenv('mode') == 'dev':
    #     logger.info(f"读取公告内容：{doc['title']}")
    #     htmlPath = f"./data/omo/html/{doc['title']}.html"
    #     if os.path.exists(htmlPath):
    #         with open(htmlPath) as f:
    #             data = f.read()
    #             f.close()
    #             return data
    #     else:
    #         return None

    docUrl = doc["url"]
    logger.info(f"爬取公告内容：{docUrl}")
    res = requests.get(docUrl)
    res.encoding = "utf-8"
    html_text = res.text
    return html_text


# 每天爬一次公开市场操作
def job():
    extractor = OMOExtOMOractor()
    with SessionLocal() as session:
        latestDocName = getLatestDocName(session)
        urlList = crawlOMOUrl(latestDocName)

        for doc in urlList:
            html = crawlOMOHtml(doc)
            if not html:
                logger.info(f"content empty: {doc['url']}")
                continue
            deals = extractor.extract(html)
            for deal in deals:
                if deal["type"] == "正回购":
                    addRepo(
                        session,
                        deal["time"],
                        deal["period"],
                        deal["amount"],
                        deal["rate"],
                    )
                elif deal["type"] == "逆回购":
                    addRRP(
                        session,
                        deal["time"],
                        deal["period"],
                        deal["amount"],
                        deal["rate"],
                    )
                elif deal["type"] == "MLF":
                    addMLF(
                        session,
                        deal["time"],
                        deal["period"],
                        deal["amount"],
                        deal["rate"],
                    )
                elif deal["type"] == "TMLF":
                    addTMLF(
                        session,
                        deal["time"],
                        deal["period"],
                        deal["amount"],
                        deal["rate"],
                    )
                elif deal["type"] == "央行票据":
                    addCB(
                        session,
                        deal["time"],
                        deal["name"],
                        deal["period"],
                        deal["amount"],
                        deal["rate"],
                        deal["price"],
                    )
                elif deal["type"] == "国债":
                    addNB(
                        session,
                        deal["time"],
                        deal["period"],
                        deal["amount"],
                        deal["price"],
                    )

        # 记录最新的公告名称
        # urlList中的元素排列顺序是：新-旧
        if len(urlList) > 0:
            setLatestDocName(session, urlList[0]["title"])


def addJob(scheduler):
    # scheduler.add_job(job, "interval", days=1, id=__name__, coalesce=True)
    scheduler.add_job(job, "cron", hour=12, id=__name__, coalesce=True)


# 调试代码
if __name__ == "__main__":
    from app.omo.models import Base
    from app.database import engine

    Base.metadata.create_all(bind=engine)
    job()
