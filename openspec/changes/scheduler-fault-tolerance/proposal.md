# Proposal

## Why

现有定时任务由 APScheduler 在 `scheduler_service.py` 中以内存任务存储运行：没有运行记录、没有重试、失败只写日志，且默认的 1 秒 misfire 窗口、`coalesce=False`、`max_instances=3` 会让延迟、停机、重叠三种情况下的触发被静默丢弃或并发重复执行。同时 `app/tasks` 的抓取实现没有请求超时，"有新公告却解析为空"也会静默成功。

需求是：把调度层改造成**资源占用低、可审计、不跳过任务**的爬虫调度器——失败要重试并及时邮件告警，触发可以延后但不能消失。既有代码作为快照冻结，不再修改。

## What Changes

- 新增自包含目录 `src/scheduler/`，不导入 `app.*`：
  - `main.py`：唯一常驻进程入口，替代 `scheduler_service.py` 的启动方式
  - `registry.py`：任务注册（cron、`catchup` 属性、重试参数）
  - `store.py`、`runner.py`、`catchup.py`、`alert.py`：运行账本、单线程消费者、启动补账、邮件告警
  - `tasks/`：重写 OMO 抓取、新浪快讯、数据库备份三个任务
  - `lib/`：数据库路径、建表与写入语句、日志
  - `config.local.example.yaml`：SMTP 与运行参数样例，真实配置不提交
- 触发与执行解耦：APScheduler 只负责到点向 `data/scheduler.db` 的 `job_run` 表写入待执行记录，单线程消费者串行执行。`misfire_grace_time=None`，延迟多久都入账；同一任务同一时刻只有一个实例。
- 启动补账：进程恢复时对比 `job_state` 水位，补跑停机期间错过的触发；`catchup=backfill` 合并为一次补跑，`catchup=none` 标记 `lost` 并立即告警。
- 失败重试：固定次数、可配置间隔；重试状态持久化，进程重启不丢。崩溃遗留的 `running` 记录在启动时标记为 `interrupted` 并重新排队。
- 邮件告警按任务类型分级：`catchup=none` 每次执行失败立即发；`catchup=backfill` 重试耗尽后发最终失败。
- 重写的任务补齐旧实现缺失的失败判定：请求超时与状态码校验、发现新公告却解析为空时判失败、备份临时文件 + 原子替换 + 完整性自检。
- **BREAKING**：生产切换方式为停用不删除——停止 `scheduler_service`，改为启动新入口；旧文件、旧 npm 脚本保留但不调度。
- 不修改 `src/web/backEnd/**` 的任何文件；旧的 `app/tasks`、`app/scheduler.py`、`scheduler_service.py` 作为冻结快照保留。
- Dagu 编排方案已废弃：其实现代码、变更记录与失效脚本已删除；本变更采用 APScheduler + SQLite 账本重新实现调度层。

## Capabilities

### New Capabilities

- `task-scheduling`: 周期性任务的触发、串行执行、运行账本、错过触发的补跑、时区与环境隔离。
- `task-failure-handling`: 执行失败后的固定次数重试、崩溃恢复，以及按任务可补属性分级的邮件告警。
- `crawler-ingestion`: 新浪快讯与央行公开市场公告的抓取、解析与入库行为，包括超时、状态码校验与解析失败判定。
- `database-backup`: 数据库备份的周期、命名、快照一致性与完整性自检。

### Modified Capabilities

无。项目尚无既有 spec。

## Impact

- 新增：`src/scheduler/**`、`data/scheduler.db`（调度账本，与业务库分离）。
- 不修改：`src/web/backEnd/**`；依赖与启动脚本已切换到 uv（`pyproject.toml` + `uv.lock`），旧调度入口停用但不删除。
- 依赖：不新增第三方包，复用已有的 `apscheduler`、`requests`、`pyquery`；`tzdata` 已列为核心依赖，Windows 下可用 `Asia/Shanghai`。
- 数据：业务库 `data/various_data.db`（生产）/ `various_data_dev.db`（开发）仍由任务写入；表结构基线由新目录的 DDL 保证与冻结模型一致，此后新增字段只在新目录演进。
- 部署：生产由 systemd 托管新入口（`Restart=always`），启动时输出一条补账摘要；不引入外部心跳服务。
- 风险：切换瞬间新旧调度进程并存会重复抓取，必须先停旧再启新；回滚即重新启动旧服务。
