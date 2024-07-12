from fastapi import APIRouter

router = APIRouter(prefix="/sinaFinanceNews", tags=["sinaFinanceNews"])


@router.get("/news")
def getAllnews():
    pass
