"""投资交易账本（investment-trade-ledger）后端模块包。

包内文件职责沿用 ``sinaFinanceNews`` 模块惯例：

- ``constants.py``：领域枚举英文码与边界常量（本文件所在层次不含任何中文展示文案）；
- ``types.py``：``DecimalText`` 自定义列类型，保证 SQLite 上金额的精确存取；
- ``models.py``：``Transaction`` / ``Valuation`` 表模型；
- ``schemas.py``：Pydantic v2 请求与响应契约；
- ``crud.py`` / ``calculators.py`` / ``service.py`` / ``exceptions.py`` / ``router.py``：
  数据访问、纯计算、用例编排、异常体系与 HTTP 路由。
"""
