# Design

## Context

动机与范围见 [proposal.md](./proposal.md)。实现前需要了解的现状与约束：

- 现有调度为 `scheduler_service.py` 中的 `BlockingScheduler` + 内存任务存储，任务注册方式是扫描 `app/tasks` 目录并调用各模块的 `addJob(scheduler)`。
- 现有 `job_defaults` 为 `coalesce=False`、`max_instances=3`（`app/scheduler.py`），任务未声明 `misfire_grace_time`，即沿用默认 1 秒；延迟超过 1 秒的触发会被直接丢弃，前次未结束时最多允许 3 个并发实例。
- 现有任务实现依赖 `app.database`、`app.logger`、`app.omo.crud`、`app.sinaFinanceNews.*`，且 `crawlOMO.py`、`crawlSinaNews.py` 的 `requests.get` 没有超时与状态码校验，"有新公告但解析为空"只写日志、任务仍以成功结束。
- `app/email2.py` 内置硬编码的 SMTP 账号与授权码，未被调度器使用。
- 本次 `src/web/backEnd/**` 全部冻结，不修改、不删除；旧调度入口停用但不移除。
- 生产为 Linux（`start.sh` 用 `nohup uvicorn`），开发机为 Windows，两处共享同一仓库；`tzdata` 已列为核心依赖，Windows 下可用 IANA 时区。
- 三个任务均为"读上游、写 SQLite"的短时批处理，彼此无数据依赖，周期分别为 1 小时、每天 12:00、每月 1 日。

## Goals / Non-Goals

**Goals:**

- 触发与执行解耦，使"延迟、停机、重叠、失败"四种情况都不会让一次计划触发静默消失。
- 运行历史、重试状态、补跑水位全部落库，进程重启后状态不丢。
- 单进程、单线程消费者，无额外服务、无轮询空转，资源占用与现有调度器同一量级。
- 新实现完全自包含，不依赖也不修改冻结的 Web 代码。
- 为"未来不可回溯的任务"预留注册属性，而不是写死告警逻辑。

**Non-Goals:**

- 不改 Web 后端、前端、`pyproject.toml`、`package.json`、`start.sh`。
- 不引入 Dagu、Airflow 等外部编排引擎或常驻 Web UI。
- 不做分布式调度、跨主机抢占、任务依赖编排。
- 不迁移 `pickStock.py` 等未注册调度的调试脚本。
- 不提供外部心跳监控（如 healthchecks.io）。
- 不修复冻结代码中的历史数据问题（如旧实现把"十月"解析成 1 月的脏数据）。

## Decisions

### 1. 回归 APScheduler，但只把它当作"闹钟"

本次需求要求单进程、低资源、无额外二进制。APScheduler 已经是既有依赖，用它负责 cron 到点即可；"不跳过"所需的运行记录、重试、补跑由我们自己的 SQLite 账本承担。

替代方案与放弃原因：

- 继续沿用现状只补参数（`misfire_grace_time=None` 等）：停机期间的触发仍然永久丢失，且没有重试与告警。
- Dagu：需要额外二进制、独立数据目录与配置体系，与"资源占用低、单进程"冲突。
- 系统 cron + 脚本：没有运行账本、没有自动重试与补跑，失败感知仍薄弱。

### 2. 触发只入队，执行由单线程消费者串行完成

```
APScheduler(cron)  --触发-->  INSERT job_run(pending)  --通知-->  消费者线程
                                                                    |
                                                   执行 tasks/*.py --+--> success
                                                                     +--> failed -> 重试或最终失败
```

- APScheduler 的 job function 只做一次 INSERT + 唤醒消费者，耗时毫秒级，因此不会出现"前次未结束导致实例被丢弃"。
- 执行集中在一个线程，天然满足"同一任务不重叠、不同任务串行"；消费者在没有到期记录时阻塞等待（条件变量 + 超时），不轮询空转。
- 若将来出现长任务，可按任务分组增加消费者，账本模型不需要改。

### 3. 不用 SQLAlchemyJobStore，任务定义留在代码里

- APScheduler 的 jobstore 会在每次启动重算 `next_run_time`，把"停机期间错过了哪几次"这个信息抹掉；用它反而需要另建一份水位。
- 任务清单是静态的、随代码发布，不需要动态增删，放代码里的注册表更可读、可测试。
- 运行历史与任务定义分离：`job_run` 记执行，`job_state` 记水位，`registry.py` 记定义。

### 4. 运行账本放在独立的 `data/scheduler.db`

- 与业务库分离，调度器的写入不会和 Web 读取、爬虫批量写入争抢同一把 SQLite 写锁。
- 备份任务只备份业务库，不会把调度历史一起卷进备份。
- `scheduler.db` 只有调度进程一个写者，使用默认 journal 模式 + `busy_timeout=5000` 足够，不启用 WAL（避免多出 `-wal`/`-shm` 两个文件增加运维认知）。
- 业务库的写入仍由任务用 `timeout=5` 的短事务完成。

表结构（初版）：

