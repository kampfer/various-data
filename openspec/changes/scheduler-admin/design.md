# Design

## Context

动机与范围见 [proposal.md](./proposal.md)。实现前需要知道的现状与约束：

- 调度器是单进程：`main.py` 在主线程跑 `BlockingScheduler`，`Runner` 在守护线程里串行执行，所有状态落在 `data/scheduler.db` 的 `job_run` / `job_state`。
- `Store` 每次操作新开一条 SQLite 连接（`busy_timeout=5000`），因此不同线程并发调用是安全的，不需要连接池或额外的锁。
- 消费循环最多等待 30 秒；`Runner.wake()` 可以立即打断等待。这是「立即执行」能做到秒级生效的前提。
- `src/web/backEnd/**` 是冻结区：README 与本仓库既有变更都明确不导入、不修改，因此管理接口不能挂在现有 Web 应用上。
- `fastapi`、`uvicorn`、`react`、`antd`、`axios`、`dayjs` 都已是现有依赖，本变更不新增运行时依赖；测试额外使用 dev 依赖 `httpx2`（Starlette 的 `TestClient` 要求）。
- 现有前端构建由 `scripts/webpack.config.js` 输出到 `dist/web`，`package.json` 使用 ESM，根 `tsconfig.json` 当前只纳入 `src/web/frontEnd/src/**/*`；本变更不复用这些配置，前端依赖改为安装在 `src/frontEnd`。
- 仓库此前没有 `tests/` 目录；本变更新建 `tests/`，并在 `pyproject.toml` 配置 `pythonpath = ["src"]`。

## Goals / Non-Goals

**Goals:**

- 管理服务与调度器共享同一个 `Store` 与 `Runner` 实例，写操作不依赖跨进程通知或轮询等待。
- 接口契约稳定、可被 `TestClient` 独立测试，不需要启动真实 uvicorn 或真实调度循环。
- 前端零全局状态库、零前端路由库，单页四区，轮询即可满足刷新需求。
- 构建链路与现有 `dist/web` 完全隔离，互不清理、互不覆盖。

**Non-Goals:**

- 不做登录、会话、权限与操作审计人维度。
- 不做 WebSocket / SSE 实时推送、历史指标图表、任务暂停恢复。
- 不读取业务库，不展示快讯或 OMO 数据。
- 不支持多调度进程或多实例共享同一管理端口。
- 不改动任何任务的抓取、解析与写入实现。

## Decisions

### 1. 管理服务以守护线程内嵌，而不是独立进程

`main.py` 启动顺序改为：`Runner.start()` → 管理服务线程 → `scheduler.start()`。

```
main()
  ├── Runner.start()                执行线程
  ├── AdminServer.start()           uvicorn.Server 在 daemon 线程里 run()
  ├── scheduler.start()             主线程阻塞
  └── finally
        ├── scheduler.shutdown(wait=False)
        ├── runner.stop()
        └── admin.stop()            server.should_exit = True; thread.join()
```

替代方案：

- **独立 `admin_server.py` 进程**：隔离更好，但 SQLite 无法通知另一个进程的 `Runner`，「立即执行」最坏要等 30 秒轮询，且需要保证两个进程使用同一个 `--mode`。
- **挂到现有 Web 后端**：冻结区不允许改动，且调度器自包含的设计初衷就是不依赖 Web 代码。

嵌入式还带来一个实际好处：`Runner.wake()` 是内存中的条件变量通知，只有同进程才能做到真正即时。

### 2. 启动参数与配置

在 `config.py` 增加 `AdminSettings`（`enabled`、`host`、`port`），由 `main.py` 的参数解析覆盖默认值：

| 参数 | 默认 | 说明 |
| --- | --- | --- |
| `--no-admin` | 不传，即启用 | 关闭管理服务 |
| `--admin-host` | `127.0.0.1` | 非回环地址时启动日志告警 |
| `--admin-port` | `8787` | 与业务 Web 的 8000 错开 |

端口占用时 `uvicorn.Server` 会启动失败；捕获异常后记录明确日志并让进程以非零码退出，避免「调度器在跑但页面永远连不上」的隐形故障。

### 3. Store 只加方法，不改表结构

`status` 与 `trigger_kind` 都是无约束的 `TEXT`，新增 `cancelled` 与 `manual` 不需要 DDL 变更，也不会影响已有数据。新增方法：

```
list_runs(job_id, status, page, page_size) -> (total, rows)
get_run(run_id) -> dict | None
overview_stats(today_start) -> {pending, retrying, success_today, failed_today}
enqueue_manual(job_id, at, max_attempts) -> (created: bool, run_id: int | None)
requeue_failed(run_id, at) -> bool
cancel_pending(run_id, at) -> bool
```

