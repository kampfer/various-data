# Proposal

## Why

`src/web/backEnd/app/tasks` 下的抓取与备份任务目前由 APScheduler 在 `scheduler_service.py` 中以线程方式调度：没有运行历史、没有失败重试、失败后只能翻 `log/various_data.log`；`crawlOMO` 解析失败只写日志，任务永远"成功"结束。

同时，这批任务代码需要迁移到新的编排体系下，且后续还有脚本要陆续迁移。需求是：**用目录隔离，爬虫代码一并迁移，新实现不引用旧代码**，旧代码在交接期内保持原样。这样迁移不依赖对既有任务代码的改动，也不会阻塞后续的逐个迁移。

## What Changes

- 新增自包含目录 `src/dagu/`：
  - `dags/`：编排定义
  - `tasks/`：迁移后的爬虫与备份实现（OMO 抓取与解析、新浪快讯抓取、数据库备份）
  - `lib/`：数据库路径解析、连接与建表、SQL 语句
  - `.env.example`、`README.md`
- 新实现**不导入 `src/web/backEnd/app` 下的任何模块**：数据库路径、表结构、SQL、日志输出全部自带；只用标准库 `sqlite3` 与仓库已有依赖 `requests`、`pyquery`。
- **表结构归属变更**：本次迁移完成后，新目录的建表与 SQL 是表结构的唯一演进位置；后续新增字段只在新代码定义，旧 `app/*/models.py` 冻结在迁移时的结构，旧爬虫与旧调度进程停用（文件暂留）。
- 三个 DAG 接管现有三个定时任务（每小时 / 每天 12:00 / 每月 1 日），并获得运行历史、手动触发、失败重试与邮件告警。
- 迁移时顺带修掉两个已知限制：
  - 上游请求加超时并校验 HTTP 状态码，避免卡死并让失败可感知。
  - 发现新公告却解析不出任何记录时以非零退出码结束（不再"静默成功"）。
- **旧代码零改动**：`src/web/backEnd/app/**`、`scheduler_service.py`、`main.py`、`Pipfile`、`package.json`、`start.sh` 均不修改；交接期内新旧实现并存，旧实现不再被调度。
- 生产环境切换方式为**停用不删除**：停止并 disable `scheduler_service`，启用 Dagu；回滚即重新启动该服务。
- 后续迁移约定：每接入一个任务，只新增 `tasks/` 下的一个实现与 `dags/` 下的一个定义，不改动已接入的任务。
- 不纳入：`pickStock.py`（未注册调度的调试脚本）、FastAPI 业务代码、前端、`email2.py`。

## Capabilities

### New Capabilities

- `task-orchestration`: 定时任务的声明式编排，包括 DAG 定义、cron 调度、串行保护、失败重试、退出码语义、开发/生产环境隔离，以及既有实现的保留与增量化接入方式。
- `task-observability`: 任务运行的可见性，包括运行历史、手动触发、仅本机可访问的 Web UI，以及失败时的邮件告警。
- `database-backup`: 数据库备份行为，包括备份周期、备份文件命名，以及备份快照与并发写入的一致性保证。

### Modified Capabilities

无。项目尚无既有 spec。

## Impact

- 新增：`src/dagu/**`（自带建表逻辑，结构与既有模型完全一致，并由一次性一致性校验保证）、部署侧 Dagu systemd 单元。
- 不修改：`src/web/backEnd/**`、`Pipfile`、`package.json`、`start.sh`。
- 依赖：Python 依赖不变（不移除 `apscheduler`）；新增外部二进制 Dagu（固定版本）。
- 运行环境：生产需安装 Dagu、设置 `TZ=Asia/Shanghai`，并以宿主机环境变量提供 `mode=pro`；开发同一套 DAG 配 `mode=dev`。
- 数据：`data/various_data.db` 由新进程直接写入，表结构与 Web 端模型保持一致；备份产物路径不变（`backup/<源库名>_YYYYMMDD.db`）。
- 表结构归属：迁移时做一次性基线对齐，之后新增字段只在新目录定义；Web 端在自身迁移前只能读到既有字段。
- 已知风险：新目录用 `CREATE TABLE IF NOT EXISTS` 只补建缺失的表，已在生产库中新增字段需要配套 `ALTER` 语句。
