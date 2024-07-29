from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_upsert
from . import models


def getLatestDocName(db: Session):
    return db.execute(
        select(models.AppState).where(models.AppState.name == "latest_doc")
    ).scalar()


def setLatestDocName(db: Session, docName: str):
    stmt = (
        sqlite_upsert(models.AppState)
        .values(name="lastes_doc", value=docName)
        .on_conflict_do_update(
            index_elements=[models.AppState.name], set_=dict(value=docName)
        )
    )
    db.execute(stmt)
    db.commit()
    return docName


def addRepo(db: Session, time: str, period: str, amount: str, rate: str):
    stmt = (
        sqlite_upsert(models.Repo)
        .values(time=time, period=period, amount=amount, rate=rate)
        .returning(models.Repo)
        .on_conflict_do_nothing()
    )
    result = db.scalars(stmt)
    return result.first()


def addRRP(db: Session, time: str, period: str, amount: str, rate: str):
    stmt = (
        sqlite_upsert(models.RRP)
        .values(time=time, period=period, amount=amount, rate=rate)
        .returning(models.RRP)
        .on_conflict_do_nothing()
    )
    result = db.scalars(stmt)
    return result.first()


def addMLF(db: Session, time: str, period: str, amount: str, rate: str):
    stmt = (
        sqlite_upsert(models.MLF)
        .values(time=time, period=period, amount=amount, rate=rate)
        .returning(models.MLF)
        .on_conflict_do_nothing()
    )
    result = db.scalars(stmt)
    return result.first()


def addTMLF(db: Session, time: str, period: str, amount: str, rate: str):
    stmt = (
        sqlite_upsert(models.TMLF)
        .values(time=time, period=period, amount=amount, rate=rate)
        .returning(models.TMLF)
        .on_conflict_do_nothing()
    )
    result = db.scalars(stmt)
    return result.first()


def addCB(
    db: Session, time: str, name: str, period: str, amount: str, rate: str, price: str
):
    stmt = (
        sqlite_upsert(models.CB)
        .values(
            time=time, name=name, amount=amount, period=period, price=price, rate=rate
        )
        .returning(models.CB)
        .on_conflict_do_nothing()
    )
    result = db.scalars(stmt)
    return result.first()


def addNB(db: Session, time: str, period: str, amount: str, price: str):
    stmt = (
        sqlite_upsert(models.NB)
        .values(time=time, period=period, amount=amount, price=price)
        .returning(models.NB)
        .on_conflict_do_nothing()
    )
    result = db.scalars(stmt)
    return result.first()
