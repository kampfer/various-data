# Design

## Context

动机与范围见 [proposal.md](./proposal.md)。实现前需要了解的现状与约束：

- 三个任务均为"读上游、写 SQLite"的短时批处理，彼此**无数据依赖**，周期分别是 1 小时、每天 12:00、每月 1 日。
- 数据库文件由 `mode` 环境变量决定：`pro` → `data/various_data.db`，其余 → `data/various_data_dev.db`；路径基于源码文件位置推导，不依赖进程工作目录。
- 需要写入的表结构（以 `app/omo/models.py`、`app/sinaFinanceNews/models.py` 为准）：
  - OMO：`app_state(name PK, value)`、`omo_repo/omo_rrp/omo_mlf/omo_tmlf(time, period 复合 PK, amount, rate)`、`omo_nb(time, period PK, amount, price)`、`omo_cb(time, name PK, amount, period, price, rate)`
  - 新浪快讯：`sf_news(id 自增 PK, sina_id, create_time, content, url, significance)`、`sf_tag(id 自增 PK, name, is_sina_tag, sina_id)`、`sf_news_tag(left_id, right_id 复合 PK)`
- 既有抓取逻辑分布在 `app/tasks/crawlOMO.py`（约 480 行，含 OMO 公告表格解析规则）、`app/tasks/crawlSinaNews.py`、`app/tasks/backupDatabase.py`，它们依赖 `app.database`、`app.logger`、`app.omo.crud`、`app.sinaFinanceNews.*`。
- `crawlSinaNews` 自身不建表，原先靠 `scheduler_service.py` 统一建表；`crawlOMO` 在 `__main__` 中自建表。
- 生产为 Linux（`start.sh` 使用 `nohup uvicorn`），开发机为 Windows；两处共享同一个 git 仓库。

## Goals / Non-Goals

**Goals:**

- 新目录自包含：新实现不导入 `app.*`，可独立运行、独立演进。
- 编排定义与任务实现集中在 `src/dagu/`，既有 `app/tasks` 零改动，交接期可并存。
- 一套 DAG 同时服务生产与开发，仅通过环境变量切换数据库与解释器。
- 为后续迁移提供稳定范式（新增实现 + 新增 DAG 即可）。
- 顺带修掉两个已知限制：请求无超时、解析失败静默成功。

**Non-Goals:**

- 不删除、不重构、不改写 `app/tasks/*`、`app/scheduler.py`、`scheduler_service.py`。
- 不迁移 `pickStock.py`（未注册调度的调试脚本）。
- 不改变入库的业务语义（去重规则、字段含义、表名与主键），只改变执行方式与失败判定。
- 不移除 `apscheduler` 依赖，不改 `package.json` 的 `dev:task` / `start:task`。
- 不引入 ORM/迁移框架，不引入集中式指标系统。

## Decisions

### 1. 编排引擎选用 Dagu

Dagu 以 YAML 定义 DAG、内置 cron、并发上限、重试、运行历史与 UI，单个静态二进制、无外部依赖，适合这种"少量、低耦合、SQLite 落库"的场景。

替代方案与放弃原因：

- 继续用 APScheduler 并补日志/告警：需要在应用内自行实现运行记录、重试和告警，代码量与维护成本高于引入 Dagu。
- Airflow / Prefect：需要数据库/服务端与调度 Worker，运维面远大于本项目的三个任务。
- 系统 cron + 自建日志：没有运行历史与手动触发 UI，失败感知仍薄弱。

### 2. 目录隔离且完全自包含

```
src/dagu/
  dags/
    crawl-sina-news.yaml
    crawl-omo.yaml
    backup-database.yaml
  tasks/
    omo.py           # 抓取公告列表 → 抓正文 → 解析表格 → 入库
    sina_news.py     # 抓取快讯 → 解析 JSON → 入库
    db_backup.py     # 在线备份 + 完整性自检
  lib/
    config.py        # 仓库根、数据目录、数据库路径、mode
    db.py            # sqlite3 连接、建表 DDL、upsert 语句
  .env.example
  README.md
```

