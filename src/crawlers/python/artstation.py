from turtle import fd
import requests
import json
import os
from urllib.parse import urlparse
from pyquery import PyQuery as pq

dataPath = 'D:\\模型素材\\artstation'

proxies = {
    'http': 'http://127.0.0.1:41091',
    'https': 'http://127.0.0.1:41091'
}

def basename(url):
    urlObj = urlparse(url)
    return os.path.basename(urlObj.path)

def crawlImage(url, savePath):
    r = requests.get(url, proxies=proxies)
    with open(savePath, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=128):
            fd.write(chunk)

def crawlMP4(url, savePath):
    headers = {
        'Range': 'bytes=0-'
    }
    r = requests.get(url, proxies=proxies, stream=True, headers=headers)
    print(r.status_code)
    with open(savePath, 'wb') as fd:
        for chunk in r.iter_content(chunk_size=1024):
            fd.write(chunk)

def crawlArtstationProject(id):
    r = requests.get(f'https://www.artstation.com/projects/{id}.json', proxies=proxies)
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
                os.path.join(dirPath, basename(source))
            )
            print(f'下载 {source} 【{index + 1}/{total}】')
        else:
            print(f'不支持的asset_type: {asset["asset_type"]}')

def crawlArtstationProjectByUrl(url):
    urlObj = urlparse(url)
    id = os.path.basename(urlObj.path)
    crawlArtstationProject(id)

crawlArtstationProjectByUrl('https://www.artstation.com/artwork/035X6y')
# print(requests.get('https://www.artstation.com/users/user-245566/likes.json?page=1', proxies=proxies).text)
