import requests
import json
import os
from constants import DATA_PATH, STATS_GOV_CRT_PATH

def makeNode(d):
  return {
    'gdp': d['data']['data'],
    'date': d['wds'][1]['valuecode']
  }

storePath = os.path.join(DATA_PATH, 'gdp.json')

# https://data.stats.gov.cn/easyquery.htm?cn=B01&zb=A0101&sj=2022C
r = requests.get(
  'https://data.stats.gov.cn/easyquery.htm',
  params={
    'm': 'QueryData',
    'dbcode': 'hgjd',
    'rowcode': 'zb',
    'colcode': 'sj',
    'wds': '[]',
    'dfwds': json.dumps([{
      'wdcode': 'zb',
      'valuecode': 'A0101'
    }, {
      'wdcode': 'sj',
      'valuecode': '1990-'
    }])
  },
  verify=STATS_GOV_CRT_PATH
)
res = json.loads(r.text)
allData = list(map(makeNode, res['returndata']['datanodes']))
columnCount = len(res['returndata']['wdnodes'][1]['nodes'])
data = {}
for rowIndex, row in enumerate(res['returndata']['wdnodes'][0]['nodes']):
  rowList = []
  for i in range(columnCount):
    rowList.append(allData[columnCount * rowIndex + i])
  data[row['cname']] = rowList
f = open(storePath, 'w')
f.write(json.dumps(data))
f.close()

# pipenv run python src/crawlers/python/gdp.py
