from sqlalchemy.orm import Session
from sqlalchemy import select, update
from . import models


def getLatestDocName(db: Session):
    return db.execute(
        select(models.AppState).where(models.AppState.name == "latest_doc")
    ).scalar()


def setLatestDocName(db: Session, name: str):
    stmt = (
        update(models.AppState)
        .where(models.AppState.name == "latest_doc")
        .values(value=name)
    )
    db.execute(stmt)
    db.commit()
    return name


def addRepo(db: Session, time: str, period: str, amount: str, rate: str):
    repo = models.Repo(time=time, period=period, amount=amount, rate=rate)
    db.add(repo)
    db.commit()
    return repo


def addRRP(db: Session, time: str, period: str, amount: str, rate: str):
    rrp = models.RRP(time=time, period=period, amount=amount, rate=rate)
    db.add(rrp)
    db.commit()
    return rrp


def addMLF(db: Session, time: str, period: str, amount: str, rate: str):
    mlf = models.MLF(time=time, period=period, amount=amount, rate=rate)
    db.add(mlf)
    db.commit()
    return mlf


def addTMLF(db: Session, time: str, period: str, amount: str, rate: str):
    tmlf = models.TMLF(time=time, period=period, amount=amount, rate=rate)
    db.add(tmlf)
    db.commit()
    return tmlf


def addCB(
    db: Session, time: str, name: str, period: str, amount: str, rate: str, price: str
):
    cb = models.CB(
        time=time, name=name, amount=amount, period=period, price=price, rate=rate
    )
    db.add(cb)
    db.commit()
    return cb


def addNB(db: Session, time: str, period: str, amount: str, price: str):
    nb = models.NB(time=time, period=period, amount=amount, price=price)
    db.add(nb)
    db.commit()
    return nb
