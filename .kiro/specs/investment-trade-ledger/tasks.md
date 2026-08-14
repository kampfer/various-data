# Implementation Plan: 投资交易账本（投资交易账本实施计划）

## Overview

（概述）

按「后端自下而上、前端自内而外、最后装配」的顺序增量实现：

- **后端**（Python / FastAPI，位于 `src/web/backEnd/app/investmentLedger/`）：常量与列类型 → 表模型 → Pydantic 契约与异常 → 纯计算层 → 数据访问层 → 服务层 → 路由层 → 三处装配点追加注册。
- **前端**（TypeScript / React，位于 `src/web/frontEnd/src/`）：工具链接入（tsconfig / webpack / vitest） → 纯领域层 → 通信层 → RTK 状态层 → 展示组件 → 页面容器与路由注册。
- 属性测试严格按设计文档「Correctness Properties」的 11 条属性实现，**每条属性恰好一个属性测试**：Property 1、2、7、10 落在前端领域层（`vitest` + `fast-check`），Property 3、4、5、6、8、9、11 落在后端（`pytest` + `hypothesis`）。
- 全程遵循既有惯例：后端沿用 `sinaFinanceNews` 模块的文件职责划分与 camelCase 函数命名；前端样式一律写入 `*.module.scss`，不使用行内样式；枚举值全链路使用英文码，中文仅出现在前端展示映射层。

## Tasks

- [x] 1. 后端模块骨架、常量与持久化模型
  - [x] 1.1 创建 investmentLedger 包骨架与领域常量
    - 新建 `src/web/backEnd/app/investmentLedger/__init__.py`
    - 新建 `constants.py`：`ProductType`（WEALTH/FUND/STOCK）、`TradeDirection`（BUY/SELL）两个 `str, Enum`，以及 `DEFAULT_PAGE_SIZE`、`MIN_PAGE_SIZE`、`MAX_PAGE_SIZE`、`PAGE_SIZE_OPTIONS`、`MAX_PRODUCT_NAME_LENGTH`、`MAX_PRODUCT_CODE_LENGTH`、`MAX_SEARCH_VALUE_LENGTH`、`ANNUALIZATION_DAYS`、`MAX_VALUATION_UNIT_PRICE`
    - 在 `Pipfile` 的 `[dev-packages]` 以固定版本加入 `pytest`、`hypothesis`；新建后端测试目录与 `conftest.py`（临时 SQLite 文件夹具，禁止连接 `various_data.db` / `various_data_dev.db`）
    - 每个枚举成员、常量均带中文注释说明含义与所对应的需求条目
    - _Requirements: 1.1, 2.24, 2.25, 3.2_

  - [x] 1.2 实现 DecimalText 自定义列类型
    - 新建 `types.py`：`DecimalText(TypeDecorator)`，`impl = String`、`cache_ok = True`
    - `process_bind_param` 将 `Decimal` 量化为两位小数字符串写入，`process_result_value` 读回为 `Decimal`，全程不经过 `float`，`None` 透传
    - _Requirements: 1.2, 3.2_

  - [x] 1.3 实现交易与估值表模型并注册建表
    - 新建 `models.py`：模块内 `Base(DeclarativeBase)`、`primaryKey` 注解、`Transaction`（`il_transaction`，含 `ix_il_transaction_product` 复合索引与 `product_type` / `product_code` / `direction` / `trade_date` 索引）、`Valuation`（`il_valuation`，含 `uq_il_valuation_product_date` 唯一约束）
    - 金额列使用 `DecimalText(20)`，日期列使用 `Date`，时间列使用 `DateTime`
    - 在 `app/models.py` 的 `initAppModels()` 中追加 `from app.investmentLedger.models import Base as LedgerBase` 与 `LedgerBase.metadata.create_all(bind=engine)`，不改动既有逻辑
    - _Requirements: 1.4, 2.5, 2.10, 2.15, 2.16, 3.3_

  - [x]* 1.4 编写模型与列类型的单元测试
    - 断言 `DecimalText` 往返保真（两位小数、上限值 999999999.99、`None`）
    - 断言 `Valuation` 三列唯一约束在临时 SQLite 上真实生效
    - _Requirements: 3.2, 3.3_