`cleanup()` 的删除条件从 `status IN ('success','lost') OR (failed 且无 next_retry_at)` 扩展为再并上 `cancelled`；`pending` / `running` / `interrupted` / 待重试的 `failed` 一律保留。

替代方案：用 SQLAlchemy 或新建 `job_action_log` 表记录操作。前者引入重依赖，后者超出「简易」范围；操作结果本身已经体现在记录状态上。

### 4. 立即执行 = 入账 + 唤醒，不直接调用任务函数

手动执行走 `enqueue_manual()` 写入 `trigger_kind=manual`、`status=pending`、`scheduled_at=now` 的记录，然后 `runner.wake()`。

为什么不像 `--run-once` 那样直接 `spec.func()`：直调会绕过重试、告警、审计和串行约束，容易出现「页面手动跑一次，正好与 cron 执行撞车」的并发写库。入账方式让手动执行与自动触发共用同一条路径。

两个必须处理的细节：

- `UNIQUE(job_id, scheduled_at)` 在秒级时间上会合并同一秒内的重复提交，接口据此返回 `created=false`，页面提示「已存在」。
- 手动入账**不调用** `advance_state()`，水位只由计划触发推进，否则会破坏补账语义。

### 5. 手动重试复用原记录，并只补一次尝试

`requeue_failed()` 只对 `status='failed'` 生效，执行：

```
status = 'pending', next_retry_at = NULL, finished_at = NULL, error = NULL,
attempt = max_attempts - 1
```

`claim_next()` 领取时会把 `attempt` 加 1，因此人工重试恰好得到一次新尝试；如果这次仍失败，`attempt == max_attempts`，直接回到终态失败。

替代方案：

- **只把 `next_retry_at` 设为当前时间**：`attempt` 可能已经等于 `max_attempts`，领取后会变成超限值，失败判定与展示都会错位。
- **新建一条 manual 记录**：审计历史更干净，但用户点的是「重试这条失败记录」，新记录与源记录失去关联，页面上无法形成因果链。

代价是 `attempt` 被回写，历史尝试次数不再单调递增。这是刻意取舍，写进 README 的运行账本说明里。

### 6. 取消是终态，不是删除

`cancel_pending()` 只对 `pending` / `interrupted` 生效，置为 `cancelled`，`finished_at` 写当前时间，`error` 为空时补「手动取消」。

不物理删除的原因：删除后无法回答「这条计划触发去哪了」；而 `pending` 消失与「从未产生」在账本上无法区分。`cancelled` 作为终态还能被统一的历史清理回收。

### 7. API 契约

统一前缀 `/api`，全部返回 JSON；时间为 ISO8601 字符串（带 `+08:00`），前端用 dayjs 格式化。

```
GET  /api/overview                      概览指标
GET  /api/jobs                          注册表 + 下次触发 + 水位 + 最近一次结果
GET  /api/runs?job_id=&status=&page=&page_size=
GET  /api/runs/{id}                     详情（error / alerted_at / alert_error）
GET  /api/logs?lines=200                日志尾部（上限 2000）
POST /api/jobs/{id}/run                 立即执行
POST /api/runs/{id}/retry               重试失败记录
POST /api/runs/{id}/cancel              取消待执行
POST /api/runs/cleanup                   {days: int}
```

约定：

- `page_size` 默认 20、上限 200；`lines` 上限 2000，超出按上限截断并在响应里返回实际行数。
- 状态不允许的操作返回 409，任务不存在返回 404，参数非法返回 422。
- 日志读取按「从文件尾部向前读固定块」实现，不整文件读入；文件不存在时返回空列表与提示，不报 500。
- 「下次触发时间」由 `spec.build_trigger().get_next_fire_time(None, now)` 计算，不读 `scheduler.get_jobs()`，从而不与管理线程共享 APScheduler 内部状态。

### 8. 前端结构与刷新

React 18 + antd 5 + axios，单页四个 Tab：概览、任务、运行记录、日志。不使用 redux 与 react-router：

- 每个 Tab 自己持有状态，用 `useEffect` + `setInterval` 轮询（概览 5s、运行记录 10s、日志默认关闭自动刷新）。
- 写操作成功后用 `message` 提示并立刻重新拉取当前 Tab 数据，不依赖轮询间隔。
- 运行记录用 antd `Table` 的服务端分页，筛选条件放在受控状态里。
- 错误详情用 `Drawer`，清理历史用 `Modal` + `InputNumber` 二次确认。

不引入 redux 的理由：状态只存在于单个 Tab 内，跨 Tab 没有共享需求；引入全局状态只会增加样板代码。

### 9. 前端自包含在 `src/frontEnd`

