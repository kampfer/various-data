from sqlalchemy import Column, Integer, String, Boolean

class SinaFinanceNews:
  __name__ = 'sina_finance_news'

  id = Column(Integer, primary_key=True, autoincrement=True)
  sina_id = Column(Integer)
  create_time = Column(Integer)
  content = Column(String)
  url = Column(String)
  significance = Column(Integer)


class SinaFinanceTag:
  __name__ = 'sina_finance_tag'

  id = Column(Integer, primary_key=True, autoincrement=True)
  name = Column(String)
  is_sina_tag = Column(Boolean)
  sina_id = Column(String)


class SinaFinanceNewsAndTag:
  __name__ = 'sina_finance_news_to_tag'
