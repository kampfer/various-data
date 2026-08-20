# Implementation Plan: 投资交易账本

## Overview

本计划依据当前 `requirements.md` 与 `design.md` 重排，目标是完成交易账本、独立持仓/历史路由、查询浏览、统计计算以及受控外部估值采集链路。任务只涉及代码、配置或自动化测试；不修改需求/设计文档，不提供用户手动估值维护入口。

执行约束：
- 保留当前清单中已经标记为完成且仍与最新设计一致的任务状态；凡因设计修订而失效的旧任务改写为新的未完成任务，不将未完成工作标记为完成。
- 后端使用 Python/FastAPI/SQLAlchemy/Pydantic，前端使用 TypeScript/React/RTK；遵循 OOP、分层模块化、camelCase 后端命名和现有装配方式。
- 复用现有账本模块、组件、依赖和测试工具；禁止重复实现平行模块，禁止行内样式，金额/比率不在前端使用浮点计算。
- 估值只读路径属于账本业务；估值写入只能经 `valuation_ingest` 内部受控边界，由白名单采集器通过协议提交，不能由前端或公开账本 API 写入。
- 标记 `*` 的测试任务为可选；其余任务为必须完成。每项任务均给出完成条件、需求映射和设计依据。

## Tasks

- [x] 1. 保留后端基础领域与数据库骨架
  - [x] 1.1 保留英文领域常量、测试隔离夹具和开发测试依赖
    - 已完成 `ProductType`、`TradeDirection`、分页/字段长度/年化常量及临时 SQLite 测试夹具；不得引入中文码值。
    - 完成条件：常量与现有测试夹具可被后续交易、估值摄取模块复用。
    - _Requirements: 1.1, 2.24, 2.25, 3.11_
  - [x] 1.2 保留 `DecimalText` 精确列类型
    - 已完成 Decimal 往返、两位小数和 `None` 透传；实现不得经过 `float`。
    - 完成条件：金额和估值单价均能以 Decimal 精确读写。
    - _Requirements: 1.2, 3.2, 3.12_
  - [x] 1.3 扩展交易与估值模型以支持来源审计和幂等键
    - 修改 `investmentLedger/models.py`：保留不可变交易模型；为 `Valuation` 增加 `source_id`、采集器/版本或引用审计字段、标准化采集时间，并建立 `(product_type, product_code, valuation_date, source_id)` 唯一约束与读取索引。
    - 复用既有 `LedgerBase`/`initAppModels()` 注册，不创建第二条建表路径；模型不暴露公开写入方法。
    - 完成条件：重建后的模型可区分同日不同来源，重复同键写入不会产生重复行，既有交易表行为不回归。
    - _Requirements: 1.4, 2.5, 2.10, 3.1, 3.11, 3.17_
  - [x]* 1.4 保留基础模型与列类型单元测试
    - 已覆盖 Decimal 往返和临时 SQLite 索引；测试不得连接真实数据库。
    - _Requirements: 3.1_
  - [ ]* 1.5 补充估值来源字段、唯一约束和审计元数据测试
    - 验证同产品/日期/来源唯一性、跨来源并存、Decimal/date 精确性及采集元数据长度边界。
    - 完成条件：模型约束测试在临时 SQLite 中稳定通过。
    - _Requirements: 3.1, 3.11, 3.17_

- [x] 2. 交易契约、查询契约与统一错误
  - [x] 2.1 保留交易/查询 Pydantic 契约与字段校验
    - 已覆盖交易字段、筛选搜索、日期闭区间、页码和页大小边界；响应金额/比率使用字符串。
    - _Requirements: 1.1, 1.2, 2.16, 2.17, 2.18, 2.20, 2.21, 2.24, 2.25, 2.26, 3.6_
  - [x]* 2.2 保留 schemas 示例校验测试
    - 已覆盖枚举、长度、单价精度、非法日期、倒置日期和页大小，并定位字段错误。
    - _Requirements: 1.2, 2.20, 2.21, 2.26_
  - [x] 2.3 保留异常体系和全局错误处理器
    - 已完成中文字段错误、页码范围、数据库错误脱敏及统一响应信封；不得回显 SQL/堆栈。
    - _Requirements: 1.2, 1.5, 2.20, 2.21, 2.26, 2.30, 3.12_
  - [x]* 2.4 保留异常处理器单元测试
    - _Requirements: 1.2, 2.30, 3.12_