- **不导入 `app.*`**：数据库路径在 `lib/config.py` 中按同一规则重新实现；表结构在 `lib/db.py` 中以 `CREATE TABLE IF NOT EXISTS` 提供；入库语句用标准库 `sqlite3` 手写。
- 选择完全自包含而非复用 `app.omo.crud` / `app.sinaFinanceNews.crud`：迁移后的实现要能独立演进、独立部署，不受 Web 端重构影响；代价是表结构需与 Web 端模型同步（见风险段）。
- 放弃"新建 runner 只调既有 `job()`"：那等于新旧代码永久耦合，迁移不彻底，且无法在不改旧文件的前提下加超时、改失败判定。
- 依赖仅限标准库 + 仓库已有 `requests`、`pyquery`，不新增 Python 依赖。

### 3. 三个独立 DAG，而不是一条依赖链

Dagu 每个 DAG 只有一条 `schedule`。三个任务周期不同且无依赖，拆成三个 DAG：

| DAG | cron | 替代原配置 |
| --- | --- | --- |
| `crawl-sina-news` | `0 * * * *` | `interval hours=1` |
| `crawl-omo` | `0 12 * * *` | `cron hour=12` |
| `backup-database` | `0 0 1 * *` | `cron day=1` |

放弃"单 DAG + depends 串行"：会把三个周期绑成一个（最短周期决定整链频率），且任一任务失败会阻断后面的任务。

### 4. 步骤直接执行任务脚本

Dagu 2.26.0 的推荐写法是 `action: exec` + `with`，参数以数组传递，不经过 shell：

```yaml
steps:
  - name: run
    action: exec
    with:
      command: ${PYTHON_BIN}
      args:
        - ${DAGU_DIR}/tasks/omo.py
    retry_policy:
      limit: 2
      interval_sec: 300
    mail_on_error: true
```

- 不用 `run:` 字符串：它在 Windows 上交给 PowerShell 执行，引号嵌套会解析失败；`exec` 形式在 Linux 与 Windows 行为一致。
- 脚本开头把 `src/dagu` 加入 `sys.path`（`Path(__file__).resolve().parents[1]`）后导入 `lib.*`，因此**不依赖工作目录、不需要 `PYTHONPATH`**。
- `PYTHON_BIN` / `DAGU_DIR` 由宿主环境变量提供（生产 systemd `EnvironmentFile`，开发机 shell 环境），DAG 文件不含绝对路径；已验证 `with` 中支持 `${VAR}` 展开。
- 备选：`dagu` 的 `dotenv` 加载 `.env`。放弃原因是把"每台机器一份配置"耦合进 DAG 语法，且各版本语义有差异。

### 5. 环境隔离靠 `mode` 环境变量

生产 `.env` 写 `mode=pro`，开发写 `mode=dev`；`lib/config.py` 据此选择数据库文件，与 Web 端规则一致。`src/dagu/.env.example` 入库，`.env` 加入 `.gitignore`。

### 6. 并发控制：全局队列串行（Dagu v2）

Dagu 2.26.0 中 `max_active_runs` 已标记 deprecated 且对本地队列不生效，并发控制改由全局队列承担：

```yaml
# 宿主机 ~/.config/dagu/config.yaml
queues:
  enabled: true
  config:
    - name: omo
      max_concurrency: 1
```

DAG 中只声明 `queue: omo`（三个任务各自一个队列）。效果是同一 DAG 同时最多一个实例，前次未结束时新触发不会并发启动，替代原 `max_instances=1` 的防重入语义。

不使用 `skip_if_successful`：它会把每小时的抓取压成"每周期只跑一次"，不符合需求。

### 7. 迁移时增强：超时与解析失败判定

