# Real-data provenance grid narrowing - 2026-04-26

## 状态
已完成

## 概要
Real-data LMSYS provenance rerun pipeline 已收窄为可追溯的窄网格：每个 QPS 只生成 3 个 `tl` 点，`tl <= 300`，uniform segment count 只扫 `m in {5,10,20,50}`，并过滤 `tl < m` 的无效候选。脚本同时支持按当前网格清理同一 `run_tag` 下的旧缓存行，避免旧宽网格污染 summary 或 grids table。

## 完成内容

### 主要功能
- 新增 `scripts/real_data_provenance_rerun.py`，用 SQLite durable logging 记录 real-data rerun 的 scheduler family、hyperparameters、baseline variant、WAIT gate settings、stdout/stderr 和 request metrics artifact path。
- 抽出 `SearchStrategy`、`resolve_tl_values_for_qps(...)`、`build_search_strategy(...)`，把 QPS 到 `tl` 网格的逻辑从 `main()` 中移出。
- 默认启用 adaptive three-point `tl` grid，参数为 `step=20`、`slope=6.0`、`min_tl=40`、`max_tl=300`、`half_width=20`。
- 三点网格在上界处会向左补齐，例如高 QPS 使用 `[260, 280, 300]`，避免截断后只剩 1-2 个点。
- uniform segment sweep 固定为 `m = 5,10,20,50`；auto50seg 和 uniform grid 都会跳过 `tl < m`。
- 新增 `--prune-stale` 能力，删除同一 `run_tag` 下不属于当前生成网格的旧 WCP 行。

### Bug 修复
- `general_nested_booking_limit_replica_scheduler.py` 中 `unique_decodes` 为空时的 segment 初始化现在回退到 count 1，避免空 workload 分支直接索引失败。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 1 |
| 修改文件 | 3 |
| 删除文件 | 0 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `scripts/real_data_provenance_rerun.py` | 新增 | Durable real-data provenance rerun pipeline，含窄网格策略、schema migration、resume、summary、stale grid pruning。 |
| `experiments.db` | 修改 | 添加/清理 `real_data_provenance_full_20260426_wg_on_off_sar256_512` 相关 provenance rows；旧宽网格 WCP rows 已按新网格 pruning。 |
| `vidur/scheduler/replica_scheduler/general_nested_booking_limit_replica_scheduler.py` | 修改 | 防止 `unique_decodes` 为空时初始化 segment count 报错。 |
| `.claude/CLAUDE.md` | 修改 | 同步新增进度报告和 provenance rerun 脚本索引。 |

## 网格审计

- 生成总 specs: 476。
- WCP specs: 446。
- Baseline specs: 30。
- 约束违规数: 0。
- `experiments.db` 中同一 `run_tag` 下旧宽网格 stale WCP rows 已 pruning: 144。
- pruning 后 remaining invalid rows: 0。

### QPS -> tl grid

| QPS | tl values |
|-----|-----------|
| 10 | 40, 60, 80 |
| 20 | 100, 120, 140 |
| 30 | 160, 180, 200 |
| 40 | 220, 240, 260 |
| 50-150 | 260, 280, 300 |

## 测试情况

- `python -m py_compile scripts/real_data_provenance_rerun.py`
- Dry plan validation over QPS 10-150 with `wait_gate=on,off`, Sarathi256, Sarathi512:
  - `total_specs=476`
  - `wcp_specs=446`
  - `baseline_specs=30`
  - `violations=0`
- SQLite pruning validation:
  - `pruned=144`
  - `remaining_bad=0`

## 下一步计划

- 继续用同一 `run_tag` resume 窄网格，已有有效 rows 自动 skip cached。
- 跑完后从 `real_data_provenance_runs` 直接生成 paper-facing grids table，避免从最终图或手工数组反推。
- 对 best WCP config 逐项保留 `stdout/stderr/request_metrics` provenance path。

---

**作者**: 自动生成
**审核**: 待审核
