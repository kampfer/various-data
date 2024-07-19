from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from backEnd.database import Base

class SFNews(Base):
    __tablename__  = "sf_news"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sina_id = Column(Integer)
    create_time = Column(Integer)
    content = Column(String)
    url = Column(String)
    significance = Column(Integer)
    tags = relationship("SFTag")


class SFTag(Base):
    __tablename__  = "sf_tag"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String)
    is_sina_tag = Column(Boolean)
    sina_id = Column(String)
