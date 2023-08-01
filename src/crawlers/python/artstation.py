import requests
import json
import os
from urllib.parse import urlparse
from pyquery import PyQuery as pq
import argparse

# 调试用
# import http.client as http_client
# import logging
# http_client.HTTPConnection.debuglevel = 1
# logging.basicConfig()
# logging.getLogger().setLevel(logging.DEBUG)
# requests_log = logging.getLogger("requests.packages.urllib3")
# requests_log.setLevel(logging.DEBUG)
# requests_log.propagate = True

dataPath = os.path.normpath(os.path.join(__file__, '../../../../data'))

useProxy = False

proxies = {
    'http': 'http://127.0.0.1:41091',
    'https': 'http://127.0.0.1:41091'
} if useProxy else None

def basename(url):
    urlObj = urlparse(url)
    return os.path.basename(urlObj.path)

def crawlImage(url, savePath):
    r = requests.get(url, proxies=proxies)
    with open(savePath, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)

def crawlMP4(url, savePath, s):
    headers = {
        'range': 'bytes=0-',
        # 'referer': 'https://www.artstation.com/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.64 Safari/537.36 Edg/101.0.1210.47',
        'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="101", "Microsoft Edge";v="101"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Host': 'cdn-animation.artstation.com',
        'Upgrade-Insecure-Requests': '1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6,is;q=0.5',
        'Cache-Control': 'no-cache'
    }
    r = s.get(url, proxies=proxies, headers=headers)
    with open(savePath, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=1024):
            fd.write(chunk)

def crawlArtstationProject(id, session):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'Referer': 'https://www.artstation.com/artwork/nEmaAe',
        'Sec-Ch-Ua': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36'
    }
    r = session.get(f'https://www.artstation.com/projects/{id}.json', proxies=proxies, headers=headers)
    data = json.loads(r.text)

    dirPath = os.path.join(dataPath, data['title'])

    def makeProjectDir():
        nonlocal dirPath
        while (os.path.exists(dirPath)):
            dirPath = f'{dirPath} - 副本'

    makeProjectDir()
    os.mkdir(dirPath)

    print(f'爬取project: {id}')
    print(f'保存地址: {dirPath}')

    total = len(data['assets'])
    for index, asset in enumerate(data['assets']):
        assetType = asset['asset_type']
        if (assetType == 'image' or assetType == 'cover'):
            crawlImage(
                asset['image_url'],
                os.path.join(dirPath, basename(asset["image_url"]))
            )
            print(f'下载 {asset["image_url"]} 【{index + 1}/{total}】')
        elif (assetType == 'video_clip'):
            tag = pq(asset['player_embedded'])
            r2 = requests.get(tag.attr('src'), proxies=proxies)
            doc = pq(r2.text)
            source = doc('#video > source').attr('src')
            crawlMP4(
                source,
                os.path.join(dirPath, basename(source)),
                session
            )
            print(f'下载 {source} 【{index + 1}/{total}】')
        else:
            print(f'不支持的asset_type: {asset["asset_type"]}')

def crawlArtstationCollection(id, s):
    r = s.get(f'https://www.artstation.com/collections/{id}/projects.json?collection_id={id}', proxies=proxies)
    data = json.loads(r.text)
    for item in data['data']:
        crawlArtstationProject(item['hash_id'], s)

def crawlArtstationProjectByUrl(url):
    urlObj = urlparse(url)
    id = os.path.basename(urlObj.path)
    crawlArtstationProject(id)

argParser = argparse.ArgumentParser()
argParser.add_argument('-p', '--project', default=None)
argParser.add_argument('-c', '--collection', default=None)
args = vars(argParser.parse_args())

s = requests.Session()

if (args['project']):
    crawlArtstationProject(args['project'], s)
if (args['collection']):
    crawlArtstationCollection(args['collection'], s)

s.close()