- [x] 2. Pydantic 契约与统一错误处理
  - [x] 2.1 实现 schemas.py 请求与响应模型
    - `ApiResponse[T]`、`FieldErrorItem`、`Metric`、`TransactionCreate`、`TransactionOut`、`TransactionQuery`、`HoldingQuery`、`HoldingOut`、`PageOut[T]`、`PortfolioStatisticsOut`、`ValuationUpsert`、`ValuationOut`、`InitialModuleOut`
    - 统一 `model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)`；金额与比率一律序列化为十进制字符串
    - 字段校验器：产品名称 1..100、产品代码 1..32、交易单价 > 0 且小数位恰为 2、数量为 > 0 整数、估值单价 0..999999999.99 且小数位 ≤ 2、`start_date` / `end_date` 必须成对且 `start <= end`、搜索值 1..100、`page >= 1`、`page_size` 闭区间 1..100
    - `Metric` 在 `available=False` 时 `value` 必为 `None` 并给出中文 `unavailable_reason`
    - _Requirements: 1.1, 1.2, 2.6, 2.12, 2.16, 2.17, 2.18, 2.20, 2.21, 2.24, 2.25, 3.1, 3.2, 3.9_

  - [x]* 2.2 编写 schemas 校验的示例单元测试
    - 覆盖枚举非法值（中文字面量、小写码）、长度边界（0/1/100/101、32/33）、单价小数位 1/2/3 位、非法日历日期（2 月 30 日）、`start > end`、页大小 0/1/100/101
    - 断言无效输入产生的错误项能定位到具体字段
    - _Requirements: 1.2, 2.20, 2.21, 2.26, 3.2_

  - [x] 2.3 实现异常体系与全局处理器
    - 新建 `exceptions.py`：`LedgerError` 基类与 `LedgerValidationError`、`TransactionNotFound`、`PageOutOfRange`、`InvalidPageSize`、`InvalidDateRange`、`InvalidSearchValue`
    - `registerLedgerExceptionHandlers(app)`：`LedgerError` → 统一 `{code,msg,data}` 信封；`RequestValidationError` → 翻译为 camelCase `fieldErrors`（`code` 用 `NOT_IN_ENUM` / `INVALID_SCALE` / `OUT_OF_RANGE` / `TOO_LONG`，`message` 为完整中文句子）；`IntegrityError` / `OperationalError` → `code: 500` 且不外泄 SQL 与堆栈
    - 在 `main.py` 追加 `registerLedgerExceptionHandlers(app)` 一行
    - `PageOutOfRange` 的 `msg` 包含「有效页码为 1 至 N」
    - _Requirements: 1.2, 1.5, 2.20, 2.21, 2.26, 2.30, 3.2_

  - [x]* 2.4 编写异常处理器单元测试
    - 断言各异常映射到正确的 HTTP 状态码、业务 `code` 与中文 `msg`
    - 断言枚举非法时不把英文码原样回显给用户，且响应中不含 SQL、表名与堆栈
    - _Requirements: 1.2, 2.30, 3.2_

- [x] 3. 计算层（纯 Decimal，无 I/O）
  - [x] 3.1 实现 Paginator 分页切片器
    - 新建 `calculators.py` 并实现 `Paginator.slice(items, page, pageSize) -> (切片, pageCount)`
    - `pageCount = ceil(len(items) / pageSize)`，空集为 0；`pageCount > 0 且 page > pageCount` 抛 `PageOutOfRange`
    - _Requirements: 2.11, 2.24, 2.25, 2.28, 2.29, 2.30, 2.31_

  - [x]* 3.2 为分页划分编写属性测试
    - **Property 6: 分页是结果集无重复、无遗漏的有序划分**
    - **Validates: Requirements 2.11, 2.25, 2.28, 2.29, 2.31**
    - 生成器需偏置 `total = 0`、`total < pageSize`、整除与非整除、`pageSize = 1` 与 `pageSize = 100`

  - [x] 3.3 实现 ProductPerformanceCalculator 产品业绩计算器
    - `calculate(txns, latestValuation) -> ProductPerformance`：持仓数量、持仓市值、累计买入/卖出金额、总收益、总收益率、年化收益率
    - 年化以 `Decimal` 的 `ln` / `exp` 实现 `(1 + r)^(365 / 持有天数) - 1`，精度 28 位；`1 + r == 0` 时结果取 `-1`
    - 任一指标不满足定义域时 `available=False`、`value=None` 并给出中文原因（缺少最新估值 / 累计买入金额为 0 / 持有天数不足），绝不以 0 代替，且不影响同次计算的其它指标
    - _Requirements: 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_

  - [x]* 3.4 为产品统计编写属性测试
    - **Property 8: 产品统计精确计算并显式标记不可用指标**
    - **Validates: Requirements 3.4, 3.5, 3.6, 3.7, 3.8, 3.9**
    - 采用参考实现对比（直白循环求和作为模型），期望值以 `Decimal` 断言，禁止 `float`；偏置全买入、全卖出、买卖抵平、收益率恰为 -1、持有天数 1 天与数千天

  - [x] 3.5 实现 PortfolioCalculator 组合聚合计算器
    - `aggregate(performances) -> PortfolioStatistics`：仅聚合具有最新估值的产品；总持仓、总收益为求和；总收益率 = 总收益 ÷ Σ累计买入金额（Σ > 0 时可用）；总年化 = Σ(年化 × 累计买入) ÷ Σ累计买入（集合非空且每个产品均有年化时可用）
    - 不满足前提的指标标记为不可用而非补 0
    - _Requirements: 3.10, 3.11, 3.12_

  - [x]* 3.6 为组合统计编写属性测试
    - **Property 9: 组合统计只聚合合格产品并按累计买入金额加权**
    - **Validates: Requirements 3.10, 3.11, 3.12**

