import json

from fastapi import APIRouter
import akshare as ak

router = APIRouter()

@router.get("/akshare")
def callAkshare(funcName, args):
    print(funcName, args)
    func = getattr(ak, funcName)
    if args:
        params = json.loads(args)
    else:
        params = {}
    df = func(**params)
    return {"code": 200, "data": json.loads(df.to_json(orient="records"))}