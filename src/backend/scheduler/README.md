# 定时任务调度器

自包含的爬虫调度器：APScheduler 只负责按 cron 到点触发，真正的执行、重试、补跑与告警状态全部落在
SQLite 账本 `data/scheduler.db`（开发模式为 `data/scheduler_dev.db`）。Python 侧代码与依赖清单都在
`src/backend/`，不依赖仓库中其它 Web 服务。

## 启动

```bash
# 开发环境（读写 data/various_data_dev.db）
uv run --project src/backend python src/backend/scheduler/main.py --mode dev

# 生产环境（读写 data/various_data.db）
uv run --project src/backend python src/backend/scheduler/main.py --mode pro
```

可选参数：

```bash
# 打印任务注册表后退出
uv run --project src/backend python src/backend/scheduler/main.py --mode dev --print-registry

# 立即执行一次指定任务后退出（sina_news / omo / db_backup），失败时退出码非 0
uv run --project src/backend python src/backend/scheduler/main.py --mode dev --run-once sina_news
```

后台管理默认随进程启动，可用以下参数调整：

```bash
# 关闭管理服务
uv run --project src/backend python src/backend/scheduler/main.py --mode dev --no-admin

# 改监听地址与端口（默认 127.0.0.1:8787）
uv run --project src/backend python src/backend/scheduler/main.py --mode dev --admin-host 0.0.0.0 --admin-port 9000
```

`main.py` 会自行把 `src/backend/` 加入 `sys.path`，不依赖当前工作目录或 `PYTHONPATH`。

## 配置

1. 复制示例配置并填写真实值：

   ```bash
   cp src/backend/scheduler/config.local.example.yaml src/backend/scheduler/config.local.yaml
   ```

   `config.local.yaml` 已被 `.gitignore` 忽略，仓库中只保留占位值。
2. 可配置项：

   | 键 | 说明 | 默认 |
   | --- | --- | --- |
   | `retry.max_attempts` | 失败后的最大尝试次数（含首次） | 3 |
   | `retry.interval_seconds` | 两次尝试的间隔秒数 | 300 |
   | `smtp.*` | 告警邮箱（host/port/use_ssl/username/password/recipients） | 无，降级为不发信 |

   缺少 SMTP 配置时启动会打印一次警告，任务照常执行，只是不发邮件。

## 目录

```
src/backend/
  pyproject.toml          后端依赖清单（uv 项目根）
  uv.lock
  .venv/                  依赖环境（git 忽略）
  admin/                  管理 API：FastAPI 路由与 uvicorn 线程封装
  scheduler/
    main.py               入口：装配 APScheduler、启动消费者
    config.py             路径、时区、重试默认值、SMTP
    registry.py           任务注册（cron、catchup、重试参数）
    store.py              运行账本 job_run / job_state
    runner.py             单线程消费者：串行执行与重试
    catchup.py            启动补账与错过触发枚举
    alert.py              邮件告警分级
    lib/db.py             业务库建表与写入语句
    lib/log.py            stdout + log/scheduler.log
    tasks/omo.py          央行公开市场公告
    tasks/sina_news.py    新浪财经快讯
    tasks/db_backup.py    数据库备份
    config.local.example.yaml
```

前端与 Python 后端分开存放：

```
src/frontEnd/             管理页面（React + antd），自带 package.json 与构建配置
src/frontEnd/dist/        前端构建产物（git 忽略）
```

## 运行账本

- `job_run`：每次计划触发一条记录，字段包括 `scheduled_at`、`trigger_kind`
  （`schedule`/`catchup`/`retry`/`manual`）、`status`
  （`pending`/`running`/`success`/`failed`/`lost`/`interrupted`/`cancelled`）、`attempt`、
  `next_retry_at`、`missed_count`、`alerted_at`、`alert_error` 等。
