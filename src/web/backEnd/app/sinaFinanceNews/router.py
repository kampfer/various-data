from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from . import crud, schemas
import app.dependencies as dependencies

get_db = dependencies.get_db

router = APIRouter(prefix="/sinaFinanceNews", tags=["sinaFinanceNews"])


@router.get("/news", response_model=list[schemas.SFNews])
def getNews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    # 修复：补 return，且函数名与 crud 一致（getNews）
    return crud.getNews(db, skip, limit)


@router.post("/addNews", response_model=schemas.SFNews)
def addNews(news: schemas.SFNews, db: Session = Depends(get_db)):
    # crud.addNews 是最外层入口，内部已 commit，这里无需再提交
    return crud.addNews(db=db, news=news)


@router.get("/tags", response_model=list[schemas.SFTag])
def getTags(db: Session = Depends(get_db)):
    # crud.getTags 已补 .all()，只读，无需提交
    return crud.getTags(db=db)


@router.post("/addTag", response_model=schemas.SFTag)
def addTag(tag: schemas.SFTag, db: Session = Depends(get_db)):
    # crud.addTag 只 flush，不 commit；
    # 这条路由是独立最外层入口，必须自己 commit
    mTag = crud.addTag(db=db, tag=tag)
    db.commit()
    db.refresh(mTag)
    return mTag