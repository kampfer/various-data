# Spec Delta

## Purpose

保证数据库备份按固定周期产出、命名可预期，并且在其他任务并发写入数据库时仍能得到一致、可恢复的快照。

## ADDED Requirements

### Requirement: 备份周期与文件命名

系统 SHALL 在每月 1 日生成一次数据库备份，备份文件 MUST 在源数据库文件名后追加 `_YYYYMMDD` 再存入 `backup/` 目录（生产环境即 `various_data_YYYYMMDD.db`）；目录不存在时 MUST 自动创建。

#### Scenario: 每月首次执行

- **WHEN** 到达每月 1 日的备份时间且 `backup/` 目录不存在
- **THEN** 创建目录并生成 `backup/various_data_YYYYMMDD.db`

#### Scenario: 同月重复执行

- **WHEN** 同一天重复执行备份
- **THEN** 备份文件被覆盖，最终仅保留一份当日备份

### Requirement: 备份内容一致性

备份 MUST 在数据库可能被其他任务同时写入的情况下产出一致快照；备份完成后 MUST 能通过 SQLite 完整性检查并可正常打开查询，MUST NOT 出现事务中间状态或损坏。

#### Scenario: 备份期间有并发写入

- **WHEN** 备份执行期间抓取任务正在写入数据库
- **THEN** 生成的备份文件可被 SQLite 打开，且完整性检查通过

#### Scenario: 备份来源为生产库

- **WHEN** 在生产环境执行备份
- **THEN** 备份内容来自 `data/various_data.db` 而非开发库

### Requirement: 备份失败可见

备份过程中出现错误（例如源数据库不可读、目标目录不可写）时，执行 MUST 以非零退出码结束，并触发失败告警。

#### Scenario: 目标目录不可写

- **WHEN** `backup/` 目录权限不足导致无法写入
- **THEN** 该次执行以非零退出码结束，并发送失败告警邮件