- `job_state`：每个任务的触发水位 `last_trigger_at`，用于启动补账。
- 同一 `job_id + scheduled_at` 只会入账一次；终态记录保留 90 天，启动时清理。
- `trigger_kind=manual`：由后台管理页面「立即执行」写入，不走水位推进。
- `status=cancelled`：由后台管理页面取消的待执行记录，属于终态，永久退出领取范围。
- 人工重试失败记录时，`attempt` 会被回写到 `max_attempts - 1`，因此历史尝试次数不再单调递增，
  这是为了只额外授予一次尝试机会。
- 运行历史直接查询账本：

  ```bash
  sqlite3 data/scheduler.db "select job_id, scheduled_at, status, attempt, error from job_run order by id desc limit 20;"
  ```

## 后台管理

管理服务与调度器同进程，默认监听 `127.0.0.1:8787`，只读调度账本，不访问业务库。

### 构建与开发

前端是 `src/frontEnd` 下的自包含应用，依赖与构建配置都在该目录内，与旧 `src/web` 无关：

```bash
cd src/frontEnd

npm install        # 首次安装
npm run build      # 生产构建，产物输出 src/frontEnd/dist
npm run type-check # 类型检查

npm run dev        # 开发模式：3001 端口，/api 代理到 127.0.0.1:8787
```

后端启动时会检查 `src/frontEnd/dist/index.html`：存在则直接托管该页面；不存在时页面根路径返回
503 并提示执行构建，REST 接口仍然可用。

### 页面能力

- 概览：待执行、待重试、运行中、今日成功/失败、运行环境与账本路径。
- 任务：cron、可补属性、重试参数、下次触发、触发水位、最近一次结果。
- 运行记录：分页与筛选、错误详情、重试失败记录、取消待执行、按天数清理历史。
- 日志：`log/scheduler.log` 尾部，可调行数并支持自动刷新。

### 访问范围

服务不提供登录鉴权，默认只绑定回环地址。需要远程访问时通过 SSH 隧道或反向代理，
若把 `--admin-host` 改为非回环地址，启动日志会输出明确的暴露警告。

## 接入新任务

1. 在 `src/backend/scheduler/tasks/` 新建模块，实现 `run(config)`；任务自身负责建表与幂等写入。
2. 在 `src/backend/scheduler/registry.py` 的 `build_registry()` 中新增 `JobSpec`：
   - `id`：账本中的任务标识，需稳定且唯一；
   - `cron`：传给 `CronTrigger` 的参数，例如 `{"minute": 0}`、`{"hour": 12, "minute": 0}`；
   - `catchup`：**必填**，只能是 `backfill`（可回溯，停机后合并补跑）或
     `none`（只展示最新值、过期不可获取，错过即记 `lost` 并立即告警）；
   - `max_attempts` / `retry_interval_seconds`：失败重试参数；
   - `func`：通常是 `partial(tasks.xxx.run, config)`。
3. 验证：

   ```bash
   uv run --project src/backend python src/backend/scheduler/main.py --mode dev --print-registry
   uv run --project src/backend python src/backend/scheduler/main.py --mode dev --run-once <job_id>
   ```

## 部署

本地生成部署包：

```bash
python deploy/build_zip.py
```

把 zip 上传到服务器后：

```bash
unzip various-data-scheduler-*.zip -d /srv
cd /srv/various-data-scheduler
sudo bash deploy/install.sh install
```

`install` 会同步依赖、生成 `config.local.yaml`、写入 systemd 单元并开机自启。日常操作：

```bash
sudo bash deploy/install.sh start|stop|restart|status
sudo bash deploy/install.sh logs 200
sudo bash deploy/install.sh upgrade    # 重新上传代码后同步依赖并重启
```

生产切换后观察至少两个整点的快讯抓取、一次 12:00 的 OMO 与一次月度备份；启动日志会打印
`启动摘要: 补跑=… 丢失=… 待重试=…`。

## 表结构基线

业务库表结构以冻结模型为基线：

```bash
uv run --project src/backend python scripts/check_task_schema.py   # 与冻结模型比对 PRAGMA，差异为空时退出码 0
uv run --project src/backend python scripts/check_omo_parser.py    # 用 data/omo/html 的历史样本回归解析
```
