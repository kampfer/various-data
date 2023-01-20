import requests
import json
import os
from urllib.parse import urlparse
from pyquery import PyQuery as pq
import re
from constants import DATA_PATH

# python src/crawlers/python/omo.py

headers = {
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
  'Accept-Encoding': 'gzip, deflate',
  'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
  'Cache-Control': 'no-cache',
  'Host': 'www.pbc.gov.cn',
  'Pragma': 'no-cache',
  'Proxy-Connection': 'keep-alive',
  'Referer': 'http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html',
  'Upgrade-Insecure-Requests': '1',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.55',
  'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
  'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.55'
}

cookies = {
  'wzws_cid': '578d684459fd4fe54d4324f4df13370e4568717d9ccd675d09966cd1dcdcf7bd4f6ae60c7e34b578840a723f0f2b118ed1528c02374ef29dbeeea6e2bc3857ce08656bd2a80f6aea8c32b483da629ace',
  'wzws_sessionid': 'gWIzNmJhYYI3NGNmNDGANTkuMTcyLjYyLjI2oGPI/js='
}

announcementsJsonPath = os.path.join(DATA_PATH, 'omo/announcements.json')
contentPath = os.path.join(DATA_PATH, 'omo/contents/')

# 爬取所有公开市场业务交易报告地址
target = 'http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html'
announcements = []
while(target):
  print(f'get page: {target}')
  r = requests.get(target, cookies=cookies, headers=headers)
  target = None
  r.encoding = 'utf-8'
  doc = pq(r.text)
  anchors = doc('#r_con a').items()
  for a in anchors:
    text = a.text()
    if re.match('首页', text):
      continue
    elif re.match('上一页', text):
      continue
    elif re.match('下一页', text):
      tagname = a.attr('tagname')
      if tagname != '[NEXTPAGE]':
         target = f'http://www.pbc.gov.cn{tagname}'
    elif re.match('尾页', text):
      continue
    else:
      announcements.append({
        'title': text,
        'url': f'http://www.pbc.gov.cn{a.attr("href")}'
      })

needUpdateJson = True
if os.path.exists(announcementsJsonPath):
  with open(announcementsJsonPath, 'r') as f:
    data = json.load(f)
    if len(data) == len(announcements):
      needUpdateJson = False
if needUpdateJson:
  print('update json')
  f = open(announcementsJsonPath, 'w')
  f.write(json.dumps(announcements))
  f.close()

print(f'total: {len(announcements)}')

# 存在重复数据
# 公开市场业务交易公告 [2008]第27号
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/2837730/index.html
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/2837727/index.html
def checkDuplicated():
  d = {}
  for item in announcements:
    if item['title'] in d:
      d[item['title']] += 1
    else:
      d[item['title']] = 1
  s = [k for k,v in d.items() if v > 1]
  print(s)

for announcement in announcements:
  txtFilePath = f'{contentPath}{announcement["title"]}.txt'
  needGetContent = True
  if os.path.exists(txtFilePath):
    f = open(txtFilePath, 'r')
    if f.read() != '':
      needGetContent = False
  if needGetContent:
    print(f'get content: {announcement["url"]}')
    r = requests.get(announcement['url'], cookies=cookies, headers=headers)
    r.encoding = 'utf-8'
    doc = pq(r.text)
    # html结构不一致，需要处理
    # content = doc('div[aria-label="内容文本区"]').text()
    content = doc('#pre table.hui12 + *').text()
    if content == '':
      print(f'content empty: {announcement["url"]}')
      break
    f = open(txtFilePath, 'w')
    f.write(content)
    f.close()
