# Tasks

## 1. 隔离目录与自包含基础库

- [x] 1.1 创建 `src/dagu/` 下的 `dags/`、`tasks/`、`lib/`、`.env.example`、`README.md`（记录锁定的 Dagu 版本、安装与启动方式、SMTP 配置位置、表结构归属与新字段落点、接入新任务的步骤）；验证：目录与文件齐备，README 中的命令可照抄执行
- [x] 1.2 实现 `lib/config.py`：按 `mode` 解析数据库路径、`data/omo/html`、`backup/` 与仓库根，规则与现有实现一致；验证：分别用 `mode=dev` 与 `mode=pro` 执行一次，打印出的数据库路径与预期一致
- [x] 1.3 实现 `lib/db.py`：`timeout=5` 的 sqlite3 连接、`CREATE TABLE IF NOT EXISTS`（`app_state`、`omo_repo`、`omo_rrp`、`omo_mlf`、`omo_tmlf`、`omo_nb`、`omo_cb`、`sf_news`、`sf_tag`、`sf_news_tag`）、以及各表的 upsert 语句；验证：在空库上执行后各表均可写入，且用既有模型建的库跑同一批 UPSERT 不报错
- [x] 1.4 增加一次性基线校验：分别用 `app/*/models.py` 与新 DDL 建两个空库，逐表对比 `PRAGMA table_info` 与 `PRAGMA foreign_key_list`；验证：校验脚本输出差异为空，改动任一列后可复现差异；该脚本只证明迁移时兼容，不作为长期同步义务
- [x] 1.5 把 `src/dagu/.env` 加入 `.gitignore`，`.env.example` 提供 `mode`、`PYTHON_BIN`、`DAGU_DIR`；验证：编辑 `.env` 后 `git status` 不出现该文件

## 2. 迁移三个任务实现

- [x] 2.1 新增 `tasks/omo.py`：迁移公告列表翻页、正文抓取、六种类型的表格解析与入库；请求加超时与状态码校验；发现新公告却解析出 0 条记录时抛错退出；验证：用 `data/omo/html` 中已有的历史公告样本逐份解析，记录条数与字段值与原实现一致
- [x] 2.2 新增 `tasks/sina_news.py`：迁移增量抓取、标签关联与批量入库；接口返回状态码非 0 时抛明确异常；验证：在 dev 库连续执行两次，第二次不产生重复记录，且记录数与上游一致
- [x] 2.3 新增 `tasks/db_backup.py`：SQLite 在线备份写临时文件后原子替换，并做完整性自检；验证：执行后 `sqlite3 <备份文件> "PRAGMA integrity_check"` 返回 `ok`，`backup/` 下文件命名与原有规则一致
- [x] 2.4 验证失败路径：把 `HTTP_PROXY`/`HTTPS_PROXY` 指向不可用代理执行 `tasks/omo.py`，确认退出码非零；再用一份不含 OMO 表格的公告作为新公告输入，确认"有新公告但解析为空"同样以非零退出；两项完成后恢复环境

## 3. DAG 编排定义

- [ ] 3.1 新增 `dags/crawl-sina-news.yaml`（cron `0 * * * *`、`queue: sina_news`、`retry_policy` 2 次间隔 300 秒、`mail_on_error`）；验证：`dagu start crawl-sina-news` 在 dev 环境成功，表中有新增记录（新浪任务单次执行时间长，尚未在 dev 跑通）
- [x] 3.2 新增 `dags/crawl-omo.yaml`（cron `0 12 * * *`，其余同上）；验证：`dagu start crawl-omo` 成功，数据落库或明确记录无新公告
- [x] 3.3 新增 `dags/backup-database.yaml`（cron `0 0 1 * *`）；验证：`dagu start backup-database` 后 `backup/` 下出现当日文件且完整性检查通过
- [ ] 3.4 校验触发时间与时区：按决定跳过本机验证，改由宿主机 `config.yaml` 的 `tz: Asia/Shanghai` 保证（在 4.1 部署时随配置生效）

## 4. 生产部署与切换

- [ ] 4.1 编写 Dagu 的 systemd 单元（已生成 `src/dagu/deploy/dagu.service`：`TZ=Asia/Shanghai`、`EnvironmentFile` 指向 `src/dagu/.env`、`Restart=always`；配置模板 `deploy/config.example.yaml` 含 `dags_dir`、`tz` 与三个 `max_concurrency: 1` 队列）；验证：在服务器上 `systemctl status dagu` 为 active，从其他主机访问 8080 被拒绝
- [ ] 4.2 在宿主机 `~/.config/dagu/base.yaml` 配置 SMTP（模板 `src/dagu/deploy/base.example.yaml`，凭据由 `.env` 的 `SMTP_*` 注入，权限 600）；验证：`grep -r "SMTP_PASS" src/` 无明文，DAG 与配置文件中不含密码
- [ ] 4.3 切换：先手动 `dagu start` 三个 DAG 各跑一轮确认数据，再 `stop` + `disable` 原调度服务并启用 Dagu；验证：连续两个整点由 Dagu 触发并留下运行记录，原调度进程不存在，`git status` 显示 `src/web/backEnd/` 无改动
- [ ] 4.4 验证失败告警：临时把 `PYTHON_BIN` 指向不存在的路径触发一次失败；验证：收到失败邮件、UI 中该次运行标记失败，恢复配置后手动触发成功

## 5. 集成验证与迁移约定

- [ ] 5.1 完整跑过一个自然日：sina 每小时触发、OMO 在 12:00 触发；验证：Dagu 运行记录无失败堆积，抓取表数据量与上游一致
- [ ] 5.2 手动触发一次备份并与源库对比；验证：备份可正常打开、`PRAGMA integrity_check` 为 `ok`，关键表行数与源库接近（允许备份时刻后的增量差异）
- [ ] 5.3 确认新实现与 Web 端互通：`src/dagu` 内不存在对 `app.` 的导入，Web 端接口能正常读取新实现写入的数据，旧任务实现与旧模型中没有本次新增的字段定义；验证：`grep -rn "from app\|import app" src/dagu` 无结果，接口返回包含新数据，`git status` 显示旧实现未被修改
- [ ] 5.4 在 `src/dagu/README.md` 中补齐"接入新任务"步骤，并对照现有三个任务逐条核对；验证：按文档走一遍只需新增 `tasks/` 与 `dags/` 各一个文件

## Workflow follow-up

- 按项目评审要求归档该变更，归档后确认 `openspec/specs/` 下新增三个能力规格。
