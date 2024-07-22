from sqlalchemy.orm import Session
from . import models, schemas


def getNews(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.SFNews).offset(skip).limit(limit).all()


def addNews(db: Session, news: schemas.SFNews):
    SFNews = models.SFNews(
        sina_id=news.sina_id,
        create_time=news.create_time,
        content=news.content,
        url=news.url,
        significance=news.significance
    )
    db.add(SFNews)
    db.commit()
    db.refresh(SFNews)
    return SFNews