- 所有上游请求设置超时（连接/读取各 30 秒）并校验 HTTP 状态码，非 2xx 直接抛出，进程以非零退出。
- 解析失败判定：`crawl-omo` 中**发现了新公告却一条记录都没解析出来**时抛错退出；"没有新公告"（非交易日）仍按成功处理。
- 入库部分保持原语义：OMO 以复合主键 `ON CONFLICT DO NOTHING` 去重，`app_state` 记录最新公告名；新浪快讯按原逻辑先查最大 `sina_id` 再增量抓取，标签按名称复用。
- 新浪接口返回状态码非 0 时抛出明确异常，不再在后续取值时抛 `TypeError`。

### 8. 备份在 `tasks/db_backup.py` 独立实现

- 用 `sqlite3.connect(src).backup(dst_conn)` 生成一致快照；先写临时文件再 `os.replace` 原子替换，避免中断留下半个文件。
- 备份后执行 `PRAGMA integrity_check` 自检，失败则非零退出。
- 相比 `VACUUM INTO`：`backup()` 不要求目标文件不存在，天然支持同日重复执行覆盖，也不改变源库 journal 模式。
- 路径与命名保持原样：`backup/<源库名>_YYYYMMDD.db`，目录不存在时自动创建。

### 9. 部署形态：本机 systemd 服务，UI 只监听回环

- 二进制安装到 `/usr/local/bin/dagu`，固定版本；`DAGU_HOME=/var/lib/dagu`，`DAGU_DAGS_DIR` 指向仓库内 `src/dagu/dags`。
- systemd 单元设置 `TZ=Asia/Shanghai`、`EnvironmentFile=/opt/various-data/src/dagu/.env`，`ExecStart` 启动 `dagu server --host 127.0.0.1 --port 8080`（参数名以实际版本为准）。
- 维护者通过 SSH 端口转发访问；不对外暴露，无需额外认证。
- 开发机：直接 `dagu start <dag>` 单次执行，不常驻服务。

### 10. 告警配置放在宿主机，不进仓库

Dagu 的 SMTP 配置写入 `~/.config/dagu/config.yaml`（`chmod 600`），DAG 开启 `mailOnError` 并声明收件人。仓库内只留字段说明。`app/email2.py` 中的硬编码凭据不迁移、不复用，保持原样。

### 11. SQLite 并发写入的处理

- 新实现用标准库 `sqlite3`，连接设置 `timeout=5`（忙等重试），每次任务一个连接、一次提交，事务为秒级。
- 不启用 WAL：会额外产生 `-wal`/`-shm` 文件，改变运维认知；当前写入频率下收益不明显。若出现 `database is locked`，再单独评估。
- 备份不再拷贝文件（见决策 8），不会读到写一半的状态。

### 12. 表结构归属：新目录是唯一演进位置，旧模型冻结

- 迁移时一次性对齐基线：新目录 DDL 与 `app/*/models.py` 结构一致，用校验证明（两边各建空库，逐表对比 `PRAGMA table_info` 与 `PRAGMA foreign_key_list`）。
- 之后表结构只在新目录演进：新增字段、索引、可空性改动都写进 `lib/db.py`；旧模型不再新增字段，旧爬虫与旧调度进程停用，视为废弃实现，后续批次删除。
- 代价：Web 端在自身迁移前只能读到既有字段；新增字段要等 Web 侧一起迁移后才可见。这是"旧代码不参与演进"的必然结果，接受。
- `CREATE TABLE IF NOT EXISTS` 只补建缺失的表，不会给已有表加列；因此后续新增字段必须在 `lib/db.py` 中配套 `ALTER TABLE` 迁移语句（执行方式在后续变更中确定）。

### 13. 切换方式：停用不删除