```sql
CREATE TABLE IF NOT EXISTS job_run (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id        TEXT    NOT NULL,
  scheduled_at  TEXT    NOT NULL,          -- 计划触发时间，ISO8601 +08:00
  trigger_kind  TEXT    NOT NULL,          -- schedule | catchup | retry
  status        TEXT    NOT NULL,          -- pending | running | success | failed | lost | interrupted
  attempt       INTEGER NOT NULL DEFAULT 0,
  max_attempts  INTEGER NOT NULL,
  missed_count  INTEGER NOT NULL DEFAULT 1,
  next_retry_at TEXT,
  started_at    TEXT,
  finished_at   TEXT,
  error         TEXT,
  alerted_at    TEXT,
  created_at    TEXT    NOT NULL,
  UNIQUE (job_id, scheduled_at)
);

CREATE TABLE IF NOT EXISTS job_state (
  job_id          TEXT PRIMARY KEY,
  last_trigger_at TEXT NOT NULL,           -- 已入账的最近一次计划触发
  updated_at      TEXT NOT NULL
);
```

`UNIQUE (job_id, scheduled_at)` 保证同一触发点不会被重复入账（例如重启后补账与正常触发竞争）。

### 5. 补账算法：水位 + 有界枚举

启动时对每个任务执行一次：

1. 从 `job_state.last_trigger_at` 出发，用该任务的 cron 表达式迭代计算到当前时间为止错过的触发点，枚举上限（如 1000 次）防止水位异常时爆量。
2. **首次启动**（无水位）：把水位初始化为"当前时间之前最近一次触发"，不回放历史。
3. **`catchup=backfill`**：把错过次数合并为一条 `trigger_kind=catchup` 的 `pending` 记录，`scheduled_at` 取最近一次错过的触发点，`missed_count` 记为错过次数。任务本身是增量的，跑一次即可追平。
4. **`catchup=none`**：不补跑，写入一条 `status=lost` 的记录（同样带 `missed_count`），并立即告警——事后执行只会写入当前值，写进账本等于篡改历史。
5. 无论哪种情况，水位都推进到当前时间之前最近一次触发。

补跑与正常触发走同一条执行路径，因此重试、告警、审计逻辑不需要分叉。

### 6. 状态机与重试

```
pending --取出--> running --成功--> success
                    |
                    +--失败且 attempt < max_attempts--> failed --到点--> running
                    |
                    +--失败且 attempt = max_attempts--> failed(终态)
running --启动时发现--> interrupted --> 按剩余次数重新排队或判终态
```

- 重试采用固定次数 + 固定间隔（注册项声明，默认 3 次 / 300 秒），不做指数退避：任务量小，固定间隔更容易预测。
- `attempt` 在执行开始时自增并落库，因此崩溃发生在执行途中也不会"白送"一次尝试。
- 启动时把遗留的 `running` 一律视为 `interrupted`：本设计是单进程串行执行，进程已重启说明上一次执行不再存活。

### 7. 告警由任务属性驱动，而不是代码分支

- `catchup=none`：每次执行失败立即发信（帐本写入 `alerted_at`），因为它没有下一次机会。
- `catchup=backfill`：仅在重试耗尽时发一封最终失败。
- 告警发送使用 `smtplib` + 10 秒超时，在消费者线程内同步发送；发送失败只记日志与 `alerted_at` 不写，绝不改变任务结果。
- 邮件正文包含：任务标识、计划时间、尝试次数、错误摘要、`catchup` 类型；不含任何凭据。
- 凭据读取 `src/scheduler/config.local.yaml`（加入 `.gitignore`），仓库只提交 `config.local.example.yaml`。缺少 SMTP 配置时打印一次警告并降级为"只记日志、不发信"。

### 8. 任务在新目录重写，不引用冻结代码

- `src/scheduler/tasks/*.py` 只依赖标准库与 `requests`、`pyquery`；数据库路径、建表 DDL、写入语句自带。
- 表结构以冻结模型为基线，首次建立时新增 `scripts/check_task_schema.py` 对比 `PRAGMA table_info` 与 `PRAGMA foreign_key_list` 证明一致；此后新增字段只在新目录演进。
- 相比"只读调用 `app/tasks`"：冻结代码无法补超时、无法把"解析为空"判失败，等于放弃容错要求。
- 相比"复用旧目录里的自包含实现"：本次明确选择重写，旧实现只作为行为参考（特别是 OMO 的表格解析规则与历史样本）。

### 9. 重写时补齐的失败判定

- 所有请求设置连接/读取超时（各 30 秒）并校验 2xx；非 2xx 抛错。
- 快讯接口业务状态码非 0 时抛明确异常。
- OMO 发现新公告却解析出 0 条记录时抛错；"没有新公告"仍按成功处理。
- 备份用 `sqlite3.Connection.backup()` 生成一致快照，先写临时文件再 `os.replace` 原子替换，完成后执行 `PRAGMA integrity_check`。
- 日志统一 stdout + `log/scheduler.log`（UTF-8），不接入 `app.logger`，避免与 Web 日志互相污染。

### 10. 时间表达用 cron，不用 interval

