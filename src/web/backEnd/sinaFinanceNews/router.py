from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from . import crud, schemas
from backEnd.dependencies import get_db

router = APIRouter(prefix="/sinaFinanceNews", tags=["sinaFinanceNews"])


@router.get("/news", response_model=list[schemas.SFNews])
def getNews(kip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    news = crud.get_news()
