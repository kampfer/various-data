from fastapi import APIRouter


router = APIRouter()


@router.get("/nbs")
def crawlerNBSData(dbcode, zb, sj):
    # fetchStatsData = getattr(import_module("utils"), "fetchStatsData")
    # extractStatsData = getattr(import_module("utils"), "extractStatsData")
    # res = fetchStatsData(dbcode, zb, sj)
    # data = extractStatsData(res)
    # return {"code": 200, "data": data}
    pass
