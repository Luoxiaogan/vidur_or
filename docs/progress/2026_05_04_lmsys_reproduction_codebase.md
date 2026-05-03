# LMSYS Section 6 Reproduction Codebase - 2026-05-04

## 状态
🚧 进行中

## 概要
本次将 LMSYS Section 6 复现实验从临时长脚本整理为可维护 codebase：`src/` 存放可复用模块，`scripts/` 只保留 CLI 聚合入口。同时完成 `experiments.db` 的无损增量合并，并按当前论文口径启动 Llama-2-7B/A100 的 paper-facing 复现网格。

## 完成内容

### 主要功能
- **模块化复现代码**: 将 real-data provenance runner 的实现迁移到 `src/vidur_or_experiments/lmsys/provenance_runner.py`，顶层 `scripts/real_data_provenance_rerun.py` 只保留兼容入口。
- **Paper-facing scaffold**: 新增 `src/vidur_or_experiments/lmsys/config.py` 和 `runner_command.py`，集中定义 Section 6 LMSYS 复现口径。
- **数据库规范化**: 新增 `src/vidur_or_experiments/lmsys/database.py`、`scripts/lmsys_db.py` 和 `docs/sql/lmsys_reproduction_schema.sql`，使用专用 reproduction DB 记录配置和 summary views。
- **实验入口**: 新增 `scripts/lmsys_section6_reproduction.py`，用于按论文文字口径生成并执行 LMSYS 网格。

### 数据库合并
- `experiments.db` pull 后出现二进制冲突，已无损导出 base/remote/local 三方数据库。
- 以本地调参库为 base，增量导入远端 `reproduction_configs` 和远端新增 `real_data_provenance_runs`。
- 合并后 `PRAGMA integrity_check = ok`。
- 合并结果记录在 `docs/progress/2026_05_03_experiments_db_merge.md`。

### 当前复现实验状态
- 正在运行: `section6_lmsys_reproduction_20260503`
- 配置: Llama-2-7B, A100, `qps=10,20,...,150`, `nreq=5000`, `nbins=50`, Sarathi chunks `512,256`, Nested WAIT `tl=40..300`, `L={1,2,3,4,5,10,20}`, `eta=0.05`, `wait_gate=on`。
- 当前已完成到 qps80/qps90 附近，进程仍在后台运行。
- 目前结论: 低/中 QPS 可打平或部分 win，但 qps70+ 暂时未复现 paper 图中对 best Sarathi 的优势。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 9 |
| 修改文件 | 8 |
| 删除文件 | 0 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/vidur_or_experiments/lmsys/config.py` | 新增 | Section 6 LMSYS paper-facing 配置对象 |
| `src/vidur_or_experiments/lmsys/runner_command.py` | 新增 | 将配置转换为 runner 命令 |
| `src/vidur_or_experiments/lmsys/database.py` | 新增 | reproduction DB schema、registry、summary views |
| `src/vidur_or_experiments/lmsys/provenance_runner.py` | 新增 | 原 durable provenance runner 的实际实现 |
| `scripts/real_data_provenance_rerun.py` | 修改 | 改为兼容 CLI 入口 |
| `scripts/lmsys_section6_reproduction.py` | 新增 | paper-facing LMSYS 复现入口 |
| `scripts/lmsys_db.py` | 新增 | reproduction DB 初始化和 summary |
| `docs/sql/lmsys_reproduction_schema.sql` | 新增 | SQLite schema 文档化 |
| `experiments.db` | 修改 | 合并本地调参库和远端 reproduction config/provenance |

## 遇到的问题与解决

### 问题 1: `experiments.db` 二进制冲突
**现象**: `git pull --rebase` 后 stash pop 产生 `experiments.db` binary conflict。
**原因**: 远端和本地均更新 SQLite DB，Git 无法自动合并。
**解决**: 导出三方 DB，使用 SQLite 增量合并，保留所有备份并记录 merge rule。

### 问题 2: 复现口径和历史 March 调参口径不一致
**现象**: 旧大 win 多来自 Llama-3/旧 metric/高 tl 或 wait-gate-off 口径，不能直接解释当前 paper 文字。
**原因**: 当前论文写的是 Llama-2-7B/A100、`tl<=300`、finite grid、Nested WAIT threshold construction。
**解决**: 固定 paper-facing scaffold，先按正文口径复现，再把不一致作为实验事实报告。

### 问题 3: `scripts/` 和 `src/` 分层混乱
**现象**: 早期新增了 `src/scripts`，不符合项目规范。
**原因**: 将 CLI 和可复用逻辑混放。
**解决**: 删除 `src/scripts`，将逻辑放入 `src/vidur_or_experiments/lmsys/`，`scripts/` 仅保留聚合入口。

## 测试情况

- [x] `py_compile` 通过: `src/vidur_or_experiments/lmsys/*.py`, `scripts/real_data_provenance_rerun.py`, `scripts/lmsys_section6_reproduction.py`, `scripts/lmsys_db.py`
- [x] `scripts/lmsys_section6_reproduction.py --run-tag moved_scaffold_check --qps 10 --limit 5` 可生成 paper-facing plan
- [x] `scripts/real_data_provenance_rerun.py --print-plan` 可通过兼容入口调用模块化 runner
- [x] `experiments.db` integrity check 通过
- [ ] Full LMSYS reproduction grid 完成

## 下一步计划

- [ ] 等待 `section6_lmsys_reproduction_20260503` 全网格跑完。
- [ ] 生成 qps10-150 的 best WCP vs best Sarathi summary。
- [ ] 若 qps70+ 仍无法复现，分别审计 Sarathi512 baseline、wait_gate-on paper 口径、chunk-size 是否应披露为调参维度。
- [ ] 将最终复现结果回填到专用 DB summary / progress 文档。

## 相关文档

- `docs/progress/2026_05_03_lmsys_section6_reproduction_scaffold.md`
- `docs/progress/2026_05_03_experiments_db_merge.md`
- `docs/sql/lmsys_reproduction_schema.sql`

---

**作者**: Codex
**审核**: 待审核
