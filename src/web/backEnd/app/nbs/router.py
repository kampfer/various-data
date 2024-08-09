import json

from fastapi import APIRouter
import requests


def fetchStatsData(dbcode, zb=None, sj=None):
    args = []
    if zb:
        args.append({"wdcode": "zb", "valuecode": zb})
    if sj:
        args.append({"wdcode": "sj", "valuecode": sj})

    r = requests.get(
        "https://data.stats.gov.cn/easyquery.htm",
        params={
            "m": "QueryData",
            "rowcode": "zb",
            "colcode": "sj",
            "wds": "[]",
            "dbcode": dbcode,
            "dfwds": json.dumps(args),
        },
        # verify=STATS_GOV_CRT_PATH,
    )

    return json.loads(r.text)


def makeStatsNode(d):
    return {"value": d["data"]["data"], "date": d["wds"][1]["valuecode"]}


def extractStatsData(res):
    allList = list(map(makeStatsNode, res["returndata"]["datanodes"]))
    columnCount = len(res["returndata"]["wdnodes"][1]["nodes"])
    data = {}
    for rowIndex, row in enumerate(res["returndata"]["wdnodes"][0]["nodes"]):
        rowList = []
        for i in range(columnCount):
            rowList.append(allList[columnCount * rowIndex + i])
        data[row["cname"]] = rowList
    return data


router = APIRouter()


@router.get("/nbs")
def crawlerNBSData(dbcode, zb=None, sj=None):
    res = fetchStatsData(dbcode, zb, sj)
    data = extractStatsData(res)
    return data
