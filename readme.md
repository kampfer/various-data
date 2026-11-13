# various-data

定时数据采集与备份服务：APScheduler 负责按 cron 触发，SQLite 账本负责记录每次运行、重试、补跑与告警状态，进程内附带一个 React + antd 管理页面。

## 功能

| 任务 | 频率 | 数据源 | 产出 |
| --- | --- | --- | --- |
| `sina_news` | 每小时整点 | 新浪财经快讯 | `sf_news` / `sf_tag` / `sf_news_tag` |
| `omo` | 每天 12:00 | 央行公开市场业务公告 | `omo_repo` / `omo_rrp` / `omo_mlf` / `omo_tmlf` / `omo_nb` / `omo_cb` |
| `db_backup` | 每月 1 日 00:00 | 本地业务库 | 在线快照写入 `backup/` |

可靠性设计：

- 每次计划触发先入账，再由单线程消费者串行执行，避免并发写库。
- 失败按 `max_attempts` / `interval_seconds` 重试，重试记录仍挂在同一条运行记录上。
- 启动时按水位补账：可回溯任务合并补跑，不可回溯任务记 `lost` 并立即告警。
- 进程收到 SIGINT 时先停调度器，再停消费者与管理服务，不遗留半执行状态。

## 目录结构

```
src/
  backend/                     Python 后端（一个 uv 项目）
    pyproject.toml             依赖清单
    uv.lock
    admin/                     管理 API（FastAPI + 线程内 uvicorn）
    scheduler/                 调度器
      main.py                  入口
      config.py                路径、时区、重试、SMTP
      registry.py              任务注册
      store.py                 运行账本
      runner.py                单线程消费者
      catchup.py               启动补账
      alert.py                 邮件告警
      lib/                     业务库与日志
      tasks/                   sina_news / omo / db_backup
      config.local.example.yaml
  frontEnd/                    管理页面（React 18 + antd 5）
    dist/                      构建产物（git 忽略）
deploy/                        打包与部署脚本
tests/                         后端测试
data/                          业务库与调度账本（git 忽略）
log/                           运行日志
backup/                        数据库备份
```

## 环境要求

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Node.js 20+ 与 npm（仅构建前端时需要）

## 快速开始

```bash
# 1. 安装后端依赖
uv sync --project src/backend

# 2. 构建管理页面
cd src/frontEnd
npm install
npm run build
cd ../..

# 3. 启动（dev 模式）
uv run --project src/backend python src/backend/scheduler/main.py --mode dev
```

启动后访问 http://127.0.0.1:8787 。

## 常用命令

```bash
# 生产模式（读写 data/various_data.db 与 data/scheduler.db）
uv run --project src/backend python src/backend/scheduler/main.py --mode pro

# 关闭管理服务
uv run --project src/backend python src/backend/scheduler/main.py --mode dev --no-admin

# 调整管理页面监听地址与端口（默认 127.0.0.1:8787）
uv run --project src/backend python src/backend/scheduler/main.py --mode dev --admin-host 0.0.0.0 --admin-port 9000

# 查看任务注册表
uv run --project src/backend python src/backend/scheduler/main.py --mode dev --print-registry

# 立即执行一次指定任务后退出
uv run --project src/backend python src/backend/scheduler/main.py --mode dev --run-once sina_news

# 后端测试
cd src/backend && uv run pytest

# 前端热更新开发（3001 端口，/api 代理到 8787）
cd src/frontEnd && npm run dev
```

`main.py` 会自行把 `src/backend` 加入 `sys.path`，不依赖当前工作目录或 `PYTHONPATH`。

## 配置

```bash
cp src/backend/scheduler/config.local.example.yaml src/backend/scheduler/config.local.yaml
```

`config.local.yaml` 已被 git 忽略，可配置：

| 键 | 说明 | 默认 |
| --- | --- | --- |
| `retry.max_attempts` | 最大尝试次数（含首次） | 3 |
| `retry.interval_seconds` | 重试间隔秒数 | 300 |
| `smtp.*` | 告警邮箱；缺省时降级为只记日志 | 不发信 |

路径约定：

- 业务库：`data/various_data.db`（dev 为 `data/various_data_dev.db`）
- 调度账本：`data/scheduler.db`（dev 为 `data/scheduler_dev.db`）
- 日志：`log/scheduler.log`
- 备份：`backup/`

## 后台管理

页面包含四个区域：

- 概览：待执行、待重试、运行中、今日成功/失败、环境与账本路径
- 任务：cron、补跑策略、重试参数、下次触发、水位、最近一次结果
- 运行记录：分页与筛选、错误详情、重试失败记录、取消待执行、按天清理历史
- 日志：`log/scheduler.log` 尾部，可调行数并自动刷新

四个写操作分别对应：立即执行、重试失败、取消待执行、按天数清理历史。

页面不提供登录鉴权，默认只绑定回环地址；需要远程访问时应通过 SSH 隧道或防火墙限制来源。

## 运行账本

- `job_run`：每次计划触发一条记录，`trigger_kind` 为 `schedule` / `catchup` / `retry` / `manual`，`status` 为 `pending` / `running` / `success` / `failed` / `lost` / `interrupted` / `cancelled`。
- `job_state`：每个任务的触发水位，用于启动补账。
- 同一 `job_id + scheduled_at` 只入账一次；终态记录保留 90 天，启动时清理。
- 人工重试失败记录时，`attempt` 会回写到 `max_attempts - 1`，只额外授予一次尝试机会。

## 打包与部署

本地生成部署包（默认会复用已有前端产物）：

```bash
python deploy/build_zip.py
```

服务器上安装：

```bash
unzip various-data-scheduler-*.zip -d /srv
cd /srv/various-data-scheduler
sudo bash deploy/install.sh install
```

`install` 会依次完成：`uv sync --frozen --no-dev`、创建运行目录、生成 `config.local.yaml`、写入 `/etc/default/various-data-scheduler`、注册 systemd 并开机自启。

```bash
sudo bash deploy/install.sh start|stop|restart|status
sudo bash deploy/install.sh logs 200
sudo bash deploy/install.sh logs -f
sudo bash deploy/install.sh upgrade    # 重新上传代码后同步依赖并重启
sudo bash deploy/install.sh uninstall  # 保留 data/log/backup
```

部署参数（`/etc/default/various-data-scheduler`）：

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `VD_MODE` | 运行模式 | `pro` |
| `VD_ADMIN_ENABLED` | 是否启动管理服务，`0` 关闭 | `1` |
| `VD_ADMIN_HOST` | 管理服务监听地址 | `0.0.0.0` |
| `VD_ADMIN_PORT` | 管理服务端口 | `8787` |

安装脚本默认把页面绑定到 `0.0.0.0` 且没有鉴权，请用防火墙限制来源 IP。