- [x] 3. 纯计算层与分页
  - [x] 3.1 保留 `Paginator` 的完整分页语义
    - 完成条件：空集总页数为 0、有效页按切片返回、越界抛出业务异常。
    - _Requirements: 2.11, 2.24, 2.25, 2.28, 2.29, 2.30, 2.31_
  - [x]* 3.2 保留 Property 6 分页属性测试
    - **Property 6: 分页是结果集无重复、无遗漏的有序划分**；覆盖空集、整除/非整除和边界页大小。
    - **Validates: Requirements 2.11, 2.25, 2.28, 2.29, 2.31**
  - [x] 3.3 保留 `ProductPerformanceCalculator` 的 Decimal 统计
    - 完成条件：持仓、持仓市值、收益、收益率、年化收益率按定义域计算；缺输入只标记对应指标不可用，不以 0 替代。
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_
  - [x]* 3.4 保留 Property 8 产品统计属性测试
    - **Property 8: 产品统计精确计算并显式标记不可用指标**。
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6**
  - [x] 3.5 保留 `PortfolioCalculator` 组合统计
    - 完成条件：仅聚合有最新估值的产品，收益率按累计买入金额计算，总年化按金额加权且不补 0。
    - _Requirements: 3.7, 3.8, 3.9_
  - [x]* 3.6 保留 Property 9 组合统计属性测试
    - **Property 9: 组合统计只聚合合格产品并按累计买入金额加权**。
    - **Validates: Requirements 3.7, 3.8, 3.9**

- [x] 4. 交易数据访问、分组、筛选排序和只读估值查询
  - [x] 4.1 保留交易查询谓词下推与稳定排序
    - 已支持产品类型、方向、日期闭区间、名称/代码包含搜索和成对产品范围；多个条件使用 AND；未指定排序时保持稳定顺序。
    - _Requirements: 2.5, 2.10, 2.16, 2.17, 2.18_
  - [x]* 4.2 保留 Property 3 查询谓词属性测试
    - **Property 3: 查询结果恰好是满足全部已启用谓词的交易集合**。
    - **Validates: Requirements 2.10, 2.16, 2.17, 2.18**
  - [x] 4.3 保留交易创建、删除和只读估值读取动作
    - 交易写入异常回滚，删除不存在返回空；不得恢复 `upsertValuation`、`ValuationService` 或其它公开估值写动作。
    - _Requirements: 1.3, 1.5, 1.4, 3.1_
  - [x]* 4.4 保留 Property 10 交易写入属性测试
    - **Property 10: 交易写入语义（创建可检索、删除即消失且互不影响）**。
    - **Validates: Requirements 1.3, 1.5**
  - [x] 4.5 将最新估值读取改为来源感知的只读查询
    - `getLatestValuations` 按产品和最大估值日期取候选，再按核心配置的 `source_priority` 选择来源；读取层不负责写入、不覆盖数据。
    - 完成条件：无估值产品不返回；同日多来源选择与优先级一致，账本统计只能消费标准化记录。
    - _Requirements: 3.1, 3.7, 3.8, 3.9_
  - [x] 4.6 保留持仓分组、展示名称和数值排序
    - 已按 `(product_type, product_code)` 精确分组，未选字段按持仓升序，选定持仓/总收益按稳定数值排序，不可用项置后。
    - _Requirements: 2.5, 2.6, 2.15, 2.19_
  - [x]* 4.7 保留 Property 4/5 持仓分组与排序属性测试
    - **Property 4: 持仓条目是结果集的一个精确划分**；**Property 5: 持仓条目顺序遵循默认或所选数值排序**。
    - **Validates: Requirements 2.5, 2.15, 2.19**

- [x] 5. 账本服务层
  - [x] 5.1 保留 `TransactionService` 创建、查询、删除和不可编辑边界
    - 完成条件：无更新方法，空结果返回 0 条/0 页，删除不存在返回业务错误。
    - _Requirements: 1.3, 1.4, 1.5, 2.11, 2.22, 2.28, 2.29, 2.30, 2.31_
  - [x] 5.2 保留 `HoldingService` 与 `OverviewService` 只读编排
    - 查询→分组→来源感知最新估值→统计→排序→分页；组合统计忽略分页；默认模块由初始接口判定，不写入交易状态。
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.19, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9_
  - [x]* 5.3 补充服务层无效输入、空结果和统计只读测试
    - _Requirements: 2.20, 2.21, 2.22, 2.26, 2.30, 3.6_