- [x] 4. 检查点 - 确保计算层与契约层测试全部通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. 数据访问层
  - [x] 5.1 实现交易查询与计数
    - 新建 `crud.py`，实现 `queryTransactions(db, query)` 与 `countTransactions(db)`
    - 把产品类型 / 交易方向 / `trade_date` 闭区间筛选、产品名称与产品代码的 `LIKE %v%` 搜索、产品历史交易范围（`product_type` + `product_code`）全部下推 SQL；多个已启用条件按逻辑与组合
    - 指定 `trade_date_order` 时按交易日期排序，未指定时按 `id` 升序以保证顺序稳定
    - _Requirements: 2.2, 2.3, 2.10, 2.14, 2.16, 2.17, 2.18_

  - [x]* 5.2 为查询谓词编写属性测试
    - **Property 3: 查询结果恰好是满足全部已启用谓词的交易集合**
    - **Validates: Requirements 2.10, 2.16, 2.17, 2.18**
    - 对任意启用子集断言健全性与完备性；偏置同产品代码不同产品类型、含中文与 emoji 的名称、闰日与跨年区间

  - [x] 5.3 实现交易写入删除与估值读写
    - 实现 `addTransaction`、`removeTransaction`（主键不存在返回 `None`）、`getLatestValuations(db, keys)`（按 `valuation_date` 取最大者，无估值的产品不出现在返回映射中）
    - 实现 `upsertValuation`：复用 `omo/crud.py` 的 `sqlite_upsert(...).on_conflict_do_update(index_elements=[三列], set_=dict(unit_price=..., updated_at=...)).returning(...)`
    - 写操作异常时 `db.rollback()`，不在 crud 中做业务判断
    - _Requirements: 1.3, 1.5, 3.3, 3.4_

  - [x]* 5.4 为交易写入语义编写属性测试
    - **Property 11: 交易写入语义（创建可检索、删除即消失且互不影响）**
    - **Validates: Requirements 1.3, 1.5**

  - [x]* 5.5 为估值 upsert 覆盖语义编写集成测试
    - 对同一 `(产品类型, 产品代码, 估值日期)` 连续写入 N 次，断言表内该键仅 1 行且单价等于最后一次写入值
    - 使用临时 SQLite 文件并在结束后清理
    - _Requirements: 3.3_

- [x] 6. 服务层
  - [x] 6.1 实现 TransactionService
    - 新建 `service.py`，实现 `listTransactions`（查询 → `Paginator.slice` → `PageOut`）、`createTransaction`、`deleteTransaction`（记录不存在抛 `TransactionNotFound`）
    - **刻意不提供任何更新方法**；结果为空时返回 `total=0`、`page_count=0` 而非报错
    - _Requirements: 1.3, 1.4, 1.5, 2.11, 2.22, 2.28, 2.29, 2.30, 2.31_

  - [x] 6.2 实现持仓分组与排序
    - 在 `service.py` 实现 `groupByProductKey(rows)`：以 `(product_type, product_code)` 分组并保持首次出现顺序；条目展示名称取「交易日期最大、同日 id 最大」那笔交易的名称
    - 实现 `sortHoldings(...)`：按 `position` / `totalProfit` 稳定数值排序，等值项保持来源顺序，指标不可用的条目恒排在全部可用条目之后
    - _Requirements: 2.5, 2.6, 2.15, 2.19_

  - [x]* 6.3 为持仓分组编写属性测试
    - **Property 4: 持仓条目是结果集的一个精确划分**
    - **Validates: Requirements 2.5**

  - [x]* 6.4 为持仓条目顺序编写属性测试
    - **Property 5: 持仓条目顺序遵循来源顺序或所选数值排序**
    - **Validates: Requirements 2.15, 2.19**

  - [x] 6.5 实现 HoldingService 只读聚合
    - `listHoldings(query)` 按六步流水线组装：查询结果集 → 分组 → 批量取最新估值 → 逐产品计算 → 排序 → 分页
    - `getPortfolioStatistics(query)` 复用同一筛选与搜索条件但忽略分页与排序，统计覆盖整个结果集
    - 类中不提供任何写方法
    - _Requirements: 2.4, 2.5, 2.6, 2.7, 2.15, 2.19, 2.22, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12_

  - [x] 6.6 实现 ValuationService 与 OverviewService
    - `ValuationService.upsertValuation(payload)` 写入或覆盖估值并返回生效行
    - `OverviewService.resolveInitialModule()`：`countTransactions() > 0` 返回 `holdings`，否则返回 `history`
    - _Requirements: 2.2, 2.3, 3.1, 3.3_

  - [x]* 6.7 编写服务层无效查询输入的示例测试
    - 断言页码越界抛 `PageOutOfRange` 且 `msg` 含有效页码范围；页大小越界、日期范围缺项或倒置、搜索值超长分别抛对应异常
    - 断言异常路径下不产生任何写库副作用
    - _Requirements: 2.20, 2.21, 2.26, 2.30_

