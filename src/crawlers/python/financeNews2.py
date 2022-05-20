import re
import time
import requests
from bs4 import BeautifulSoup
import math

# 调试用
# import http.client as http_client
# import logging
# http_client.HTTPConnection.debuglevel = 1
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

s = requests.Session()

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,is;q=0.5',
    'Cache-Control': 'no-cache',
    'Connection': 'keep-alive',
    'Host': 'kns.cnki.net',
    'Pragma': 'no-cache',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="101", "Microsoft Edge";v="101"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-User': '?1',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.47'
}

r1 = s.get('https://kns.cnki.net/kns/request/SearchHandler.ashx', params={
    'action': '',
    'NaviCode': '*',
    'catalogName': 'ZJCLS',
    'ua': 1.21,
    'isinEn': 0,
    'PageName': 'ASP.brief_result_aspx',
    'DbPrefix': 'CCND',
    'DbCatalog': '中国重要报纸全文数据库',
    'ConfigFile': 'CCND.xml',
    'db_opt': 'CCND',
    'db_value': '中国重要报纸全文数据库综合',
    'publishdate_from': '2015-01-01',
    'publishdate_to': '2015-12-31',
    'CKB_extension': 'ZYW',
    'his': 0,
    '__': time.time(),
    'magazine_value1': '中国证券报',
    'magazine_special1': '%'
}, headers=headers)

totalPattern = re.compile(r'\s找到\s(.*)\s条结果\s')

def crawlPage(pageNo, pageSize):
    data = []
    r = s.get('https://kns.cnki.net/kns/brief/brief.aspx', params={
        'curpage': pageNo,
        'RecordsPerPage': pageSize,
        'QueryID': '1',
        'ID': '',
        'turnpage': '1',
        'tpagemode': 'L',
        'dbPrefix': 'CCND',
        'Fields': '',
        'DisplayMode': 'listmode',
        'PageName': 'ASP.brief_result_aspx',
        'isinEn': '0'
    }, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    rows = soup.select('.GridTableContent tr:not(.GTContentTitle)')
    totalContent = soup.find('table', class_='pageBar_top').find('div', class_='pagerTitleCell').text
    total = int(totalPattern.match(totalContent).group(1).replace(',', ''))
    print(total)
    for row in rows:
        cols = row.select('td')
        col = {
            'title': cols[1].text,
            'author': cols[2].text,
            'source': cols[3].text,
            'date': cols[4].text,
            'url': cols[1].find('a').attrs['href']
        }
        data.append(col)
    return data

# print(crawlPage(1, 20))
# crawlPage(1, 20)

pageNo = 1
pageSize = 20
data = []
total = math.inf

while(len(data) < total):
    print(f'第{pageNo}页')
    r = s.get('https://kns.cnki.net/kns/brief/brief.aspx', params={
        'curpage': pageNo,
        'RecordsPerPage': pageSize,
        'QueryID': '1',
        'ID': '',
        'turnpage': '1',
        'tpagemode': 'L',
        'dbPrefix': 'CCND',
        'Fields': '',
        'DisplayMode': 'listmode',
        'PageName': 'ASP.brief_result_aspx',
        'isinEn': '0'
    }, headers=headers)
    soup = BeautifulSoup(r.text, 'html.parser')
    rows = soup.select('.GridTableContent tr:not(.GTContentTitle)')
    totalContent = soup.find('table', class_='pageBar_top').find('div', class_='pagerTitleCell').text
    total = int(totalPattern.match(totalContent).group(1).replace(',', ''))
    # print(total)
    for row in rows:
        cols = row.select('td')
        col = {
            'title': cols[1].text,
            'author': cols[2].text,
            'source': cols[3].text,
            'date': cols[4].text,
            'url': cols[1].find('a').attrs['href']
        }
        data.append(col)
    pageNo += 1