- [x] 6. 外部估值采集协议、白名单注册与标准化
  - [x] 6.1 定义 `valuation_ingest/protocol.py` 的采集器协议和值对象
    - 实现 `CollectorManifest`、`StandardValuation`、`ValuationCollector`；manifest 必须声明唯一标识、版本、来源和支持的产品类型；协议只接收产品键/超时，不接收 SQLAlchemy Session。
    - 完成条件：协议可被多个数据源复用，采集器只能返回原始结果/候选标准结果，不能导入数据库连接。
    - _Requirements: 3.10, 3.11, 3.13, 3.15_
  - [x] 6.2 实现 `CollectorRegistry` 白名单/受控目录发现与注册
    - 仅扫描 `collectors/` 和显式受信目录，校验 manifest、入口、版本、来源、能力集合及插件自声明一致性；拒绝目录外路径、重复版本和冲突优先级，并记录元数据。
    - 完成条件：未知路径不会被动态加载；新增数据源只需插件和 manifest，不改账本核心业务。
    - _Requirements: 3.11, 3.14, 3.15_
  - [x] 6.3 实现 `ValuationNormalizer` 标准化与业务校验
    - 校验产品类型/能力、代码长度、有效日期、正且有限的单价、两位小数规则、来源与 manifest 一致、采集时间和引用字段格式；非法结果逐条拒绝，不调用仓储写入。
    - 完成条件：合法结果产生字段完整且 Decimal/date 规范一致的 `StandardValuation`，不静默四舍五入超过两位的小数。
    - _Requirements: 3.12_
  - [ ]* 6.4 编写 Property 11 标准化属性测试
    - **Property 11: 标准估值结果规范化且非法结果不进入账本**；使用 fake collector/clock，不访问外网。
    - **Validates: Requirements 3.12**
  - [ ]* 6.5 编写 manifest/白名单注册冒烟测试
    - 验证必填元数据、受信目录边界、重复版本/冲突拒绝及不执行任意用户路径。
    - _Requirements: 3.11, 3.14_

- [x] 7. 估值受控写入、来源优先级、故障隔离与触发
  - [x] 7.1 实现 `ValuationRepository` 的事务幂等写入与来源优先级
    - 只接受 `StandardValuation`；以产品/日期/来源唯一键实现重复批次等效写入；同日跨来源按核心 `source_priority` 决定生效记录，优先级相同保留已有值并记录冲突；所有写入在受控事务中完成。
    - 完成条件：仓储是估值唯一写入口，账本公开路由、前端 API 和采集器均无法绕过它写数据库。
    - _Requirements: 3.1, 3.12, 3.13, 3.17_
  - [x] 7.2 实现 `CollectorOrchestrator` 的能力匹配、超时、重试和失败隔离
    - 只向采集器提供协议接口；按 manifest 能力派发；单个插件异常、解析失败或超时被记录并隔离，其他采集器继续执行；查询服务不因采集失败中断。
    - 完成条件：成功批次仍可标准化并写入，失败插件不会取消其它独立批次。
    - _Requirements: 3.10, 3.13, 3.16_
  - [ ]* 7.3 编写 Property 12 采集器异常与超时隔离属性测试
    - **Property 12: 采集器异常与超时彼此隔离**；使用成功/网络异常/解析异常/超时 fake collector 和受控时钟。
    - **Validates: Requirements 3.16**
  - [ ]* 7.4 编写 Property 13 幂等与来源冲突属性测试
    - **Property 13: 估值摄取幂等且来源冲突结果确定**；验证重复批次不增行、到达顺序不影响优先级结果、同优先级冲突保留旧值并记录。
    - **Validates: Requirements 3.1, 3.17**
  - [x] 7.5 增加受控命令/后台任务入口并禁止前端触发
    - `valuation_ingest/cli.py` 调用编排器，支持受控参数、结果日志和退出状态；保留可替换后台任务抽象，但不注册 FastAPI 前端估值写路由。
    - 完成条件：命令可触发采集链路，前端没有估值维护按钮、表单或公开写入口。
    - _Requirements: 3.13, 3.18_
  - [ ]* 7.6 编写估值摄取集成与边界测试
    - 覆盖合法结果落库、非法结果不落库、重复写入、跨来源优先级、失败隔离、命令触发，以及应用路由不存在估值写方法；仅使用 fake collector 和临时 SQLite。
    - _Requirements: 3.1, 3.12, 3.13, 3.16, 3.17, 3.18_

