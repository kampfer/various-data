from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class SFTag(BaseModel):
    name: str
    is_sina_tag: bool
    sina_id: str

    # https://fastapi.tiangolo.com/tutorial/sql-databases/#use-pydantics-orm_mode
    class Config:
        from_attributes = True


class SFNews(BaseModel):
    sina_id: int
    create_time: int
    content: str
    url: str
    significance: Optional[int] = 0
    tags: Optional[list[SFTag]]

    class Config:
        from_attributes = True