- [x] 7. 路由层与后端装配
  - [x] 7.1 实现 router.py 七个接口
    - `APIRouter(prefix="/investmentLedger", tags=["investmentLedger"])`，服务层以工厂依赖注入（复用 `dependencies.get_db`）
    - `GET /initialModule`、`GET /transactions`、`POST /transactions`、`DELETE /transactions/{transactionId}`、`GET /holdings`、`GET /portfolioStatistics`、`PUT /valuations`
    - 全部以 `response_model=ApiResponse[...]` 声明；查询模型以 `Annotated[..., Depends()]` 从 query string 绑定
    - **不实现**交易更新接口、`GET /transactions/{id}`、持仓写接口
    - _Requirements: 1.1, 1.3, 1.4, 1.5, 2.2, 2.3, 2.4, 2.23, 3.1, 3.10_

  - [x] 7.2 在 app/api.py 注册账本路由
    - 追加 `from app.investmentLedger.router import router as ledgerRouter` 与 `apiRouter.include_router(ledgerRouter)`，不改动既有注册
    - _Requirements: 2.1_

  - [x]* 7.3 编写接口集成测试
    - 空库 `GET /initialModule` → `history`，插入 1 笔后 → `holdings`
    - `POST /transactions` 有效数据可在 `GET /transactions` 中检索到；无效数据返回 422 且响应含 `fieldErrors`
    - `DELETE /transactions/{id}` 存在则成功、不存在返回 404
    - `GET /holdings` 空结果返回 `total=0`、`page_count=0`；`PUT /valuations` 覆盖后统计使用最新单价
    - 全部使用临时 SQLite 文件，测试后清理，不访问真实金融接口
    - _Requirements: 1.2, 1.3, 1.5, 2.2, 2.3, 2.22, 3.3_

  - [x]* 7.4 编写接口边界断言测试
    - 断言应用路由表中不存在交易的 PUT / PATCH 方法，也不存在 `GET /transactions/{id}` 或任何以交易标识为查询条件的参数
    - 断言持仓相关路径只有 GET 方法
    - _Requirements: 1.4, 1.6, 1.7, 2.23_

- [x] 8. 检查点 - 确保后端全部测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. 前端工具链接入
  - [x] 9.1 新增 TypeScript 配置与依赖
    - 在仓库根新建 `tsconfig.json`：`strict: true`、`allowJs: true`、`checkJs: false`、`noEmit: true`、`jsx: "react"`、`moduleResolution: "bundler"`、`isolatedModules: true`、`noUncheckedIndexedAccess: true`，`include` 覆盖 `src/web/frontEnd/src/**/*`
    - 新建 `src/web/frontEnd/src/types/global.d.ts`：声明 `*.module.scss`、`*.module.css`、`*.css`、`*.scss`
    - `package.json`：dependencies 追加 `@reduxjs/toolkit@^1.9.7`；devDependencies 追加 `typescript@^5.4.5`、`@babel/preset-typescript@^7.24.0`、`@types/react@^18.2.79`、`@types/react-dom@^18.2.25`；scripts 追加 `build:web` 与 `type-check`
    - _Requirements: 2.1_

  - [x] 9.2 调整 webpack 配置以编译 TS
    - 仅改 `scripts/webpack.config.js`：追加 `resolve.extensions` 与 `alias`，babel-loader `test` 改为 `/\.[jt]sx?$/`，presets 追加 `@babel/preset-typescript`
    - CSS / Sass 两条 rule 与 `entry` 保持不变，`webpack.dev.config.js` 不改动
    - _Requirements: 2.1_

  - [x] 9.3 配置前端测试环境
    - 新增 vitest 配置：`environment: 'jsdom'`、对 `*.module.scss` 使用 `classNameStrategy: 'non-scoped'` 或 stub
    - devDependencies 追加固定版本的 `vitest`、`fast-check`、`@testing-library/react`、`@testing-library/jest-dom`、`jsdom`；测试脚本使用单次执行模式（`vitest --run`）
    - _Requirements: 2.1_