- [x] 8. 公开后端 API 与装配边界
  - [x] 8.1 修订账本公开路由为交易写入和账本只读接口
    - 保留 `GET /initialModule`、交易列表/创建/删除、持仓和组合统计；删除/迁移现有 `PUT /valuations`、`ValuationService` 暴露路径及任何公开估值写入；不提供交易更新或按交易标识查询。
    - 完成条件：路由表只包含设计规定的公开接口，持仓相关路径只有 GET，估值写入只能由 `valuation_ingest` 内部调用。
    - _Requirements: 1.3, 1.4, 1.5, 2.4, 2.23, 3.13, 3.18_
  - [x] 8.2 保留既有 app 路由与模型注册装配
    - 已完成账本 router、LedgerBase 和异常处理器的基础装配；后续只做必要的移除/迁移，不重复注册。
    - _Requirements: 2.1, 3.13_
  - [ ]* 8.3 编写公开 API 边界与回归集成测试
    - 断言不存在 PUT/PATCH 估值写路由、交易更新、`GET /transactions/{id}` 或标识查询参数；验证交易创建/删除、空结果分页和最新估值只读统计。
    - _Requirements: 1.3, 1.4, 1.5, 2.22, 2.23, 3.1, 3.7, 3.18_

- [x] 9. 前端工具链和基础领域类型
  - [x] 9.1 保留 TypeScript、RTK、Vitest、fast-check 和 webpack TS 支持
    - 继续使用现有固定版本、`strict`、`allowJs`、`checkJs: false`、单次测试脚本；不升级 RTK 2.x，不新增同类依赖。
    - _Requirements: 2.1_
  - [x] 9.2 保留英文枚举码与中文展示映射分离
    - `constants.ts` 不含中文文案，`labels.ts` 是码到中文的唯一映射来源；组件不得手写对照表。
    - _Requirements: 1.1, 2.12, 2.24_
  - [x] 9.3 保留交易草稿和查询输入校验器
    - 校验失败保留原值并不产生状态变更建议；覆盖交易、搜索、日期、页大小和页码边界。
    - _Requirements: 1.2, 2.20, 2.21, 2.25, 2.26, 2.30, 2.31_
  - [x]* 9.4 保留 Property 1/7 前端校验属性测试
    - **Property 1: 交易草稿校验拒绝无效输入并保留原值**；**Property 7: 无效查询输入不改变已应用的浏览状态与结果**。
    - **Validates: Requirements 1.2, 2.20, 2.21, 2.26, 2.30**
  - [x] 9.5 修订 `LedgerQueryState` 为按模块保存浏览快照并支持导航意图
    - 删除 `activeModule` 语义；保留 history/holdings 各自筛选、搜索、排序、页大小、有效页码和结果快照。实现 `default`、`defaultWithScope`、`withFilters`、`withPageSize`、`withPage`；`scopeProductType` 与 `scopeProductCode` 必须成对且仅用于历史范围。
    - 完成条件：模块直接切换不重置目标快照；持仓入口和无上下文 history 深链才重置为默认状态；任何条件/排序/页大小变更将页码置 1。
    - _Requirements: 2.9, 2.10, 2.13, 2.14, 2.27_
  - [ ]* 9.6 修订 Property 2 浏览状态属性测试
    - **Property 2: 浏览状态转换遵守导航意图与重置不变量**；覆盖 module-switch、holding-scope、无上下文深链和页码重置。
    - **Validates: Requirements 2.9, 2.13, 2.14, 2.27**

- [x] 10. 前端通信与状态层基础
  - [x] 10.1 保留 typed DTO、axios 错误归一和唯一 HTTP 出口
    - API 客户端只提供交易写入、交易/持仓/组合/初始模块读取；不提供估值写入、交易更新或按标识查询。
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 2.23, 3.1, 3.13_
  - [x] 10.2 修订 Ledger state 为路由驱动且不含 `activeModule`/`bootstrapLedger`
    - `types.ts` 只存可序列化的 per-module query/list/form/error 快照；移除旧 `activeModule`、`switchModule`、`bootstrapLedger`。保留 `fetchInitialModule`、`fetchHistory`、`fetchHoldings`、`fetchPortfolioStatistics`、交易提交/删除 thunk。
    - 完成条件：路由切换不 dispatch 模块切换 action，不清空目标模块结果；无效输入和请求失败保留已应用状态/列表。
    - _Requirements: 2.2, 2.3, 2.9, 2.13, 2.14, 2.20, 2.21, 2.26, 2.27, 2.30_
  - [x] 10.3 修订 selectors 与 reducer 测试
    - 选择器按当前路由/目标模块读取对应快照，正确处理 0 页；测试确认无 `activeModule`、无 `bootstrapLedger`，直接切换保留状态，范围进入 history 才重置。
    - _Requirements: 2.9, 2.13, 2.14, 2.22, 2.28, 2.31_