原实现中每小时任务用 `interval hours=1`，相位取决于进程启动时刻；改为 `CronTrigger(minute=0)` 后触发点对齐整点，补账算法也能只依赖 cron 表达式推算，不必记录 interval 的锚点。

时区统一为 `ZoneInfo("Asia/Shanghai")`，不依赖宿主机默认时区。

### 11. 进程守护与运行记录清理

- 生产用 systemd 托管新入口，`Restart=always`、`RestartSec=10`；启动时打印一条摘要（补跑条数、丢失条数、待重试条数），崩溃重启后可从日志看出影响面。
- 不引入外部心跳：进程死亡期间的告警缺口由 systemd 重启 + 启动摘要覆盖，接受"主机整体宕机时无人告警"这一残余风险。
- 运行记录保留 90 天：在每次启动补账之后顺带执行一次删除，不额外起定时线程；`lost` 记录同样按 90 天清理，长期留存会在备份归档前被人工检查。

### 12. 目录与入口

```
src/scheduler/
  main.py             入口，解析 --mode，启动服务
  config.py           仓库根、数据库路径、账本路径、SMTP、重试默认值
  registry.py         三个任务的 JobSpec（cron、catchup、重试参数）
  store.py            账本连接、建表、状态查询与更新
  runner.py           单线程消费者、执行、重试
  catchup.py          启动补账与崩溃恢复
  alert.py            SMTP 发送与告警分级
  lib/db.py           业务库建表 DDL 与写入语句
  lib/log.py
  tasks/omo.py
  tasks/sina_news.py
  tasks/db_backup.py
  config.local.example.yaml
```

- 入口方式：`uv run python src/scheduler/main.py --mode dev|pro`；`main.py` 自行把 `src/scheduler` 的父目录加入 `sys.path`，不依赖工作目录与 `PYTHONPATH`。
- 不改 `package.json`：旧 `dev:task` / `start:task` 保留指向旧入口，新入口的启动方式写进 README。

## Risks / Trade-offs

- [重写解析规则回归] 重写 OMO 解析可能丢失边角格式 → 用仓库内 `data/omo/html` 历史样本做覆盖率审计，发现"含操作情况表格却 0 条"即失败；新增 `scripts/check_omo_parser.py` 作为新实现的回归脚本。
- [单线程串行] 一个长任务会推迟其他任务 → 三个任务都是短批处理；重试等待不占用线程，不阻塞其他任务；将来出现长任务再按任务分组增加消费者。
- [不可回溯任务被误标为可补] 接入"只展示最新值"的页面时若忘记声明 `catchup=none`，会写入错误时间的数据 → 注册项强制显式声明，评审时检查；新增任务接入文档中列为必填项。
- [告警风暴] `catchup=none` 每次失败都发信，重试 3 次即 4 封 → 该类型任务的注册项可单独把重试次数调小；后续如仍吵，再在账本层增加按任务的时间窗抑制。
- [切换瞬间重复执行] 新旧调度进程同时存活会各抓一遍 → 迁移步骤要求先 `stop` + `disable` 旧服务再启动新服务；两个实现都是幂等写入，重复执行不产生脏数据，但会浪费上游请求。
- [主机整体宕机] 进程无法发信，停机期间的触发靠启动补账恢复，但宕机本身无人告警 → 接受该残余风险；不引入外部心跳服务。
- [补账爆量] 水位丢失或长时间停机可能算出极多错过次数 → 枚举上限 1000，超出时按上限截断并告警；`backfill` 始终只补一次，不会逐次重放。
- [SQLite 锁冲突] 业务库仍被 Web 读取、任务写入 → 任务侧统一 `timeout=5` 的短事务与单次提交；账本独立文件，不参与业务库竞争。
- [Windows 开发环境时区] 无系统 tzdata 时 `ZoneInfo` 会失败 → `tzdata` 已列为核心依赖，`uv sync` 后即可用，README 中记录该前提。

## Migration Plan

1. 开发机用 `--mode dev` 逐个任务单次执行，核对写库结果与退出状态。
2. 跑表结构基线校验：冻结模型与新 DDL 各建空库，逐表对比 `PRAGMA table_info` 与 `PRAGMA foreign_key_list`。
3. 验证容错：停机跨过触发点后启动，确认补跑；把上游代理指向不可用地址，确认重试与告警；检查账本状态流转。
4. 生产配置 `config.local.yaml`（SMTP、模式），`systemctl stop` + `disable` 旧 `scheduler_service`，启动新服务。
5. 观察一个完整周期（至少两个整点的快讯抓取 + 一次 OMO + 一次备份），确认运行记录与数据正常。
6. 回滚：停止新服务，重新 `start` 旧服务；代码无需变更。

## Open Questions

- 重试默认值最终取 3 次 / 300 秒是否合适，可在实施首日根据实际失败率调整，不影响表结构与状态机。
- 运行记录保留 90 天是否需要按任务区分（例如备份记录保留更久），可在实施时按实际数据量决定。
- 是否需要在 Web 端展示运行历史：本次不做，Web 的改造范围尚未确定。