```
src/backend/pyproject.toml               后端依赖清单（uv 项目根）
src/backend/admin/                       管理 API（api.py / server.py）
src/backend/scheduler/                   调度器
src/frontEnd/package.json                前端自己的依赖与脚本
src/frontEnd/webpack.config.js           生产：产物 src/frontEnd/dist
src/frontEnd/webpack.dev.config.js       开发：3001 端口，/api 代理到 127.0.0.1:8787
src/frontEnd/tsconfig.json               独立类型检查配置
src/frontEnd/src/                        React 源码（main.tsx + pages/**）
```

- 新代码与旧 `src/web/**` 在目录上彻底分开：不引用 `scripts/webpack.*`、不修改根 `tsconfig.json`、不共享根 `node_modules`。
- 前端依赖通过 `src/frontEnd/package.json` 安装到该目录自己的 `node_modules`，旧代码后续删除或迁移时互不影响。
- `CleanWebpackPlugin` 只清理 `src/frontEnd/dist`，不会误删 `dist/web`。
- 开发态依赖 webpack proxy，因此后端不需要配置 CORS。
- 前端单页无前端路由，`StaticFiles(html=True)` 即可，不需要 history fallback。

### 10. 静态资源缺失的降级

启动时检查 `src/frontEnd/dist/index.html`：

- 存在：`app.mount("/", StaticFiles(directory=..., html=True))`。
- 不存在：注册一个根路由返回 503 与「在 `src/frontEnd` 执行 `npm run build`」提示，同时打一条 warning 日志。API 路由不受影响。

这样「先部署后端、后补前端构建」不会让调度器启动失败。

### 11. 测试策略

- `Store` 新方法用 `tmp_path` 建临时账本直接单测：入账去重、重试的 `attempt` 上限、取消的状态约束、清理的状态边界。
- API 用 `fastapi.testclient.TestClient` 注入临时账本与假 `Runner`（只记录 `wake()` 调用），覆盖 404/409/422 与正常路径，不启动 uvicorn。
- 前端不引入测试框架，靠 `src/frontEnd` 内的 `npm run build` 与 `npm run type-check` 保证可构建、类型通过；后端测试需要 `httpx2`，已加入 dev 依赖组。

## Risks / Trade-offs

- [调度进程即 Web 进程] 调度崩溃时页面同时不可用 → systemd `Restart=always` 会在 10 秒内拉起，页面随之恢复；不需要额外补偿。
- [端口被占用导致进程退出] 可能被误判为调度故障 → 启动日志明确区分「管理端口占用」与「调度异常」，README 记录排查命令。
- [账本并发写] API 写操作与消费者、调度回调同时写 SQLite → 每操作独立连接 + `busy_timeout=5000`；写事务都是单条 UPDATE/INSERT，持锁时间在毫秒级。
- [manual 与 cron 同秒冲突] 立即执行恰好落在 cron 触发那一秒时，`UNIQUE` 会去重 → 返回「已存在」，用户看到的是提示而非静默失败；不影响已入账的自动触发。
- [人工重试回写 attempt] 历史尝试次数不再单调 → 在 README 的运行账本说明中明确该语义；如后续需要严格审计，再增加操作记录表。
- [日志文件读竞争] Windows 下日志文件可能被写入进程占用 → 以只读方式打开并捕获 `OSError`，失败时返回空内容与提示，不让接口 500。
- [无鉴权] 任何能访问该端口的人都能触发任务与清理历史 → 默认只绑定回环地址；改绑定地址时启动日志告警；远程访问要求走 SSH 隧道或反向代理。
- [新状态遗漏] `cancelled` 若未纳入某个查询，统计或清理会出现偏差 → 状态取值集中为 `store.py` 中的常量元组，查询与清理都引用同一处；新增测试覆盖清理边界。
- [前端构建未纳入部署流程] 部署后只看到 503 → 503 文案直接给出构建命令；README 的部署小节把构建列为前置步骤。

## Migration Plan

1. 在 `src/frontEnd` 执行 `npm install && npm run build` 生成产物，以 `--mode dev` 启动调度器，确认概览、任务、运行记录、日志四个区域都有数据。
2. 依次验证四个写操作：立即执行后账本新增 `manual` 记录并被消费；失败记录重试后只多一次尝试；`pending` 记录取消后不再被领取；清理只删除超期终态记录。
3. 关闭管理服务启动（`--no-admin`），确认调度行为与变更前一致。
4. 部署到生产：先构建前端，再重启 systemd 服务；仅在需要远程访问时修改监听地址，并确认存在隧道或代理。
5. 回滚：直接以 `--no-admin` 启动即可关闭入口；账本新增的两个枚举值对旧代码无副作用，无需数据回滚。

## Open Questions

- 是否需要在账本中显式标记「该次重试由人工触发」。当前不新增字段，只体现在日志与 `attempt` 变化上；若后续需要严格的审计链，可单独增加操作记录表，不影响本设计的接口契约。