- [x] 10. 前端领域层（纯 TypeScript）
  - [x] 10.1 实现枚举常量与展示标签映射
    - `domain/ledger/constants.ts`：`PRODUCT_TYPES` / `TRADE_DIRECTIONS`（`as const` + 联合类型）、`PAGE_SIZE_OPTIONS`、`DEFAULT_PAGE_SIZE`、`MIN_PAGE_SIZE`、`MAX_PAGE_SIZE`、`LedgerModule`、`SortOrder`、`HoldingSortField`
    - `domain/ledger/labels.ts`：`PRODUCT_TYPE_LABELS` / `TRADE_DIRECTION_LABELS`（`Record<码, string>` 保证穷尽）、`LabeledOption`、`productTypeOptions()`、`tradeDirectionOptions()`
    - 常量文件不含任何中文展示文案；标签文件是中文文案的唯一来源
    - _Requirements: 1.1, 2.12, 2.24_

  - [x] 10.2 实现 LedgerQueryState 浏览状态值对象
    - `domain/ledger/LedgerQueryState.ts`：`LedgerQuerySnapshot`、`ProductScope`、`LedgerQueryParams` 类型与 `LedgerQueryState` 类
    - 静态构造 `default(module)`、`defaultWithScope(module, scope)`、`from(snapshot)`；转换方法 `withFilters(patch)`（page 恒置 1）、`withPageSize(size)`（page 恒置 1）、`withPage(page)`（仅改 page）；辅助 `isDefault(module)`、`toSnapshot()`、`toParams()`（跳过 null 字段）
    - 字段 `readonly`，构造后冻结实例与快照
    - _Requirements: 2.9, 2.13, 2.14, 2.27_

  - [x]* 10.3 为浏览状态转换编写属性测试
    - **Property 2: 浏览状态转换遵守重置不变量**
    - **Validates: Requirements 2.9, 2.13, 2.27**
    - `fc.assert(..., { numRuns: 100 })`

  - [x] 10.4 实现 TradeDraftValidator 交易草稿校验器
    - `domain/ledger/TradeDraftValidator.ts`：校验产品类型与交易方向属于码全集、产品名称 1..100、产品代码 1..32、数量为 > 0 整数、单价 > 0 且小数位恰为 2、交易日期为有效日历日期
    - 为每个无效字段返回一条中文原因（文案取自 `labels.ts`），校验过程不修改草稿任何字段值
    - _Requirements: 1.1, 1.2_

  - [x]* 10.5 为交易草稿校验编写属性测试
    - **Property 1: 交易草稿校验拒绝无效输入并保留原值**
    - **Validates: Requirements 1.2**
    - 非法枚举取值需覆盖中文字面量、大小写不符的码、空串与 `null`；名称长度取 0/1/100/101，代码长度取 0/1/32/33，单价覆盖 `0.00` / `0.01` / 三位小数 / 负数 / 非数字

  - [x] 10.6 实现 ValuationDraftValidator 估值草稿校验器
    - 校验产品类型属于码全集、产品代码 1..32、估值日期为有效日历日期、估值单价 0..999999999.99 且小数位 ≤ 2
    - 为每个无效字段返回一条中文原因，草稿字段值保持不变
    - _Requirements: 3.1, 3.2_

  - [x]* 10.7 为估值草稿校验编写属性测试
    - **Property 10: 估值草稿校验拒绝无效输入并保留原值**
    - **Validates: Requirements 3.2**
    - 单价需覆盖 `0`、`999999999.99`、`1000000000.00`、三位小数、负数

  - [x] 10.8 实现 QueryInputValidator 查询输入校验器
    - 校验搜索值非空且 ≤ 100 字符、日期范围成对且为有效日历日期且 `start <= end`、自定义页大小为 1..100 整数、请求页码为 1..总页数
    - 校验失败时返回中文提示，且不产生任何状态变更建议（由调用方决定不 dispatch）
    - _Requirements: 2.20, 2.21, 2.25, 2.26, 2.30, 2.31_

  - [x]* 10.9 为无效查询输入编写属性测试
    - **Property 7: 无效查询输入不改变已应用的浏览状态与结果**
    - **Validates: Requirements 2.20, 2.21, 2.26, 2.30**

