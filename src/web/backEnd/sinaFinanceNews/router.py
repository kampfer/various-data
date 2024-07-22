from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from . import crud, schemas
from backEnd.dependencies import get_db

router = APIRouter(prefix="/sinaFinanceNews", tags=["sinaFinanceNews"])


@router.get("/news", response_model=list[schemas.SFNews])
def getNews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    news = crud.get_news(db, skip, limit)


@router.post("/add", response_model=schemas.SFNews)
def addNews(news: schemas.SFNews, db: Session = Depends(get_db)):
    return crud.addNews(db=db, news=news)