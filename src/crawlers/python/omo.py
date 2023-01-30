import requests
import json
import os
from urllib.parse import urlparse
from pyquery import PyQuery as pq
import re
from constants import DATA_PATH

# python src/crawlers/python/omo.py

announcementsJsonPath = os.path.join(DATA_PATH, 'omo/announcements.json')
contentPath = os.path.join(DATA_PATH, 'omo/contents/')

def crawlOMO():
  headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Accept-Encoding': 'gzip, deflate',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'Cache-Control': 'no-cache',
    'Host': 'www.pbc.gov.cn',
    'Pragma': 'no-cache',
    'Connection': 'keep-alive',
    'Referer': 'http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36 Edg/109.0.1518.70'
  }

  # 貌似是根据request header参数生成的，需要对应上
  cookies = {
    'wzws_cid': 'e1e3595310dc9defebb164cb6782103762703340fb934e93233e1ab5dee210cbb09003d25fecce60e3c3882e97a7dd8520f4eab4d71524c63dac0fa254b5a2e820567b6c2ed38c1bb8e75be2f198d683',
    'wzws_sessionid': 'gjc0Y2Y0MaBj1cHjgThiMjgzZYA1OS4xNzIuNjIuMjY='
  }

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

  # 如果公告数据已经存在并且新数据与旧数据长度一致，就不需要更新公告数据json文件
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

  # 爬取公告详情并保存
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

from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By

def getWebDriver():
  driverPath = '/home/liao/msedgedriver'
  service = Service(executable_path=driverPath)

  options = Options()
  options.add_argument("headless")
  options.add_argument("--no-sandbox")

  return webdriver.Edge(service = service, options = options)

# 爬取公告列表
# 排序：新-》旧
# limit参数可以限制数量
def crawlAnnouncementListBySelenium(driver, limit):
  target = 'http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html'
  announcements = []
  while(target):
    print(f'get page: {target}')
    driver.get(target)
    target = None
    anchors = driver.find_elements(By.CSS_SELECTOR, '#r_con a')
    for a in anchors:
      text = a.text
      if re.match('首页', text):
        continue
      elif re.match('上一页', text):
        continue
      elif re.match('下一页', text):
        tagname = a.get_attribute('tagname')
        if tagname != '[NEXTPAGE]':
          target = f'http://www.pbc.gov.cn{tagname}'
      elif re.match('尾页', text):
        continue
      else:
        announcements.append({
          'title': text,
          'url': a.get_attribute('href')
        })
        if len(announcements) >= limit:
          break
  return announcements

# 爬取单个公告详情
def crawlAnnouncementBySelenium(driver, url):
  print(f'get content: {url}')
  driver.get(url)
  elements = driver.find_elements(By.CSS_SELECTOR, '#zoom')
  content = elements[0].text
  lines = content.splitlines()
  strLen = list(map(len, lines))
  maxLine = lines[strLen.index(max(strLen))]
  res = re.findall('逆回购|正回购|央行票据|中期借贷便利', maxLine)
  print(res)
  # maxLine = max(line.strip() for line in lines)
  return content

def crawlAnnouncementsByList(driver, list):
  for announcement in announcements:
    txtFilePath = f'{contentPath}{announcement["title"]}.txt'
    print(f'get content: {announcement["url"]}')
    content = crawlAnnouncementBySelenium(driver, announcement['url'])
    if content == '':
      print(f'content empty: {announcement["url"]}')
    f = open(txtFilePath, 'w')
    f.write(content)
    f.close()

def saveAnnouncement(announcement, content):
  txtFilePath = f'{contentPath}{announcement["title"]}.txt'
  f = open(txtFilePath, 'w')
  f.write(content)
  f.close()

# 全量爬取，覆盖所有旧数据（用于初始化数据）
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html
# http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/17081/index1.html
def crawlOMOBySelenium(driver):
  announcements = crawlAnnouncementListBySelenium(driver)

  print('update json')
  f = open(announcementsJsonPath, 'w')
  f.write(json.dumps(announcements))
  f.close()

  for announcement in announcements:
    txtFilePath = f'{contentPath}{announcement["title"]}.txt'
    print(f'get content: {announcement["url"]}')
    content = crawlAnnouncementBySelenium(driver, announcement['url'])
    if content == '':
      print(f'content empty: {announcement["url"]}')
    f = open(txtFilePath, 'w')
    f.write(content)
    f.close()

def updateOMOBySelenium(driver):
  driver.get('http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/index.html')
  tableElems = driver.find_elements(By.CSS_SELECTOR, '#r_con table')
  tableCount = len(tableElems)
  content = tableElems[tableCount - 1].text
  matchObject = re.search(r'总记录数:(\d+),每页显示(\d+)条记录', content)
  total = int(matchObject.group(1))
  pageNum = int(matchObject.group(2))

  f = open(announcementsJsonPath, 'r')
  data = json.load(f)
  dataLen = len(data)
  list = crawlAnnouncementListBySelenium(driver, total - dataLen)

  for i in range(len(list) - 1, -1, -1):
    data.insert(0, list[i])
    content = crawlAnnouncementBySelenium(driver, list[i]['url'])
    saveAnnouncement(list[i], content)

  f = open(announcementsJsonPath, 'w')
  f.write(json.dumps(data))
  f.close()

driver = getWebDriver()
try:
  # updateOMOBySelenium(driver)
  crawlAnnouncementBySelenium(driver, 'http://www.pbc.gov.cn/zhengcehuobisi/125207/125213/125431/125475/3971702/index.html')
finally:
  driver.quit()