- [x] 11. 前端通信层
  - [x] 11.1 定义后端 DTO 类型契约
    - `api/types.ts`：`ApiEnvelope`、`FieldErrorItem`、`Metric`、`TransactionOut`、`HoldingOut`、`PageOut<T>`、`PortfolioStatisticsOut`、`ValuationOut`、`InitialModuleOut` 等接口，与后端 camelCase 输出逐字段镜像，金额与比率为字符串
    - _Requirements: 2.6, 2.12, 3.9_

  - [x] 11.2 实现 axios 实例与错误归一
    - `api/request.ts`：axios 实例 + 拦截器按既有 `{ code, msg, data }` 约定泛型解包；非 200 与网络异常统一抛 `LedgerApiError`（保留 `code`、中文 `msg`、`fieldErrors`）
    - _Requirements: 1.2, 2.20, 2.21, 2.26, 2.30, 3.2_

  - [x] 11.3 实现账本 API 客户端
    - `api/ledger.ts`：`fetchInitialModule`、`fetchTransactions`、`createTransaction`、`deleteTransaction`、`fetchHoldings`、`fetchPortfolioStatistics`、`upsertValuation` 共 7 个函数，参数由 `LedgerQueryState.toParams()` 提供
    - 该文件是唯一 HTTP 出口，不提供交易更新与按标识查询的函数
    - _Requirements: 1.3, 1.4, 1.5, 2.2, 2.3, 2.23, 3.1_

  - [x]* 11.4 编写通信层单元测试
    - 断言业务错误、422 `fieldErrors`、网络异常分别归一为带中文提示的 `LedgerApiError`
    - 断言未启用的查询条件不出现在请求参数中
    - _Requirements: 1.2, 2.16, 2.17, 2.18_

- [x] 12. 前端状态层（Redux Toolkit）
  - [x] 12.1 定义 LedgerState 类型与异步 thunk
    - `store/ledger/types.ts`：当前模块、已应用查询快照、列表数据与分页元信息、组合统计、表单草稿与字段错误、加载与错误状态
    - `store/ledger/thunks.ts`：`bootstrapLedger`、`fetchHistory`、`fetchHoldings`、`fetchPortfolioStatistics`、`submitTransaction`、`removeTransaction`、`submitValuation` 等 `createAsyncThunk`
    - state 只存可序列化快照，不存类实例
    - _Requirements: 2.2, 2.3, 2.14_

  - [x] 12.2 实现 ledgerSlice
    - `createSlice({ name: 'ledger' })`：同步 reducers `switchModule`、`openHistoryWithScope`、`applyQuery`、`changePage`、`changePageSize`、草稿编辑与弹窗开合；`extraReducers` 处理各 thunk 的三态
    - 所有查询状态转换经 `LedgerQueryState.from(state.query).xxx().toSnapshot()` 完成，重置与页码归 1 规则不在 slice 内重复实现
    - 失败态不清空既有列表数据与已应用查询状态
    - _Requirements: 1.2, 2.9, 2.13, 2.14, 2.20, 2.21, 2.26, 2.27, 2.30_

  - [x] 12.3 实现派生选择器
    - `store/ledger/selectors.ts`：以 `createSelector` 派生当前模块、当前页行数据、分页信息（含 `pageCount === 0` 判定）、组合统计、字段错误映射
    - _Requirements: 2.22, 2.28, 2.31_

  - [x] 12.4 迁移 store 根装配
    - 将 `store/index.js` 改写为 `store/index.ts`：`configureStore({ reducer: { news, stock, crawlers, ledger } })` 并导出 `RootState` / `AppDispatch`
    - 删除 `store/reducers/index.js`；`main.js` 仅把 `import store from './store/index.js'` 改为 `'./store'`；三个既有 reducer 文件零改动
    - _Requirements: 2.1_

  - [x]* 12.5 编写状态层单元测试
    - 断言 slice 的重置不变量（模块切换、持仓入口进入、条件变更后页码为 1）与失败态不丢数据
    - 断言 `store.getState()` 仍含 `news` / `stock` / `crawlers` 三个键且初始值与迁移前一致，控制台无 serializable / immutable 告警
    - _Requirements: 2.9, 2.13, 2.27_

