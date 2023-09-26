import sqlite3
import json
from datetime import datetime


def generateConditionSql(keyword, startTime, endTime, category, significance):
    print(keyword, startTime, endTime, category, significance)
    condition = []
    if keyword != None:
        condition.append("content LIKE :keyword")
    if startTime != None and endTime != None:
        condition.append("create_time >= :startTime AND create_time <= :endTime")
    if category != None and category != 0:
        condition.append("tags LIKE :category")
    if significance != None and significance != 0:
        condition.append("significance=:significance")
    conditionStr = f"WHERE {' AND '.join(condition)}" if len(condition) > 0 else ""
    print(conditionStr)
    return conditionStr


class SinaNews7x24DB:
    def __init__(self, dbFile="data/sina_news_7x24.db"):
        self.conn = sqlite3.connect(dbFile)
        self.createTable()

    def createTable(self):
        sql = """
    CREATE TABLE IF NOT EXISTS sina_news_7x24 (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sina_id INTEGER,
      create_time INTEGER,
      content TEXT,
      url TEXT,
      tags TEXT,
      significance INTEGER
    );
    """
        self.conn.execute(sql)
        sql = """
    CREATE TABLE IF NOT EXISTS tag (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT,
      is_sina_tag BOOLEAN,
      sina_id TEXT
    )
    """
        self.conn.execute(sql)
        self.conn.commit()

    def recoverFromJson(self, jsonFile):
        self.clear()
        self.createTable()

        f = open(jsonFile, "r")
        data = json.load(f)
        rows = []
        for item in data:
            tags = []
            for d in item["tag"]:
                tagId = self.insertTag(d["name"], d["id"], True)
                tags.append(tagId)

            # 新闻
            sina_id = item["id"]
            create_time = int(
                datetime.strptime(item["create_time"], "%Y-%m-%d %H:%M:%S").timestamp()
                * 1000
            )
            content = item["rich_text"]
            url = item["docurl"]
            newsTags = ",".join(map(str, tags))
            significance = 0
            rows.append((sina_id, create_time, content, url, newsTags, significance))

        self.insertMultipleNews(rows)

    # 创建tag并返回id
    def insertTag(self, name, sinaId, isSinaTag=False):
        conn = self.conn
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tag WHERE name=?", (name,))
        result = cursor.fetchone()

        if result is None:
            sql = """
        INSERT OR IGNORE INTO tag (name, is_sina_tag, sina_id) VALUES (?,?,?)
      """
            cursor.execute(sql, (name, sinaId, isSinaTag))
            conn.commit()
            return cursor.lastrowid
        else:
            return result[0]

    def insertMultipleNews(self, list):
        sql = """
      INSERT INTO sina_news_7x24
      (sina_id, create_time, content, url, tags, significance)
      VALUES(?, ?, ?, ?, ?, ?)
    """
        self.conn.executemany(sql, list)
        self.conn.commit()

    def updateNewsSignificance(self, id, significance):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE sina_news_7x24 SET significance=? WHERE id=?", (significance, id)
        )
        self.conn.commit()

    def updateNewsTags(self, id, tags):
        cur = self.conn.cursor()
        cur.execute("UPDATE sina_news_7x24 SET tags=? WHERE id=?", (tags, id))
        self.conn.commit()

    def selectNews(
        self,
        page=0,
        pageSize=20,
        keyword=None,
        sort=0,
        significance=None,
        startTime=None,
        endTime=None,
        category=None,
    ):
        conditionStr = generateConditionSql(
            keyword, startTime, endTime, category, significance
        )

        sql = f"""
            SELECT * FROM sina_news_7x24
            {conditionStr}
            ORDER BY create_time {'DESC' if sort == 0 else 'ASC'}
            LIMIT :pageSize OFFSET :pageSize*:page
        """

        cursor = self.conn.execute(
            sql,
            {
                # 占位符只能用于替换值，而排序的DESC和ASC关键字不能用占位符
                "keyword": f"%{keyword}%",
                "startTime": startTime,
                "endTime": endTime,
                "significance": significance,
                "page": page,
                "pageSize": pageSize,
                "category": f"%{category}%",
            },
        )
        return cursor.fetchall()

    def selectNewsTags(self):
        cur = self.conn.cursor()
        cur.execute("SELECT * FROM tag")
        return cur.fetchall()

    def newsCount(
        self,
        keyword=None,
        startTime=None,
        endTime=None,
        category=None,
        significance=None,
    ):
        conn = self.conn
        cursor = conn.cursor()

        conditionStr = generateConditionSql(
            keyword, startTime, endTime, category, significance
        )
        cursor.execute(
            f"SELECT COUNT(*) FROM sina_news_7x24 {conditionStr}",
            {
                "keyword": f"%{keyword}%",
                "startTime": startTime,
                "endTime": endTime,
                "significance": significance,
                "category": f"%{category}%",
            },
        )

        result = cursor.fetchone()
        return result[0]

    def clear(self):
        self.conn.execute("DROP TABLE sina_news_7x24")
        self.conn.execute(
            "UPDATE sqlite_sequence SET seq = 0 WHERE name = 'sina_news_7x24'"
        )
        self.conn.execute("DROP TABLE tag")
        self.conn.execute("UPDATE sqlite_sequence SET seq = 0 WHERE name = 'tag'")
        self.conn.commit()

    def destroy(self):
        self.conn.close()


# if __name__ == "__main__":
#   db = SinaNews7x24DB()
#   db.recoverFromJson('data/sina7x24.json')
#   print(db.selectNewsTags())
#   print(db.selectNews(10, 100))
#   # print(db.newsCount())