- [x] 11. 前端展示组件（保留已完成部分，修订冲突部分）
  - [x] 11.1 保留 `MetricValue`、`LedgerPagination`、筛选栏和交易表单
    - 已实现不可用指标、分页边界、筛选校验、交易创建；所有样式位于 CSS Modules，无行内样式；表单不含估值字段。
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 2.16, 2.17, 2.18, 2.20, 2.21, 2.24-2.31, 3.6_
  - [x] 11.2 修订历史交易表格和持仓表格以匹配独立模块边界
    - 历史表格只展示规定交易列和删除操作，不显示 id/编辑入口；持仓表格只展示规定汇总列、无展开交易、无估值写入口，并提供带范围意图的历史入口；复用已有组件而非复制实现。
    - 完成条件：空结果保留列头；持仓写操作只提示用户去历史模块/只读，不发写请求。
    - _Requirements: 1.5, 1.6, 1.7, 2.4, 2.5, 2.6, 2.7, 2.8, 2.10, 2.11, 2.12, 2.22, 2.23, 3.18_
  - [x] 11.3 将 `ModuleSwitch` 改为 URL 导航，不使用旧 `Radio.Group` 内部状态切换
    - 使用设计规定的 antd Menu/路由导航方式，`useLocation` 派生高亮，`useNavigate` 携带 `ledgerNavigation='module-switch'`；不得 dispatch `switchModule`，不得依赖 `activeModule`。
    - 完成条件：URL 为 `/investmentLedger/holdings` 或 `/investmentLedger/history`，直接切换保留目标状态，组件无行内样式。
    - _Requirements: 2.1, 2.13_
  - [ ]* 11.4 更新组件边界与无行内样式测试
    - 验证列集合/顺序、持仓只读、无 id、无估值控件、URL 导航、中文标签映射和组件树无 `style` 属性。
    - _Requirements: 1.4, 1.6, 1.7, 2.1, 2.4, 2.6, 2.7, 2.12, 2.13, 2.23, 3.18_

- [x] 12. 页面容器、嵌套路由与导航装配
  - [x] 12.1 将 `pages/InvestmentLedger/index.tsx` 改为 `LedgerLayout`
    - 父路由只渲染导航和 `<Outlet />`；删除旧单页 `activeModule`、`bootstrapLedger` 和“当前面板三元切换”编排，样式全部放入 `index.module.scss`。
    - 完成条件：布局层不直接调用估值写入、不保存模块状态，目标子路由负责各自查询。
    - _Requirements: 2.1, 2.13, 2.14, 3.18_
  - [x] 12.2 实现 `IndexRedirect` 默认模块判定
    - 无子路径时调用 `fetchInitialModule`，无交易跳 history，有交易跳 holdings；使用 `<Navigate replace>`，不写 redux 模块字段。
    - _Requirements: 2.2, 2.3_
  - [x] 12.3 实现 `HoldingsPage`、`HistoryPage` 和持仓范围导航
    - 直接模块切换携带 module-switch 意图；持仓条目进入 history 携带 holding-scope 并应用默认状态+成对产品范围；无上下文 history 深链展示全部交易默认状态。
    - 完成条件：筛选、排序、分页和结果在两个模块间按设计保留/重置，scope 不被当作普通搜索条件。
    - _Requirements: 2.8, 2.9, 2.10, 2.13, 2.14, 2.16-2.19, 2.24-2.31_
  - [x] 12.4 更新 `router.js` 嵌套路由并回归导航测试
    - 注册 `/investmentLedger` 父路由及 `holdings`/`history` 子路由和 index redirect，复用既有 Hash Router；测试默认打开、直接切换保留状态、范围入口重置状态。
    - _Requirements: 2.1, 2.2, 2.3, 2.9, 2.13, 2.14_

