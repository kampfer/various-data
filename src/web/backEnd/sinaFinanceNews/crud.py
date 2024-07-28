from sqlalchemy.orm import Session
from sqlalchemy import exists, select
from . import models, schemas


def getNews(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.SFNews).offset(skip).limit(limit).all()


def addNews(db: Session, news: schemas.SFNews):
    mNews = models.SFNews(
        sina_id=news.sina_id,
        create_time=news.create_time,
        content=news.content,
        url=news.url,
        significance=news.significance,
    )
    if hasattr(news, "tags"):
        for tag in news.tags:
            mTag = addTag(db, tag)
            mNews.tags.append(mTag)
    db.add(mNews)
    db.commit()
    db.refresh(mNews)
    return mNews


def addManyNews(db: Session, news: list[schemas.SFNews]):
    mNewsAdded = []
    for sNews in news:
        mNews = models.SFNews(
            sina_id=sNews.sina_id,
            create_time=sNews.create_time,
            content=sNews.content,
            url=sNews.url,
            significance=sNews.significance,
        )
        if hasattr(sNews, "tags"):
            for sTag in sNews.tags:
                mTag = addTag(db, sTag)
                mNews.tags.append(mTag)
        mNewsAdded.insert(0, mNews)
    db.add_all(mNewsAdded)
    db.commit()


def existsTag(db: Session, name: str):
    # result = db.query(exists().where(models.SFTag.name == name))
    result = db.execute(select(exists().where(models.SFTag.name == name)))
    return result.scalar()


def getTags(db: Session):
    return db.query(models.SFTag)


def addTag(db: Session, tag: schemas.SFTag):
    stmt = select(models.SFTag).where(models.SFTag.name == tag.name)
    mTag = db.scalar(stmt)
    if not mTag:
        mTag = models.SFTag(
            name=tag.name, is_sina_tag=tag.is_sina_tag, sina_id=tag.sina_id
        )
        db.add(mTag)
        db.commit()
    return mTag


def toggleNewsSignificance():
    pass