- [ ] 13. 检查点 - 确保前端领域层与状态层测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. 前端展示组件
  - [x] 14.1 实现 MetricValue 与 LedgerPagination
    - `MetricValue`：`available=false` 时渲染「不可用」并以 Tooltip 展示中文原因，绝不以 0 替代
    - `LedgerPagination`：页大小选项 10/20/50 + 自定义页大小输入；显示当前页码与总页数；`pageCount === 0` 时显示「当前结果没有可浏览的页」
    - 样式写入各自 `index.module.scss`，不使用行内样式
    - _Requirements: 2.24, 2.25, 2.26, 2.28, 2.29, 2.30, 2.31, 3.9_

  - [x] 14.2 实现 TradeFilterBar 筛选与搜索栏
    - 产品类型、交易方向筛选（选项由 `productTypeOptions()` / `tradeDirectionOptions()` 生成）、交易日期范围 `RangePicker`、产品名称与产品代码搜索框
    - 校验不通过时仅 `message.error` 提示，不回调应用查询
    - _Requirements: 2.16, 2.17, 2.18, 2.20, 2.21_

  - [x] 14.3 实现 TradeFormModal 与 ValuationFormModal
    - 交易表单：产品类型、交易方向为选择控件，产品名称、产品代码、交易单价、交易数量、交易日期为输入控件；提交前经 `TradeDraftValidator` 校验，字段错误映射到 `Form.Item` 的 `help` / `validateStatus` 并保留已填值
    - 估值表单：产品类型、产品代码、估值日期、估值单价，提交前经 `ValuationDraftValidator` 校验
    - 均不提供任何编辑既有交易的入口
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 3.1, 3.2_

  - [x] 14.4 实现 TradeHistoryPanel 历史交易面板
    - 表格恰为产品类型、产品名称、产品代码、交易单价、交易数量、交易方向、交易日期 7 个独立列 + 操作列（删除，带 `Popconfirm`）
    - 每笔交易占用一行且不重复；不渲染交易标识；无编辑入口；支持交易日期排序；应用产品历史交易范围时展示范围标签
    - 空结果时 0 行但保留列头
    - _Requirements: 1.5, 1.4, 2.10, 2.11, 2.12, 2.15, 2.22, 2.23_

  - [x] 14.5 实现 HoldingsPanel 与 PortfolioSummary
    - 持仓表格恰为产品类型、产品名称、产品代码、持仓、总收益、总收益率、年化收益率 7 个只读列；不展示逐笔交易、无展开行、无新增/删除/编辑控件
    - 每个持仓条目提供进入历史交易记录模块的入口；持仓与总收益列支持升序/降序排序
    - 用户在持仓模块发起写操作意图时以 `message.info` 提示前往历史交易记录模块维护 / 持仓模块仅供查看，且不发任何写请求
    - `PortfolioSummary` 以 `Descriptions` 渲染总持仓、总收益、总收益率、总年化收益率（复用 `MetricValue`）
    - _Requirements: 1.6, 1.7, 2.4, 2.5, 2.6, 2.7, 2.8, 2.19, 2.22, 3.10, 3.11, 3.12_

  - [x] 14.6 实现 ModuleSwitch 模块切换器
    - 以 `Radio.Group` 在持仓模块与历史交易记录模块之间切换，切换只回调容器，不改变 URL
    - _Requirements: 2.1, 2.13_

  - [x]* 14.7 编写组件示例测试
    - 断言两张表格的列集合与顺序、持仓表无写入控件与展开行、渲染文本中不出现记录 id
    - 断言空结果保留列头、页大小选项为 10/20/50、`pageCount === 0` 时的提示文案
    - 断言产品类型与交易方向列渲染为中文标签而 dispatch 载荷为英文码，且 `Object.keys(PRODUCT_TYPE_LABELS)` 与 `PRODUCT_TYPES` 集合相等
    - 断言组件树中不存在行内 `style` 属性；查询使用 `getByRole` / `getByLabelText`
    - _Requirements: 1.4, 2.4, 2.6, 2.7, 2.12, 2.22, 2.23, 2.24, 2.31_

