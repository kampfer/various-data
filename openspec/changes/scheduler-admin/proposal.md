# Proposal

## Why

调度器把运行状态全部落在 `data/scheduler.db`，但目前只能靠 `sqlite3` 手写 SQL 和 `log/scheduler.log` 观察：待执行队列、重试计划、补跑水位、失败原因都不可见；「立即执行」只能停服后用 `--run-once` 单跑一次，日常运维成本高且容易误操作。

需要一个跟调度进程同生共死、成本极低的内部管理页面：能看到常用状态，能完成最常见的四个动作，不需要额外服务、额外数据库或前端状态管理框架。

## What Changes

- 新增独立的管理 API 包 `src/backend/admin/`：FastAPI 应用 + 线程内 uvicorn，由 `src/backend/scheduler/main.py` 在调度器启动前拉起；默认监听 `127.0.0.1:8787`，提供 `--no-admin` 关闭、`--admin-host` / `--admin-port` 调整。
- 新增只读接口：运行概览、任务注册表（含下次触发与水位）、运行记录分页与详情、日志尾部。
- 新增四个写操作：立即执行任务、重试失败记录、取消待执行记录、按天数清理历史记录。
- 账本语义扩展（`TEXT` 字段，不改表结构）：
  - `trigger_kind` 增加 `manual`，手动执行与自动触发共用同一条入账、执行、重试、告警路径；
  - `status` 增加 `cancelled` 终态，只有 `pending` / `interrupted` 可被取消；
  - 历史清理的删除范围覆盖 `cancelled`。
- 新增 React 18 + antd 5 单页管理界面（不使用 redux）：概览、任务、运行记录、日志四个 Tab，采用定时轮询刷新；静态资源由同一 FastAPI 进程托管。
- 前端完全自包含：源码、`package.json`、webpack 配置与 tsconfig 全部放在 `src/frontEnd/`，构建产物为 `src/frontEnd/dist/`，与旧 `src/web/**`、`scripts/webpack.*` 无任何依赖关系。
- 静态资源未构建时，API 仍可用，根路径返回 503 与构建提示，不影响调度器启动。
- 不修改 `src/web/backEnd/**`，不修改任何任务的抓取或写入实现。
- 不做登录鉴权，通过仅绑定回环地址限制访问面；远程访问依赖 SSH 隧道或反向代理。

## Capabilities

### New Capabilities

- `scheduler-admin`: 调度器的进程内后台管理界面与其 REST 接口，覆盖运行状态展示、手动执行、失败重试、待执行取消与历史清理，以及这些操作对运行账本状态的约束。

### Modified Capabilities

无。项目主 `openspec/specs/` 目前为空（`scheduler-fault-tolerance` 尚未归档），因此本变更对 `task-scheduling` 的增量（`manual` 触发类型、`cancelled` 终态）以 ADDED requirement 的形式落在新能力 `scheduler-admin` 中，待旧变更归档后再由后续变更收敛。

## Impact

- 新增：`src/backend/admin/**`（管理 API：`api.py`、`server.py`）、`src/frontEnd/**`（自包含 React 应用：`package.json`、webpack 配置、tsconfig、页面源码）、产物目录 `src/frontEnd/dist/`。
- 修改：`src/backend/scheduler/main.py`（装配管理服务与优雅退出）、`src/backend/scheduler/store.py`（查询、取消、重试、统计与清理范围）、`src/backend/scheduler/config.py`（管理服务配置与产物路径）、`src/backend/scheduler/README.md`、`.gitignore`；`src/backend/pyproject.toml` 增加 pytest 路径配置与测试所需的 dev 依赖 `httpx2`。
- 依赖：不新增运行时依赖，复用已有的 `fastapi`、`uvicorn`、`react`、`antd`、`axios`、`dayjs`；前端依赖安装在 `src/frontEnd/node_modules`，不影响仓库根目录。
- 数据：只读写调度账本；`job_run` / `job_state` 表结构不变，仅新增两个枚举取值。不读取业务库。
- 部署：systemd 单元与启动命令不变；生产默认只监听回环地址，是否需要对外暴露单独评估。
- 风险：管理服务与调度器同进程，调度进程退出时页面同时不可用；新增 `cancelled` 状态后，任何依赖状态全集的查询（清理、统计）都必须同步覆盖。
