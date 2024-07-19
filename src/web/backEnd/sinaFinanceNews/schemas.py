from pydantic import BaseModel


class SFTag(BaseModel):
    id: int
    name: str
    is_sina_tag: bool
    sina_id: str


class SFNews(BaseModel):
    id: int
    sina_id: int
    create_time: int
    content: str
    url: str
    significance: int
    tags: list[SFTag]
