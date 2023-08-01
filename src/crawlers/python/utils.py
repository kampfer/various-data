import requests
import json
import os
from constants import DATA_PATH, STATS_GOV_CRT_PATH

def makeStatsNode(d):
  return {
    'value': d['data']['data'],
    'date': d['wds'][1]['valuecode']
  }

def fetchStatsData(dbcode, zb, sj):
  r = requests.get(
    'https://data.stats.gov.cn/easyquery.htm',
    params={
      'm': 'QueryData',
      'rowcode': 'zb',
      'colcode': 'sj',
      'wds': '[]',
      'dbcode': dbcode,
      'dfwds': json.dumps([
        {
          'wdcode': 'zb',
          'valuecode': zb,
        },
        {
          'wdcode': 'sj',
          'valuecode': sj
        }
      ])
    },
    verify=STATS_GOV_CRT_PATH
  )
  return json.loads(r.text)

def extractStatsData(res):
  allList = list(map(makeStatsNode, res['returndata']['datanodes']))
  columnCount = len(res['returndata']['wdnodes'][1]['nodes'])
  data = {}
  for rowIndex, row in enumerate(res['returndata']['wdnodes'][0]['nodes']):
    rowList = []
    for i in range(columnCount):
      rowList.append(allList[columnCount * rowIndex + i])
    data[row['cname']] = rowList
  return data

def saveData(storePath, data):
  f = open(storePath, 'w')
  f.write(json.dumps(data))
  f.close()

def readData(storePath):
  f = open(storePath, 'r')
  data = json.load(f)
  f.close()
  return data

def crawlStatsData(dbcode, zb, sj, saveName):
  res = fetchStatsData(dbcode, zb, sj)
  data = extractStatsData(res)
  saveData(os.path.join(DATA_PATH, f'{saveName}.json'), data)