- [x] 13. 删除过时估值维护实现并完成全链路回归
  - [x] 13.1 移除旧 `ValuationFormModal`、估值维护按钮和公开 `PUT /valuations` 依赖
    - 删除/迁移只删除冲突代码，不改变交易和持仓只读能力；前端 API、容器、路由、后端服务均不得留下可达估值写入口。
    - 完成条件：代码搜索和路由边界测试均证明估值只能经内部 `valuation_ingest` 写入。
    - _Requirements: 3.13, 3.18_
  - [x] 13.2 连接受控命令、采集器注册、摄取仓储与账本只读查询
    - 完成端到端内部链路：命令→编排器→协议采集器→标准化→仓储；账本服务只通过来源优先级读取结果；新增来源不改核心账本服务。
    - _Requirements: 3.1, 3.10-3.18_
  - [x] 13.3 执行类型检查、构建和一次性自动化测试
    - 运行 `npm run type-check`、`npm run build:web`、`pytest -q`、`vitest --run`；只使用临时 SQLite/fake collector，不访问真实金融接口；修复失败后保留最终证据。
    - 完成条件：类型检查、构建、后端测试、前端测试和采集器属性/集成测试全部通过。
    - _Requirements: 1.2, 1.3, 1.5, 2.1, 2.9, 2.13, 2.16-2.31, 3.1-3.18_

- [x] 14. 检查点 - 后端交易、估值摄取与公开边界完成
  - 确认交易创建/删除、持仓历史路由契约、估值协议/白名单/标准化/幂等/故障隔离/命令触发均已有实现和测试；如有问题先修复再进入前端装配。

- [x] 15. 最终检查点 - 确保全部测试与构建通过
  - 确认未修改 `requirements.md`、`design.md` 或本功能之外源代码；确认所有未完成任务仍未被误标为完成，并询问用户是否有后续实现问题。

- [x] 16. 新建交易记录弹窗的基金搜索辅助（需求 5）
  - [x] 16.1 后端基金搜索代理：契约、第三方客户端与故障收敛
    - 在 `schemas.py` 新增 `FundSearchQuery`（单参数 `keyword`，1..100 字符）与 `FundSearchOut`（`fund_name` 1..100、`fund_code` 1..32）；在 `fund_search.py` 实现 `EastmoneyFundSearchClient`（不带 callback 直取 JSON，固定超时）与 `FundSearchService`（过滤 `FundBaseInfo` 非空或 `CATEGORYDESC=="基金"` 的条目，第三方异常收敛为空结果并经 `app.logger` 记录，不外泄异常）；在 `router.py` 新增 `GET /fundSearch`。
    - 完成条件：`keyword` 为空/超长被 Pydantic 拒绝；第三方异常返回 200 + 空列表且不抛异常；非基金条目被过滤；结果 `fund_name`/`fund_code` 长度可直接回填草稿。
    - _Requirements: 5.2、5.6、5.7_
  - [x] 16.2 前端基金搜索 DTO、API 出口与防抖控制器
    - 在 `api/types.ts` 新增 `FundSearchOut`；在 `api/ledger.ts` 新增 `searchFunds(keyword)`；在 `domain/ledger/FundSearchController.ts` 实现 `FundSearchController`（500ms 默认防抖、空 keyword 不发请求且回调空结果、`requestId` 竞态保护仅最新结果回调、`dispose()` 取消定时器）。
    - 完成条件：连续输入只发起最后一次请求；空输入不发请求；并发请求只回放最新结果；卸载调用 `dispose()` 不在组件卸载后 setState。
    - _Requirements: 5.3、5.6_
  - [x] 16.3 `FundSearchResults` 组件与 `TradeFormModal` 集成
    - 新建 `components/InvestmentLedger/FundSearchResults/{index.tsx,index.module.scss}`（仅展示「基金名称 + 基金代码」+ 空态提示，无自身请求、无 `style` 内联）；在 `TradeFormModal` 构造 `FundSearchController`，`componentDidUpdate` 仅在 `productType==='FUND'` 且 `productName`/`productCode` 变化为非空时触发 `search(最新变化字段值)`；选中结果用 `justSelected` 标记回填两字段并清空结果、跳过本次搜索；非基金类型或关闭弹窗时 `dispose` 并清空结果。
    - 完成条件：非基金类型不渲染结果区、不发请求；选中后两字段回填且不触发重复搜索；样式全部走 CSS Modules。
    - _Requirements: 5.1、5.4、5.5、5.8_
  - [x]* 16.4 基金搜索属性与集成测试
    - 后端：fake client 覆盖正常基金/混合基金股票/第三方异常/超时/非法 JSON；断言空结果、非基金过滤、日志调用。前端：fake `searchFunds` 覆盖防抖 500ms、空 keyword 不发请求、竞态只回放最新结果、选中回填不触发搜索、非基金类型不发请求。
    - 落地范围：后端 `test_investmentLedgerFundSearch.py` 覆盖故障收敛/基金过滤/字段长度边界（9 例）；前端 `FundSearchController.test.ts` 覆盖防抖/竞态/异常收敛/销毁（6 例），`FundSearchResults/index.test.tsx` 覆盖加载/空态/结果列表与选中交互（3 例）。
    - _Requirements: 5.1-5.8_
  - [x] 16.5 执行类型检查、构建与一次性自动化测试
    - 运行 `npm run type-check`、`npm run build:web`、`pytest -q`、`vitest --run`；fake client/fake axios，不访问真实第三方接口；修复失败后保留最终证据。
    - 完成条件：类型检查、构建、后端测试、前端测试全部通过。
    - 验证证据：`tsc --noEmit` 0 错误；`pytest test_investmentLedger{Schemas,RouteBoundary,FundSearch}.py` 17 passed；`vitest --run FundSearchController.test.ts FundSearchResults/index.test.tsx TradeFormModal/index.test.tsx` 11 passed。仓库既有 `ledger.test.ts` / `ledgerSlice.unit.test.ts` / `navigation.unit.test.ts` / `TradeHistoryPanel/index.test.tsx` 共 5 处失败为 `DEFAULT_PAGE_SIZE` 等预先存在问题，与本次改动无关，已通过 `git stash` 比对验证。
    - _Requirements: 5.1-5.8_

