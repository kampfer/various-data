- 开发语言：[python](https://docs.python.org/3/tutorial/classes.html#a-word-about-names-and-objects)
- 应用框架：[fastapi](https://fastapi.tiangolo.com/tutorial/sql-databases/#__tabbed_2_1)
- 服务器：[uvicorn]()
- 数据库：[sqlite](https://www.sqlite.org/index.html)
- 数据库工具包：[sqlalchemy](https://docs.sqlalchemy.org/en/20/orm/quickstart.html)
- 数据检验：[pydantic](https://docs.pydantic.dev/latest/)
- 任务队列工具：[apscheduler](https://apscheduler.readthedocs.io/en/3.x/userguide.html#basic-concepts)


目录结构设计：
backEnd
  - app
    - **
  - main.py

## python的模块化设计是一坨大便

在所有目录外再套一层app目录，这样避免错误`attempted relative import beyond top-level package`
都用绝对引用
