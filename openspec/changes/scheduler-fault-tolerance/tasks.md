# Tasks

## 1. 目录骨架与基础配置

- [x] 1.1 建立 `src/scheduler/` 目录与包骨架（`main.py`、`config.py`、`registry.py`、`store.py`、`runner.py`、`catchup.py`、`alert.py`、`lib/`、`tasks/`）；验证：`python src/scheduler/main.py --help` 能输出用法，不报导入错误
- [x] 1.2 实现 `config.py`：按 `--mode` 解析业务库、`scheduler.db`、日志目录、重试默认值与 SMTP 配置路径，规则与现有代码一致；验证：分别用 dev 与 pro 启动，打印的数据库路径分别为 `various_data_dev.db` 与 `various_data.db`
- [x] 1.3 实现 `lib/log.py`：stdout + `log/scheduler.log` 双输出并强制 UTF-8；验证：写入含中文与全角空格的日志，文件中不乱码
- [x] 1.4 新增 `config.local.example.yaml` 并把 `config.local.yaml` 加入 `.gitignore`；验证：`git status` 中不含真实凭据文件，示例文件只有占位值

## 2. 运行账本与状态机

- [x] 2.1 实现 `store.py` 的建表与连接：`job_run`、`job_state`，含 `UNIQUE(job_id, scheduled_at)` 约束与 `busy_timeout=5000`；验证：空库执行后两张表存在，重复插入同一 `job_id + scheduled_at` 被忽略
- [x] 2.2 实现状态流转方法：入账 `pending`、取出置 `running` 并递增 `attempt`、成功置 `success`、失败写 `next_retry_at` 或终态；验证：一次完整流转后各时间字段与尝试次数符合预期
- [x] 2.3 实现启动时的记录清理（保留 90 天）；验证：插入一条 91 天前的已完成记录后启动，该记录被删除，近期记录保留

## 3. 重写三个任务

- [x] 3.1 实现 `lib/db.py`：`CREATE TABLE IF NOT EXISTS` 建表与各表写入语句，结构与冻结模型一致；验证：新增 `scripts/check_task_schema.py` 对比冻结模型与新 DDL 建的库，`PRAGMA table_info` 与 `PRAGMA foreign_key_list` 差异为空
- [x] 3.2 实现 `tasks/sina_news.py`：增量抓取、标签关联、批量入库，请求带超时与状态码校验，业务状态码非 0 抛错；验证：dev 库连续执行两次，第二次无新增记录；状态码异常时退出非零
- [x] 3.3 实现 `tasks/omo.py`：公告翻页、正文抓取、按关键字归类解析、六类交易入库；验证：新增 `scripts/check_omo_parser.py` 对 `data/omo/html` 的 419 份样本零漏解析
- [x] 3.4 实现 `tasks/db_backup.py`：`backup()` 在线快照、临时文件 + 原子替换、`PRAGMA integrity_check` 自检；验证：执行后 `backup/` 下出现当日文件，且对该文件执行完整性检查返回 `ok`
- [x] 3.5 验证任务失败路径：把 `HTTP_PROXY`/`HTTPS_PROXY` 指向不可用代理执行抓取任务，确认以失败结束；再用一份不含 OMO 表格的公告作为新公告，确认"有新公告但解析为空"同样失败；验证完成后恢复环境

## 4. 调度内核

- [x] 4.1 实现 `registry.py` 的 `JobSpec` 与三个任务注册（cron 表达式、`catchup` 属性、重试次数与间隔），`catchup` 必填；验证：启动时打印注册表，三个任务的触发时间与设计表一致
- [x] 4.2 实现 `main.py` 的 APScheduler 装配：`CronTrigger` + `ZoneInfo("Asia/Shanghai")` + `misfire_grace_time=None`，触发函数只入队并唤醒消费者；验证：把触发时间改到 1 分钟后，到点后账本新增一条 `pending`，且任务函数未在该回调中执行
- [x] 4.3 实现 `runner.py` 单线程消费者：条件变量等待、串行执行、同一任务不并发；验证：让同一任务执行耗时超过触发间隔，确认第二次触发排队而非并发，执行结束后补跑一次
- [x] 4.4 实现重试：失败后按声明间隔写入 `next_retry_at`，`attempt` 达到上限后转终态；验证：构造必失败任务，确认按间隔重试且最终只发一封最终失败告警
- [x] 4.5 实现 `catchup.py` 启动补账：`backfill` 合并为一条补跑、`none` 写 `lost`、首次启动不回放、枚举上限 1000；验证：停服跨过 5 次整点触发后启动，账本只多出一条 `trigger_kind=catchup` 的记录且 `missed_count=5`
- [x] 4.6 实现崩溃恢复：启动时把遗留 `running` 置为 `interrupted` 并按剩余次数重新排队；验证：任务执行中强杀进程后重启，该记录被重新执行且 `attempt` 未重置

## 5. 邮件告警

- [x] 5.1 实现 `alert.py` 发送与分级：`catchup=none` 每次失败立即发、`backfill` 仅在重试耗尽发、`lost` 立即发；验证：三类场景各触发一次，收到的邮件数量与设计矩阵一致
- [x] 5.2 实现告警失败不影响任务：SMTP 地址指向不可达时执行失败任务；验证：任务的重试与终态流转照常，日志记录告警失败
- [x] 5.3 实现缺少 SMTP 配置时的降级；验证：不配置 SMTP 启动会打印一次明确警告，任务照常执行且不发信
- [x] 5.4 校验告警内容；验证：收到的邮件包含任务标识、计划时间、尝试次数、错误摘要与可补属性，且不含凭据

## 6. 集成与部署切换

- [ ] 6.1 开发环境完整跑过一个自然日；验证：快讯每小时入账、OMO 在 12:00 入账，账本无长期停留在 `running` 的记录
- [ ] 6.2 编写 systemd 单元（`Restart=always`、`RestartSec=10`）并完成生产切换：先 `stop` + `disable` 旧 `scheduler_service`，再启动新服务；验证：新服务 `active`，旧进程不存在，`git status` 显示 `src/web/backEnd/` 无改动
- [ ] 6.3 验证启动摘要与回滚；验证：重启后日志打印补跑/丢失/待重试条数；回滚为停新服务、`start` 旧服务后任务恢复
- [x] 6.4 在 `src/scheduler/README.md` 记录启动命令、配置位置、接入新任务的步骤（含 `catchup` 必填说明）；验证：按文档从零配置一份本地环境能跑通单次执行

## 7. 收尾检查

- [x] 7.1 确认新实现不依赖冻结代码；验证：`grep -rn "from app\|import app" src/scheduler` 无结果
- [x] 7.2 确认冻结范围未被触碰；验证：`git status` 中 `src/web/backEnd/**` 没有任何修改
- [x] 7.3 确认 Dagu 方案没有残留；验证：`src/dagu` 目录、旧变更目录均不存在，旧 Dagu 版两个失效脚本已删除（新版 `scripts/check_task_schema.py` 与 `scripts/check_omo_parser.py` 由 3.1/3.3 重建），`openspec list` 中只有 `scheduler-fault-tolerance`

## Workflow follow-up

- 本变更完成实施并通过评审后执行归档，确认 `openspec/specs/` 下新增 `task-scheduling`、`task-failure-handling`、`crawler-ingestion`、`database-backup` 四个能力规格。