- 生产 `systemctl stop && systemctl disable` 原 `scheduler_service`，启用 Dagu 服务；代码、依赖、npm 脚本全部保留。
- 必须整进程停用：三个任务仍注册在 APScheduler 中，两边同时存活会各跑一遍。写库是 upsert / 先去重再插入，重复执行不产生脏数据，但仍会浪费上游请求。
- 回滚：重新 `start` 原服务并停 Dagu，无需 `git revert`。

### 14. 日志只写 stdout

新实现不接入 `app.logger`（避免与 Web 端日志文件互相污染），信息与异常统一输出到 stdout/stderr，由 Dagu 按次收集，在 UI 中可查。

### 15. 后续任务接入约定

每接入一个新任务，只做两件事：新增 `src/dagu/tasks/<task>.py`、新增 `src/dagu/dags/<task>.yaml`。若该任务目前在 APScheduler 中注册，需在切换时下线其注册——属于后续批次，届时决定删除注册代码还是保留。

## Risks / Trade-offs

- [表结构归属切换] 新目录成为唯一演进位置，旧模型冻结 → 迁移时用一次性基线校验证明兼容；此后新增字段只改 `lib/db.py`，旧模型不动；`IF NOT EXISTS` 不补列，字段变更需配套 `ALTER`。
- [Web 端读不到新字段] 旧模型冻结，Web 侧迁移前新增字段不可见 → 接受；如需展示，另开变更迁移 Web 端读取逻辑。
- [双实现并存] 交接期内旧爬虫文件仍在（不删、不调度），页面结构变化时需要改新实现，容易误改旧文件 → README 明确"调度与新功能以 `src/dagu` 为准"；后续批次删除旧文件。
- [版本字段差异] 已锁定 Dagu 2.26.0 并用 `dagu validate` 校验三个 DAG；v2 使用 snake_case（`error_mail` / `retry_policy` / `mail_on_error`），`run:` 字符串在 Windows 下走 PowerShell 会解析失败，故统一用 `action: exec`；并发控制依赖宿主机 `config.yaml` 的 `queues`，部署时必须同步配置。
- [解析规则回归] 迁移会重写约 480 行 OMO 解析逻辑，存在行为偏差风险 → 用仓库内 `data/omo/html` 已有公告样本做回归：迁移前后同一批 HTML 的提取结果必须一致。
- [解析失败判错带来误报] 央行新版式可能导致解析 0 条而失败 → 依靠重试吸收抖动；误报本身是期望行为（能尽早发现版式变化），修复后手动重跑即可。
- [切换瞬间重复执行] APScheduler 与 Dagu 同时存活会重复抓取 → 迁移步骤要求先停原服务再启用 Dagu。
- [Dagu 服务挂掉] 任务全部停摆且无人知晓 → systemd `Restart=always`；UI 无认证但仅回环。
- [超时仍可能卡在重试] 上游持续不可用时会连续失败并触发邮件 → 重试次数限制为 2 次，间隔 5 分钟。

## Migration Plan

1. 开发机：跑一次表结构一致性校验（既有模型建库 vs 新 DDL 建库，逐表比对 `PRAGMA table_info`），确认无差异。
2. 开发机：配置 `src/dagu/.env`（`mode=dev`），用 `data/omo/html` 中的历史公告样本验证 OMO 解析结果与旧实现一致。
3. 开发机逐个 `dagu start` 三个 DAG，核对写库结果、退出码、失败告警。
4. 生产安装 Dagu 与 systemd 单元，配好 `EnvironmentFile` 与 SMTP；先手动 `dagu start` 跑一轮确认真实数据。
5. 停用 `scheduler_service`（stop + disable）→ 启用 Dagu 服务。
6. 观察一轮完整周期（至少两个整点的 sina 抓取 + 一次 OMO），确认运行记录与数据正常。
7. 回滚：`systemctl start scheduler_service` 并停 Dagu；代码无需变更。

## Open Questions

- Dagu 具体版本号与步骤超时字段名，需在实施第一步确认后固定（不影响本设计与任务拆分）。
