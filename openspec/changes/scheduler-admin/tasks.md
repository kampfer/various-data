# Tasks

## 1. 进程骨架与配置

- [x] 1.1 在 `config.py` 增加 `AdminSettings`（`enabled` / `host` / `port`，默认关闭为 false、`127.0.0.1`、`8787` 的反向默认即启用），并在 `main.py` 增加 `--no-admin`、`--admin-host`、`--admin-port`；验证：`uv run --project src/backend python src/backend/scheduler/main.py --help` 能列出三个参数，`describe_config()` 输出管理服务地址
- [x] 1.2 新建 `src/backend/admin/api.py`，先提供最小应用与 `GET /api/health`，用构造函数注入 `Store`、`Runner`、注册表与日志路径，不读取全局状态；验证：`fastapi.testclient.TestClient` 请求 `/api/health` 返回 200
- [x] 1.3 新建 `src/backend/admin/server.py`，封装 `uvicorn.Server` 的启动、`should_exit` 停止与线程 join，并区分「端口占用」与「应用异常」两类错误；验证：单元测试用随机空闲端口启动后停止，线程不残留
- [x] 1.4 修改 `main.py` 的启动与退出顺序为 `Runner.start()` → 管理服务 → `scheduler.start()`，`finally` 中依次停止调度器、消费者、管理服务；验证：`--mode dev` 启动顺序由单测断言，管理服务真实启动后 `/api/health` 与页面可访问
- [x] 1.5 验证管理服务的开关与异常路径；验证：`--no-admin` 时不会构造管理服务（单测断言），端口被占用时抛出 `kind=port` 的错误并以非零码退出

## 2. 账本查询与写操作

- [x] 2.1 在 `store.py` 集中定义状态与触发类型常量，并实现 `list_runs`、`get_run`、`overview_stats`；验证：`pytest` 覆盖分页总数、筛选条件与当日统计（用 `tmp_path` 临时账本）
- [x] 2.2 实现 `enqueue_manual`：写入 `trigger_kind='manual'` 的 `pending` 记录，重复秒级提交返回 `created=False`，且不调用 `advance_state`；验证：测试断言重复提交只有一条记录、`job_state` 水位不变
- [x] 2.3 实现 `requeue_failed`：仅 `failed` 可重试，回写 `attempt = max_attempts - 1` 并清空 `next_retry_at` / `finished_at` / `error`；验证：测试断言重试后领取的 `attempt` 等于 `max_attempts`，非 `failed` 记录返回 False 且状态不变
- [x] 2.4 实现 `cancel_pending`（仅 `pending` / `interrupted` → `cancelled`）并扩展 `cleanup` 的删除范围包含 `cancelled`；验证：测试断言 `running` 不可取消、超期的 `cancelled` 被清理、未完成与待重试记录被保留

## 3. API 层

- [x] 3.1 实现只读接口 `GET /api/overview`、`/api/jobs`、`/api/runs`、`/api/runs/{id}`，下次触发时间用 `spec.build_trigger().get_next_fire_time(None, now)` 计算；验证：`TestClient` 断言字段完整、`page_size` 上限 200 生效、未知记录返回 404
- [x] 3.2 实现写操作接口 `POST /api/jobs/{id}/run`、`POST /api/runs/{id}/retry`、`POST /api/runs/{id}/cancel`、`POST /api/runs/cleanup`，写成功后调用 `runner.wake()`；验证：`TestClient` 覆盖 404（未知任务）、409（状态不允许）、422（天数非法）与正常返回
- [x] 3.3 实现 `GET /api/logs`：从文件尾部按块读取，行数上限 2000 且响应返回实际行数，文件不存在或读取失败时返回空内容与提示；验证：测试用大日志文件断言只读尾部、超限截断、缺失文件不返回 500
- [x] 3.4 实现静态资源托管：构建产物存在时挂载 `StaticFiles(html=True)`，不存在时根路径返回 503 与构建提示，同时记录 warning 日志；验证：分别在有/无产物目录时请求 `/` 与 `/api/health`，页面与接口行为符合规格
- [x] 3.5 补齐 API 层测试；验证：`uv run pytest` 全部通过，且测试不启动真实 uvicorn、不触碰业务库文件

## 4. 前端

- [x] 4.1 在 `src/frontEnd/` 内新增自包含的 `package.json`、`webpack.config.js`、`webpack.dev.config.js` 与 `tsconfig.json`（3001 端口、`/api` 代理到 8787），产物输出 `src/frontEnd/dist`；验证：在该目录执行 `npm install && npm run build` 生成产物，根目录旧 `src/web` 与 `scripts/` 未被改动
- [x] 4.2 搭建页面骨架（`ConfigProvider` 中文语言包 + 四个 Tab）与 axios 客户端，完成概览 Tab 与 5 秒轮询；验证：`npm run dev` 下概览指标与 `/api/overview` 返回一致
- [x] 4.3 实现任务 Tab：展示 cron、可补属性、重试参数、下次触发、水位、最近一次结果，并提供「立即执行」二次确认；验证：点击后出现成功提示，运行记录 Tab 出现 `manual` 记录
- [x] 4.4 实现运行记录 Tab：服务端分页、按任务与状态筛选、错误详情 Drawer、行内「重试」与「取消」、顶部清理历史 Modal；验证：四种操作的结果与账本状态一致，不允许的状态不显示对应按钮
- [x] 4.5 实现日志 Tab：展示尾部内容、可调行数、手动刷新与自动刷新开关；验证：日志内容随 `log/scheduler.log` 追加而更新
- [x] 4.6 运行类型检查；验证：在 `src/frontEnd` 内执行 `npm run type-check` 通过，无类型错误

## 5. 文档与集成验证

- [x] 5.1 更新 `src/backend/scheduler/README.md`：新增管理服务的启动参数、前端构建与开发命令、端口与访问范围说明，并在运行账本小节补充 `manual` 与 `cancelled` 的语义；验证：按文档从零执行 `npm install && npm run build` 与启动命令能打开页面
- [x] 5.2 端到端验证四个操作：立即执行、失败重试、取消待执行、按天清理；验证：真实 HTTP 调用依次返回 `manual` 入队、`attempt 2/3`、`cancelled`、`removed=1`，账本状态与设计一致
- [x] 5.3 回归验证管理服务不影响调度内核；验证：`--no-admin` 不构造管理服务的装配测试通过，`git status` 显示 `src/web/backEnd/**` 无改动

## Workflow follow-up

- 本变更实施并通过评审后执行归档，确认 `openspec/specs/` 下新增 `scheduler-admin` 能力规格。
- 归档顺序：先归档 `scheduler-fault-tolerance`，再归档本变更，避免主规格叠加冲突。
