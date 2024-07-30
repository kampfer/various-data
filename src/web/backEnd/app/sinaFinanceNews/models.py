from __future__ import annotations
from typing import List
from typing import Annotated
from typing import Optional

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import relationship
from sqlalchemy import Column
from sqlalchemy import Table
from sqlalchemy import ForeignKey

# make use of pep-593 Annotated to package common directives into types
# https://docs.sqlalchemy.org/en/20/changelog/whatsnew_20.html#step-five-make-use-of-pep-593-annotated-to-package-common-directives-into-types
primaryKey = Annotated[int, mapped_column(primary_key=True, autoincrement=True)]


class Base(DeclarativeBase):
    pass


# 双向
# https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#setting-bi-directional-many-to-many
association_table = Table(
    "sf_news_tag",
    Base.metadata,
    Column("left_id", ForeignKey("sf_news.id"), primary_key=True),
    Column("right_id", ForeignKey("sf_tag.id"), primary_key=True),
)


class SFNews(Base):
    __tablename__ = "sf_news"

    id: Mapped[primaryKey]
    sina_id: Mapped[int]
    create_time: Mapped[int]
    content: Mapped[str]
    url: Mapped[str]
    significance: Mapped[int]
    tags: Mapped[Optional[List[SFTag]]] = relationship(
        secondary=association_table, back_populates="news"
    )  # PEP 484 annotations 从左侧推断类型 是最新的写法


class SFTag(Base):
    __tablename__ = "sf_tag"

    id: Mapped[primaryKey]
    name: Mapped[str]
    is_sina_tag: Mapped[bool]
    sina_id: Mapped[str]
    news: Mapped[Optional[List[SFNews]]] = relationship(
        secondary=association_table, back_populates="tags"
    )
