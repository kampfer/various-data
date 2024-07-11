import requests
from pyquery import PyQuery as pq
import os
from constants import DATA_PATH
import json
import re
from ernie_speed_128k import ie_by_ernie

announcementsJsonPath = os.path.join(DATA_PATH, "omo/announcements.json")
dataPath = os.path.join(DATA_PATH, "omo/data.json")
contentPath = os.path.join(DATA_PATH, "omo/contents/")
htmlContentPath = os.path.join(DATA_PATH, "omo/html/")


def readJson(filePath):
    f = open(filePath, "r", encoding="utf-8")
    data = json.loads(f.read())
    f.close()
    return data


def writeJson(filePath, data):
    f = open(filePath, "w", encoding="utf-8")
    f.write(json.dumps(data, ensure_ascii=False))
    f.close()


def readFile(filePath):
    f = open(filePath, "r", encoding="utf-8")
    data = f.read()
    return data


def writeFile(filePath, content):
    f = open(filePath, "w", encoding="utf-8")
    f.write(content)
    f.close()


# 存在重复数据：
# 公开市场业务交易公告 [2008]第27号
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/2837730/index.html
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/2837727/index.html
def checkDuplicated():
    f = open(announcementsJsonPath, "r")
    omo_list = json.loads(f.read())
    f.close()
    d = {}
    for item in omo_list:
        if item["title"] in d:
            d[item["title"]] += 1
        else:
            d[item["title"]] = 1
    s = [k for k, v in d.items() if v > 1]
    print(s)


def crawlOMOHtml(omo_list):
    for p in omo_list:
        # txt_content = crawlOMO()
        target_url = f"http://www.pbc.gov.cn{p['url']}"
        txtPath = f'{htmlContentPath}{p["title"]}.html'
        res = requests.get(target_url)
        res.encoding = "utf-8"
        html_text = res.text
        if html_text == "":
            print(f'content empty: {p["url"]}')
        f = open(txtPath, "w")
        f.write(html_text)
        f.close()

        print(f"crawl omo: {target_url}")


# 统计央行表格头的类型
# 1. 不是所有表格都有标题
# 2. 标题中可能包含到期信息
# 3. 正回购和逆回购的表格头是一样的
# 4. 央行票据有多种表格头
def statisticTableHeads(omoList):
    # 表格与交易类型的对照表（手动维护）
    for item in omoList:
        # if item['url'] != '/zhengcehuobisi/125207/125213/125431/125475/2844741/index.html':
        #     continue
        htmlFilePath = os.path.join(htmlContentPath, f'{item["title"]}.html')
        if not os.path.exists(htmlFilePath):
            crawlOMOHtml([item])
        html = readFile(htmlFilePath)
        doc = pq(html)
        zoom = doc.find("#zoom")
        tables = zoom.find("table")

        for table in tables.items():
            if not table.find("table"):
                tr = table.find("tr").eq(0)
                trText = tr.text()
                if trText in head2Deal:
                    deal = head2Deal[trText]
                    if "files" not in deal:
                        deal["files"] = [htmlFilePath]
                    else:
                        deal["files"].append(htmlFilePath)
                else:
                    print(f"{trText} 没有对应交易类型")

    return head2Deal


# list存在 - 增量更新
# list不存在 - 全量跟新
#
# 首页地址：
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/17081/index1.html
def updateOMOList(list):
    latest = list[0] if list else None

    target_url = (
        "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html"
    )
    newList = []

    while target_url:
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
                if latest and latest["title"] == title:
                    return newList, (newList + list)
                else:
                    newList.append({"title": title, "url": item.attr("href")})

    return newList, newList


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
    def findPrevText(self, node):
        prevNodes = node.prevAll()
        for node in reversed(list(prevNodes.items())):
            text = node.text()
            if text:
                return text
        if node.parent():
            return self.findPrevText(node.parent())
        return None

    # 提取指定公告中的央行公开市场操作
    def extract(self, htmlFilePath):
        html = readFile(htmlFilePath)
        doc = pq(html)
        tables = doc.find("#zoom table")
        time = doc.find("#shijian").text()
        deals = []

        for table in tables.items():
            if not table.find("table"):
                successFul = False  # 是否命中提取规则
                title = self.findPrevText(table)
                if title:
                    title = title.replace("\n", "")

                    if re.search(r"如下：", title):  # 只有一个表格，并且表格没有title
                        if re.search(r"发行(.*)央行票据", title):
                            deals = extractor.extractYHPJ(table)
                            successFul = True
                        elif re.search(r"开展(.*)正回购", title):
                            deals = extractor.extractZHG(table)
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
                                deals = extractor.extractNHG(table)
                                successFul = True
                            elif name == "正回购":
                                deals = extractor.extractZHG(table)
                                successFul = True
                            elif name == "MLF":
                                deals = extractor.extractMLF(table)
                                successFul = True
                            elif name == "TMLF":
                                deals = extractor.extractTMLF(table)
                                successFul = True
                            elif name == "央行票据":
                                deals = extractor.extractYHPJ(table)
                                successFul = True
                            elif name == "现券买断":
                                deals = extractor.extractGZ(table)
                                successFul = True

                if not successFul:
                    print(f"提取失败: {htmlFilePath}")

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


if __name__ == "__main__":
    extractor = OMOExtOMOractor()
    omoList = readJson(announcementsJsonPath)
    allDeal = {}
    for omo in omoList:
        htmlFilePath = os.path.join(htmlContentPath, omo["title"] + ".html")
        deals = extractor.extract(htmlFilePath)
        for deal in deals:
            type = deal["type"]
            if type in allDeal:
                allDeal[type].append(deal)
            else:
                allDeal[type] = [deal]
    writeJson("omo.json", allDeal)

    # for d in allDeal["逆回购"]:
    #     print(d["time"], d["rate"])
