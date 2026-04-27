# QPS=10 Gate-On Nested WAIT Tuning - 2026-04-28

## 状态
🚧 进行中

## 概要
本轮专注 qps=10、WAIT gate on 的 Nested WAIT / WCP 调参，修正了 segment 语义、固定 request bins=50，并将主搜索从粗网格推进到 boundary/gate 微调。当前 best WCP 已接近 Sarathi，但尚未严格 win。

## 完成内容

### 算法与脚本修正
- **固定 request bins=50**: bin 只表示 workload 聚合粒度，不再和 segment 数混用。
- **修正 nested segment 语义**: 后段请求只能在前段 advance 后出现在后段入口；后段是否 release 由自身 boundary backlog 决定，避免错误的同批次 strict chain 造成尾部卡死。
- **新增可调项**: 支持 `gate_total_budget_scale`、`gate_prefill_budget_scale`、`wait_entry_min_count`、`decode_priority`、显式 segment limits 和 custom boundaries。
- **trimmed metric**: qps=10 调参统一使用 head 25% / tail 10% trimmed mean，并要求 `n_completed=5000` 才纳入比较。

### 调参结果
- Sarathi qps=10 baseline: mean `1.703389329`, p99 `5.363853123`, n_completed `5000`.
- 旧 best WCP gate-on: `auto6seg_tl180_cs48_wgON`, mean `1.703744403`.
- 新 best WCP gate-on: `auto6seg_b60-140-220-300-400-500_tl295_cs52_gp1p01_wgON`, mean `1.703400783`, p99 `5.363985574`, n_completed `5000`.
- 当前 gap: WCP 比 Sarathi 慢约 `0.000011454s`，但 p99 基本持平。

### 负结果
- strict same-batch segment chain 会导致 incomplete 或显著变慢；m=6/tl175/180 只完成 `4988/5000`，drain 后 mean 约 `1.93`。
- 低 m/低 tl 不是正确方向；m=2/tl20 drain mean 约 `3.17`。
- gate total scale、FIFO decode priority、seg_margin 小范围微调均未突破 `1.703412176` 平台。
- tl=290..299 单步细扫、gp=0.99/1.00/1.01 未跨过 Sarathi。

## 代码变更

| 类型 | 数量 |
|------|------|
| 新增文件 | 1 |
| 修改文件 | 5 |
| 删除文件 | 1 |

### 关键文件变更

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `scripts/real_data_provenance_rerun.py` | 修改 | 模块化 search strategy，新增 trimmed metrics、gate/boundary/segment-limit sweep 参数。 |
| `vidur/config/config.py` | 修改 | 新增 Nested WAIT gate budget、decode priority、drain、segment limit 配置项。 |
| `vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py` | 修改 | 修正 segment entry / backlog gate 语义，并支持 gate scale 与 decode ordering。 |
| `vidur/scheduler/replica_scheduler/general_nested_booking_limit_replica_scheduler.py` | 修改 | 支持 explicit segment limits 并记录 n_k / segment metadata。 |
| `experiments.db` | 修改 | 记录 qps=10 gate-on 调参与对比结果。 |
| `.gitignore` | 删除 | 用户要求去掉 git ignore；`.claude/settings.local.json` 可继续 ignore。 |

## 测试情况

- [x] `python -m py_compile scripts/real_data_provenance_rerun.py vidur/config/config.py vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py vidur/scheduler/replica_scheduler/general_nested_booking_limit_replica_scheduler.py`
- [x] qps=10 gate-on WCP 多轮调参完成，所有纳入比较的记录均 `n_completed=5000`
- [x] request-level 差距归因完成：WCP 在短请求和 400+ decode 上略快，在 150-400 decode 上略慢

## 下一步计划

- [ ] 继续分析 best WCP 与 Sarathi 的 request-level latency 差异，优先定位 150-400 decode 的慢点。
- [ ] 如需强行 qps=10 win，进一步尝试局部 custom boundaries 与 prefill gate 公式修正，而不是继续扩大普通 m/tl/cs 网格。
- [ ] 将 best config 固化到论文/表格使用的 provenance query 中，并标注 qps=10 当前仍未严格 win。

## 相关文档

- `docs/progress/2026_04_26_real_data_provenance_grid.md`
- `scripts/real_data_provenance_rerun.py`

---

**作者**: 自动生成
**审核**: 待审核
