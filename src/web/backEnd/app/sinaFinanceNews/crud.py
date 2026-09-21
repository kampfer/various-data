from sqlalchemy.orm import Session
from sqlalchemy import exists, select
from . import models, schemas


def getNews(db: Session, skip: int = 0, limit: int = 100):
    """分页查询新闻列表。"""
    return db.query(models.SFNews).offset(skip).limit(limit).all()


def addNews(db: Session, news: schemas.SFNews):
    """
    新增单条新闻，并关联其标签。

    关键点：必须先 db.add(mNews) 再加入 tag 关联。
    否则 addTag 内部的 flush/commit 触发 autoflush 时，
    SQLAlchemy 会发现 mNews 不在 session 中，
    从而报 "SFTag.news won't proceed" 警告并静默丢弃关联。
    """
    mNews = models.SFNews(
        sina_id=news.sina_id,
        create_time=news.create_time,
        content=news.content,
        url=news.url,
        significance=news.significance,
    )

    # 先把新闻对象放入 session，使其处于 pending 状态。
    # 这样后续对 mNews.tags 的关联操作才会被 flush 正常处理。
    db.add(mNews)

    if hasattr(news, "tags"):
        for tag in news.tags:
            # addTag 内部使用 flush 而非 commit，
            # 因此这里不会触发事务提交，也不会让 mTag 过期。
            mTag = addTag(db, tag)
            mNews.tags.append(mTag)

    # 统一提交一次事务；前面的所有 add/append 在此一并落库。
    db.commit()
    db.refresh(mNews)  # 取回数据库生成的字段（如自增 id）
    return mNews


def addManyNews(db: Session, news: list[schemas.SFNews]):
    """
    批量新增新闻。

    与 addNews 同理，每个 mNews 在循环内就 db.add，
    而不是等循环结束后 add_all，否则循环中 addTag 的 flush
    会因为 mNews 不在 session 中而报同样的警告。

    另外把 commit 收到循环外只做一次，保证：
      1. 整个批量操作是一个原子事务，出错可整体回滚；
      2. 避免 N 次 commit 带来的性能损耗。
    """
    mNewsAdded = []

    for sNews in news:
        mNews = models.SFNews(
            sina_id=sNews.sina_id,
            create_time=sNews.create_time,
            content=sNews.content,
            url=sNews.url,
            significance=sNews.significance,
        )

        # 每个对象先加入 session，再做 tag 关联
        db.add(mNews)

        if hasattr(sNews, "tags"):
            for sTag in sNews.tags:
                mTag = addTag(db, sTag)
                mNews.tags.append(mTag)

        # 用 append 保持与输入相同的顺序；
        # 原代码用 insert(0, ...) 会导致返回列表逆序。
        mNewsAdded.append(mNews)

    # 循环外统一提交，一个事务搞定全部新闻
    db.commit()
    return mNewsAdded


def existsTag(db: Session, name: str):
    """判断指定名称的标签是否已存在，返回布尔值。"""
    # 注释掉的写法是 query 版本；execute + select 是 2.0 推荐写法
    # result = db.query(exists().where(models.SFTag.name == name))
    result = db.execute(select(exists().where(models.SFTag.name == name)))
    return result.scalar()


def getTags(db: Session):
    """返回标签查询对象（注意：这里返回的是 Query，未执行，调用方自行处理）。"""
    return db.query(models.SFTag)


def addTag(db: Session, tag: schemas.SFTag):
    """
    按名称查找标签，不存在则创建，返回 ORM 对象。

    改动点：把原来的 db.commit() 改为 db.flush()。
    理由：
      1. flush 会分配主键并把对象写入当前事务，但不提交；
         事务边界交由最外层调用方（addNews/addManyNews）控制。
      2. 原 commit 会在批量场景下被调用 N 次，既慢又破坏原子性；
         而且 commit 默认 expire_on_commit=True 会让 mTag 过期，
         后续访问其属性会触发额外 SELECT。
    """
    stmt = select(models.SFTag).where(models.SFTag.name == tag.name)
    mTag = db.scalar(stmt)

    if not mTag:
        mTag = models.SFTag(
            name=tag.name,
            is_sina_tag=tag.is_sina_tag,
            sina_id=tag.sina_id,
        )
        db.add(mTag)
        db.flush()  # 分配主键，但不提交事务

    return mTag


def toggleNewsSignificance():
    """占位函数，待实现。"""
    pass