## Notes

- 本次将旧的单页 `activeModule`、`switchModule`、`bootstrapLedger`、不变 URL 的 `Radio.Group` 和公开估值写入/直接准备估值记录任务全部改为与设计一致的路由驱动、内部摄取任务；它们不再作为目标实现。
- 估值写入职责只属于 `valuation_ingest`：采集器无数据库访问能力，`ValuationNormalizer` 负责标准化与校验，`ValuationRepository` 负责受控事务、幂等和来源优先级，`CollectorOrchestrator` 负责超时/重试/失败隔离，`cli.py` 负责受控命令触发。
- 13 条正确性属性均有独立测试任务：Property 1→9.4，Property 2→9.6，Property 3→4.2，Property 4→4.7，Property 5→4.7，Property 6→3.2，Property 7→9.4，Property 8→3.4，Property 9→3.6，Property 10→4.4，Property 11→6.4，Property 12→7.3，Property 13→7.4。
- 所有属性测试使用 fake clock/fake collector/fake repository 或临时 SQLite，不访问天天基金网等真实外部服务；金额、比率和来源优先级断言不得使用浮点近似替代 Decimal/确定性比较。
- 任务中的文件路径、类名和接口名来自当前设计；实现时优先迁移/复用现有代码，新增样式必须使用 `*.module.scss`，不得使用 `style={{...}}`。

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.3", "9.5"] },
    { "id": 1, "tasks": ["1.5", "4.5"] },
    { "id": 2, "tasks": ["6.1", "10.2", "11.2"] },
    { "id": 3, "tasks": ["6.2", "10.3", "11.3"] },
    { "id": 4, "tasks": ["6.3", "6.5", "8.1", "12.1"] },
    { "id": 5, "tasks": ["6.4", "7.1", "12.2"] },
    { "id": 6, "tasks": ["7.2", "9.6"] },
    { "id": 7, "tasks": ["7.3", "7.4", "7.5", "8.3", "11.4", "12.3"] },
    { "id": 8, "tasks": ["7.6", "12.4", "13.1"] },
    { "id": 9, "tasks": ["13.2"] },
    { "id": 10, "tasks": ["13.3"] },
    { "id": 11, "tasks": ["16.1", "16.2"] },
    { "id": 12, "tasks": ["16.3"] },
    { "id": 13, "tasks": ["16.4"] },
    { "id": 14, "tasks": ["16.5"] }
  ]
}
```
