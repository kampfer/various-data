# 定时任务（Dagu）

本目录是定时任务的唯一实现位置：抓取、解析、入库与备份都在这里，不依赖
`src/web/backEnd/app`。Web 端的 `app/*/models.py` 冻结在迁移时的结构，不再承载新的字段定义。

## 目录结构

```
src/dagu/
  dags/     DAG 定义（cron、队列、重试、失败告警）
  tasks/    任务实现（独立进程执行）
  lib/      路径配置（config.py）、SQLite 连接/建表/入库语句（db.py）
```

## 前置依赖

- Dagu **2.26.0**（已锁定；升级前先对三个 DAG 跑 `dagu validate`）。
- Python 依赖：`requests`、`pyquery`（`Pipfile` 已包含），其余只用标准库。

## 宿主全局配置

Dagu 的两个全局文件都放在 `~/.config/dagu/`，示例随仓库提供：

| 文件 | 仓库内示例 | 作用 |
| --- | --- | --- |
| `config.yaml` | `deploy/config.example.yaml` | `dags_dir`、时区、队列、监听地址 |
| `base.yaml` | `deploy/base.example.yaml` | SMTP、默认通知开关（`chmod 600`） |

- `dags_dir` 必须指向 `src/dagu/dags`，`tz` 写 `Asia/Shanghai`（不依赖 systemd 是否正确传递 `TZ`）。
- `queues.config` 必须登记三个同名队列且 `max_concurrency: 1`：`max_active_runs` 在 v2 已废弃，缺队列时同一 DAG 可能并发执行。
- SMTP 凭据不进仓库：`base.yaml` 只写 `${SMTP_HOST}` / `${SMTP_PORT}` / `${SMTP_USER}` / `${SMTP_PASS}`，实际取值由 systemd 从 `.env` 注入。

## 环境变量

复制 `.env.example` 为 `.env`（该文件已在 `.gitignore` 中），至少包含：

| 变量 | 说明 |
| --- | --- |
| `mode` | `pro` 使用 `data/various_data.db`，其余使用 `data/various_data_dev.db` |
| `PYTHON_BIN` | Python 解释器绝对路径 |
| `DAGU_DIR` | 本目录绝对路径，DAG 用它拼接 `tasks/` 下的脚本 |
| `ALERT_EMAIL` | 失败告警收发地址 |

生产由 systemd 的 `EnvironmentFile` 注入，开发机自行设置后用 `dagu start`。

## 手动执行

```bash
dagu validate src/dagu/dags/crawl-omo.yaml
dagu start src/dagu/dags/crawl-omo.yaml --name crawl-omo
```

本机验证时用一个临时 Dagu 数据目录，避免污染默认位置：

```bash
dagu start src/dagu/dags/crawl-omo.yaml --name crawl-omo --dagu-home "$TEMP/dagu-home"
```

DAG 用 `action: exec` 直接执行解释器，参数以数组传递，不经过 shell——Windows 的 PowerShell 与 Linux 的
`sh` 都能正确执行；用 `run:` 字符串在 Windows 上会因引号解析失败。`with` 中的 `${PYTHON_BIN}`、`${DAGU_DIR}`
由 Dagu 展开，DAG 文件里不含绝对路径。

## 生产部署（systemd）

Dagu 只监听回环地址，通过 SSH 端口转发访问控制台。单元文件见 `deploy/dagu.service`。

部署步骤：

1. 安装 Dagu 2.26.0 到 `/usr/local/bin/dagu`，`dagu version` 确认版本。
2. 复制 `deploy/dagu.service` 到 `/etc/systemd/system/dagu.service`，按实际用户与路径修改。
3. 复制 `.env.example` 为 `.env` 并填入 `mode=pro`、`PYTHON_BIN`、`DAGU_DIR`、`ALERT_EMAIL` 与 SMTP 凭据。
4. 复制 `deploy/config.example.yaml` 与 `deploy/base.example.yaml` 到 `~/.config/dagu/`，把 `base.yaml` 设为 `chmod 600`。
5. `systemctl daemon-reload && systemctl enable --now dagu`。
6. 校验：`systemctl status dagu` 为 active；`curl -I 127.0.0.1:8080` 本机可访问；从其他主机访问 8080 被拒绝；`dagu ls` 列出三个 DAG。

切换与回滚：

- 切换：先手动 `dagu start` 三个 DAG 各跑一轮确认数据，再停用旧的 APScheduler 调度服务（`stop` + `disable`），Dagu 保持运行。
- 回滚：反向操作，启动旧服务并停 Dagu；代码无需变更。
- 切换窗口内不要同时运行两套调度，否则会重复抓取。

## 表结构归属

- `lib/db.py` 是表结构的**唯一演进位置**：新增字段、索引、可空性改动都写在这里。
- 迁移时与既有模型做过一次性基线校验（`scripts/check_task_schema.py`），证明结构兼容；
  这个脚本不是长期同步义务。
- `CREATE TABLE IF NOT EXISTS` 只补建缺失的表，**不会给已有表加列**。生产库新增字段时，
  必须在 `lib/db.py` 中配套 `ALTER TABLE` 迁移语句。
- Web 端在自身迁移前只能读到既有字段；新增字段要等 Web 侧一起迁移后才可见。

## 接入新任务

1. 在 `tasks/` 新增一个脚本，复用 `lib/config.py` 与 `lib/db.py`，入口为 `job()`，异常直接抛出（退出码即结果）。
2. 在 `dags/` 新增一个 YAML：

   ```yaml
   schedule: "0 * * * *"
   queue: <队列名>
   steps:
     - name: run
       action: exec
       with:
         command: ${PYTHON_BIN}
         args:
           - ${DAGU_DIR}/tasks/<脚本>.py
       retry_policy:
         limit: 2
         interval_sec: 300
       mail_on_error: true
   ```

3. 在宿主机 `config.yaml` 的 `queues.config` 中登记同名队列（`max_concurrency: 1`）。
4. 用 `dagu validate` 与 `dagu start` 跑一遍，确认退出码与落库结果。

已接入的任务不需要因新任务而修改。

## 已知限制

- OMO 解析沿用旧实现的"每份公告只保留最后一张匹配表格"的行为，未在此次迁移中改变。
- 新浪快讯首次执行或长期停跑后会从当前最新一条向前翻页补齐，页数取决于间隔时长。
- `error_mail` 中的 `${ALERT_EMAIL}` 展开未在 2.26.0 上实测；若未展开，直接在该字段写死收件地址。
- 若上游持续不可用，重试 2 次后仍会失败并发出告警邮件，属于预期行为。
