import sqlite3
import json
from datetime import datetime


def generateConditionSql(keyword, startTime, endTime, category, significance):
    condition = []
    if keyword != None:
        condition.append("n.content LIKE :keyword")
    if startTime != None and endTime != None:
        condition.append(
            "n.create_time >= :startTime AND n.create_time <= :endTime")
    if category != None and category != 0:
        condition.append(
            "n.id IN (SELECT news_id from news_tag nt WHERE nt.tag_id = :category)")
    if significance != None and significance != 0:
        condition.append("n.significance=:significance")
    conditionStr = f"WHERE {' AND '.join(condition)}" if len(
        condition) > 0 else ""
    # print(keyword, startTime, endTime, category, significance)
    # print(conditionStr)
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

        sql = """
        CREATE TABLE IF NOT EXISTS news_tag (
            news_id INTEGER,
            tag_id INTEGER
        )
        """
        self.conn.execute(sql)

        self.conn.commit()

    def recoverFromJson(self, jsonFile):
        self.clear()
        self.createTable()

        f = open(jsonFile, "r")
        data = json.load(f)
        total = len(data)
        for idx, item in enumerate(data):
            # 新闻
            sina_id = item["id"]
            create_time = int(
                datetime.strptime(item["create_time"],
                                  "%Y-%m-%d %H:%M:%S").timestamp()
                * 1000
            )
            content = item["rich_text"]
            url = item["docurl"]
            significance = 0
            newsId = self.insertNews(
                sina_id, create_time, content, url, significance)

            for d in item["tag"]:
                tagId = self.insertTag(d["name"], d["id"], True)
                self.insertRelation(newsId, tagId)

            print(
                f"insert news: {sina_id} {idx + 1}/{total} {((idx + 1) / total)*100}%"
            )

    def insertNews(self, sina_id, create_time, content, url, significance):
        conn = self.conn
        cursor = conn.cursor()
        sql = """
        INSERT INTO sina_news_7x24
        (sina_id, create_time, content, url, significance)
        VALUES(?, ?, ?, ?, ?)
        """
        cursor.execute(sql, (sina_id, create_time, content, url, significance))
        conn.commit()
        print(f"insert news {sina_id}")
        return cursor.lastrowid

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
            cursor.execute(sql, (name, isSinaTag, sinaId))
            conn.commit()
            return cursor.lastrowid
        else:
            return result[0]

    def insertRelation(self, newsId, tagId):
        sql = """
        INSERT OR IGNORE INTO news_tag (news_id, tag_id) VALUES (?,?)
        """
        self.conn.execute(sql, (newsId, tagId))
        self.conn.commit()

    def insertManyNews(self, list):
        sql = """
        INSERT INTO sina_news_7x24
        (sina_id, create_time, content, url, significance)
        VALUES(?, ?, ?, ?, ?, ?)
        """
        self.conn.executemany(sql, list)
        self.conn.commit()

    def insertManyTags(self, tags):
        sql = """
        INSERT OR IGNORE INTO tag (name, is_sina_tag, sina_id) VALUES (?,?,?)
        """
        self.conn.executemany(sql, tags)
        self.conn.commit()

    def insertManyRelations(self, relations):
        sql = """
        INSERT OR IGNORE INTO news_tag (news_id, tag_id) VALUES (?,?)
        """
        self.conn.executemany(sql, relations)
        self.conn.commit()

    def updateNewsSignificance(self, id, significance):
        cur = self.conn.cursor()
        cur.execute(
            "UPDATE sina_news_7x24 SET significance=? WHERE id=?", (
                significance, id)
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
        SELECT n.id, n.create_time, n.content, n.significance, GROUP_CONCAT(t.id, ',') as tags
        FROM sina_news_7x24 n
        JOIN news_tag nt
        ON n.id = nt.news_id
        JOIN tag t
        ON t.id = nt.tag_id
        {conditionStr}
        GROUP BY n.id
        ORDER BY create_time {'DESC' if sort == 0 else 'ASC'}
        LIMIT :pageSize OFFSET :pageSize*:page
        """

        # print(category, sql)

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
                "category": category,
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

        sql = f"""
            SELECT COUNT(*)
            FROM sina_news_7x24 n
            {conditionStr}
        """

        # print(category, sql)

        cursor.execute(
            sql,
            {
                "keyword": f"%{keyword}%",
                "startTime": startTime,
                "endTime": endTime,
                "significance": significance,
                "category": category,
            },
        )

        result = cursor.fetchone()
        return result[0]

    def clear(self):
        self.conn.execute("DROP TABLE sina_news_7x24")
        self.conn.execute(
            "UPDATE sqlite_sequence SET seq = 0 WHERE name = 'sina_news_7x24'")
        self.conn.execute("DROP TABLE tag")
        self.conn.execute(
            "UPDATE sqlite_sequence SET seq = 0 WHERE name = 'tag'")
        self.conn.execute("DROP TABLE news_tag")
        self.conn.commit()

    def destroy(self):
        self.conn.close()


if __name__ == "__main__":
    db = SinaNews7x24DB()
    db.recoverFromJson("data/sina7x24.json")
    print(db.selectNewsTags())
    print(db.selectNews(10, 100))
    # print(db.newsCount())
