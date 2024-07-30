# from __future__ import annotations
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass


class AppState(Base):
    __tablename__ = "app_state"
    name: Mapped[str] = mapped_column(primary_key=True)
    value: Mapped[str]


# 正回购
class Repo(Base):
    __tablename__ = "omo_repo"
    time: Mapped[str] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(primary_key=True)
    amount: Mapped[str]
    rate: Mapped[str]


# 逆回购
class RRP(Base):
    __tablename__ = "omo_rrp"
    time: Mapped[str] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(primary_key=True)
    amount: Mapped[str]
    rate: Mapped[str]


class MLF(Base):
    __tablename__ = "omo_mlf"
    time: Mapped[str] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(primary_key=True)
    amount: Mapped[str]
    rate: Mapped[str]


# 定向MLF
class TMLF(Base):
    __tablename__ = "omo_tmlf"
    time: Mapped[str] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(primary_key=True)
    amount: Mapped[str]
    rate: Mapped[str]


# 国债
class NB(Base):
    __tablename__ = "omo_nb"
    time: Mapped[str] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(primary_key=True)
    amount: Mapped[str]
    price: Mapped[str]


# 央行票据
class CB(Base):
    __tablename__ = "omo_cb"
    time: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(primary_key=True)
    amount: Mapped[str]
    period: Mapped[str]
    price: Mapped[Optional[str]]
    rate: Mapped[str]