- [x] 15. 页面容器与路由装配
  - [x] 15.1 实现 LedgerPage 容器
    - `pages/InvestmentLedger/index.tsx`：类型化 `connect` 绑定 store，挂载时 dispatch `bootstrapLedger()` 决定初始模块；编排 `ModuleSwitch` + 当前面板 + `PortfolioSummary` + 两个表单弹窗
    - 模块导航与持仓条目入口分别 dispatch `switchModule` / `openHistoryWithScope`，保证以默认浏览状态打开目标模块
    - 校验失败与接口错误统一在容器内以 `message` 提示，不清空当前结果
    - _Requirements: 1.6, 1.7, 2.2, 2.3, 2.8, 2.9, 2.13, 2.14, 2.20, 2.21, 2.26, 2.30_

  - [x] 15.2 注册前端路由
    - 在 `router.js` 追加 `/investmentLedger` 路由项，引入 `./pages/InvestmentLedger/index`（import 不写扩展名），不改动既有路由项
    - _Requirements: 2.1_

  - [x]* 15.3 编写容器示例测试
    - 断言空数据时默认打开历史交易记录模块、存在交易时默认打开持仓模块
    - 断言模块间导航与从持仓条目进入历史交易后浏览状态为默认状态（含范围）
    - 断言持仓模块中的写操作意图只产生提示、不触发写请求
    - _Requirements: 1.6, 1.7, 2.2, 2.3, 2.9, 2.13_

- [x] 16. 全链路校验与回归
  - [x] 16.1 执行类型检查与生产构建并修复问题
    - 运行 `npm run type-check`（`tsc --noEmit`）直至 0 错误，确认既有 `.js` 因 `checkJs: false` 无报错
    - 运行 `npm run build:web` 确认 `.ts` / `.tsx` 经 babel-loader 打包通过、既有入口链路不受 loader `test` 放宽影响
    - 运行 `pytest -q` 与 `vitest --run`（均为单次执行模式）并修复失败项
    - _Requirements: 2.1_

- [ ] 17. 最终检查点 - 确保全部测试与构建通过
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- 标记 `*` 的子任务为可选测试任务，追求最小可用版本时可跳过；核心实现任务不可跳过。
- 11 条正确性属性各自对应且仅对应一个属性测试任务：Property 1 → 10.5、Property 2 → 10.3、Property 3 → 5.2、Property 4 → 6.3、Property 5 → 6.4、Property 6 → 3.2、Property 7 → 10.9、Property 8 → 3.4、Property 9 → 3.6、Property 10 → 10.7、Property 11 → 5.4。
- 需求 3.3 的估值覆盖语义依赖数据库副作用，按设计以集成测试（5.5）覆盖而非属性测试。
- 后端属性测试使用 `@settings(max_examples=100, deadline=None)`，前端使用 `fc.assert(..., { numRuns: 100 })`；金额与比率断言一律使用 `Decimal`，禁止 `float`。
- 每个属性测试首行注释关联设计，例如 `# Feature: investment-trade-ledger, Property 8: 产品统计精确计算并显式标记不可用指标`。
- 集成测试只使用临时 SQLite 文件，不得连接 `various_data.db` 或 `various_data_dev.db`，不访问真实金融接口。
- 装配点只做追加（`app/api.py`、`app/models.py`、`main.py`、`router.js`），既有业务逻辑零改动；store 根装配为唯一改写文件。

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "9.1"] },
    { "id": 1, "tasks": ["1.2", "9.2", "10.1"] },
    { "id": 2, "tasks": ["1.3", "9.3", "10.2", "11.1"] },
    { "id": 3, "tasks": ["2.1", "1.4", "10.3", "10.4", "11.2"] },
    { "id": 4, "tasks": ["2.3", "2.2", "10.5", "10.6", "11.3"] },
    { "id": 5, "tasks": ["3.1", "2.4", "10.7", "10.8", "11.4"] },
    { "id": 6, "tasks": ["3.3", "3.2", "10.9", "12.1"] },
    { "id": 7, "tasks": ["3.5", "3.4", "12.2"] },
    { "id": 8, "tasks": ["5.1", "3.6", "12.3"] },
    { "id": 9, "tasks": ["5.3", "5.2", "12.4"] },
    { "id": 10, "tasks": ["6.1", "5.4", "12.5", "14.1"] },
    { "id": 11, "tasks": ["6.2", "5.5", "14.2"] },
    { "id": 12, "tasks": ["6.5", "6.3", "14.3"] },
    { "id": 13, "tasks": ["6.6", "6.4", "14.4"] },
    { "id": 14, "tasks": ["7.1", "6.7", "14.5"] },
    { "id": 15, "tasks": ["7.2", "14.6"] },
    { "id": 16, "tasks": ["15.1", "7.3"] },
    { "id": 17, "tasks": ["15.2", "7.4", "14.7"] },
    { "id": 18, "tasks": ["15.3"] },
    { "id": 19, "tasks": ["16.1"] }
  ]
}
```
