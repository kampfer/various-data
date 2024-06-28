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
    f.write(json.dumps(data))
    f.close()


def readFile(filePath):
    f = open(filePath, "r", encoding="utf-8")
    data = f.read()
    return data


def extractOMO(html):
    def findPrev(elem):
        all = elem.prev_all('p')
        i = len(all) - 1
        while not all[i].text():
            i += 1
        return all[i]

    doc = pq(html)

    time = doc("#shijian").text()

    tables = doc.find("#zoom table")
    # zoom_children = list(zoom.children().items())
    for i, elem in enumerate(tables.items()):
        if elem.is_("table") and len(elem.find('tr')) > 1:
            prev = findPrev(elem)
            type = prev.text()
            # type = re.search(r"央行票据|逆回购|MLF", type).group(0)
            print(type)
            # print(elem.text())
            if type == "逆回购":
                print(elem.text().split("\n"))
            elif type == "央行票据":
                continue
            elif type == "MLF":
                continue
            else:
                continue
    # tables = zoom.find('table')
    # for i, table in enumerate(tables.items()):
    #     trs = table.find('tr')
    #     ret = []
    #     for tr in trs.items():
    #         ret.append([td.text() for td in tr.find('td').items()])


def extractOMO2(text):
    # doc = pq(html)

    # title = doc.find("title").text()

    # zoom = doc.find("#zoom")
    lines = text.replace(' ', '').split()
    # if re.search(' ', text):
    #     breakpoint()
    if len(lines) > 3:
        longest = lines.index(sorted(lines, key=lambda v: len(v), reverse=True)[0])
        print(lines[longest])
        # lines = lines[longest+1:-2]
        # print(lines)
        reg = r'正回购|逆回购|央行票据|MLF'
        print(re.findall(reg, lines[longest]))
        cur = 0
        finded = False
        while cur < len(lines):
            if re.search(reg, lines[cur]):
                finded = True
            cur += 1
        # if not finded: print(text)
        return True
    else:
        return False
    
    # arr = content[longest + 1:-2]
    # if len(arr) > 0:
    #   print(arr)


# 全量爬取，覆盖所有旧数据（用于初始化数据）
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/17081/index1.html
def crawlOMOList():
    target_url = (
        "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html"
    )
    omo_list = []

    while target_url:
        print(f"crawl omo list: {target_url}")
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
                omo_list.append({"title": title, "url": item.attr("href")})

    return omo_list


# 存在重复数据
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


def crawlOMOTxt():
    if os.path.exists(announcementsJsonPath):
        f = open(announcementsJsonPath, "r")
        omo_list = json.loads(f.read())
        f.close()
    else:
        omo_list = crawlOMOList()

        f = open(announcementsJsonPath, "w")
        f.write(json.dumps(omo_list))
        f.close()

    for p in omo_list:
        txt_content = crawlOMO(f"http://www.pbc.gov.cn{p['url']}")
        txtPath = f'{contentPath}{p["title"]}.txt'
        if txt_content == "":
            print(f'content empty: {p["url"]}')
        f = open(txtPath, "w")
        f.write(txt_content)
        f.close()


def crawlOMOHtml():
    if os.path.exists(announcementsJsonPath):
        f = open(announcementsJsonPath, "r")
        omo_list = json.loads(f.read())
        f.close()
    else:
        omo_list = crawlOMOList()

        f = open(announcementsJsonPath, "w")
        f.write(json.dumps(omo_list))
        f.close()

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


if __name__ == "__main__":
    # urls = [
    #     "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/5381883/index.html",  # 逆回购
    #     "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/5379475/index.html",  # 央行票据(香港)
    #     "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/5228967/index.html",  # 逆回购多期限
    #     "http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/5169908/index.html",  # 逆回购+MLF
    # ]
    # checkDuplicated()
    # crawlOMOHtml()
    # crawlOMO(urls[3])

    omo_list = readJson(announcementsJsonPath)
    # omoFiles = os.listdir(htmlContentPath)
    omoFiles = os.listdir(contentPath)

    i = 0
    emptyFiles = []
    for p in omoFiles:
        filePath = os.path.join(contentPath, p)
        content = readFile(filePath)
        if extractOMO2(content):
            i += 1
        else:
            emptyFiles.append(filePath)
    # 保存没有操作的公告文件路径，留作测试用
    writeJson(os.path.join(DATA_PATH, "omo/empty.json"), emptyFiles)
    print(f'{i}/{len(omo_list)}')
