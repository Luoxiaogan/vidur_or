# SGLang Mixing 实验 - 当前状态

> 最后更新: 2026-02-19

## 当前工作

SGLang Fake Decode 模式下的 batch metrics 记录功能已完成 V2/V3 修复。

---

## 待解决问题

### P1 - 可选优化

- [ ] **lb_entry_time 记录的不是 HTTP 接收时间**
  - `/generate` endpoint 没有设置 `received_time`
  - 当前记录的是 tokenizer_manager 处理时间
  - 对于 Engine 直接调用可以手动设置，HTTP 方式需要修改代码

---

## 已完成任务

### V3 修复 (2026-02-19) - 新增 Retracted Queue 指标

- [x] **新增 `num_retracted_queue_reqs` 指标** - 记录 retracted 队列长度
- [x] **新增 `num_total_queue_reqs` 指标** - 聚合所有队列（含 retracted）
- [x] 在 `decode.py` 中保存 `_decode_retracted_queue_snapshot`
- [x] 在 `scheduler_metrics_mixin.py` 中使用新指标并清零
- [x] 验证：`num_total_queue_reqs = num_queue_reqs + num_retracted_queue_reqs` 始终正确

### V2 修复 (2026-02-19) - 修复 Metrics 重复记录

- [x] **修复 `num_retracted_reqs` 重复记录** - 同一 retraction 被记录 40 次
  - 原因：`self.num_retracted_reqs` 只在 `log_decode_stats()` 中清零（每 40 batch）
  - 修复：添加独立计数器 `_batch_retracted_reqs`，每次记录后清零
- [x] **修复 `num_new_seqs` 重复/保持旧值**
  - 原因：`_decode_new_seqs_snapshot` 设置后不清零
  - 修复：在 `get_new_prebuilt_batch()` 开头初始化为 0，记录后清零

### 基础功能

- [x] SGLang Fake Decode 环境搭建
- [x] Batch Metrics CSV 导出功能实现 (`--export-batch-metrics-to-file`)
- [x] Request Metrics CSV 导出功能实现 (`--export-request-metrics-to-csv`)
- [x] lb_entry_time 传递链修改（HTTP 接收时间 -> Req.time_stats）
- [x] lb_entry_time_perf 添加（用于精确时间间隔计算）
- [x] 测试脚本创建（test_1.py, test_2.py, test_3.py）
- [x] _decode_queue_snapshot 机制添加（用于记录 decode 模式的队列长度）

---

## 下一步行动

1. **进行 mixing 实验**
   - 使用 test_2.py 运行负载测试
   - 分析 batch_metrics_v3.csv 中的调度行为

2. **分析 request_metrics CSV**
   - 验证时间链是否正确：lb_entry_time < wait_queue_entry_time < forward_entry_time < completion_time

---

## tmux 配置

已配置两个 tmux session：
- `sglang_server`: 运行 SGLang server
- `sglang_test`: 运行测试脚本

Claude Code 操作方式：
```bash
# 在 session 中执行命令
tmux send-keys -t sglang_server 'command' Enter
tmux send-keys -t sglang_test 'command' Enter

# 查看输出
tmux capture-pane -t sglang_server -p -S -100
```

---

## 测试命令

```bash
# 激活环境
conda activate sglang_mix
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH

# 启动 server
python -m sglang.launch_server \
    --model-path /data/pretrained_models/Qwen2.5-1.5B-Instruct \
    --port 30000 \
    --disaggregation-mode decode \
    --disaggregation-decode-enable-fake-auto \
    --export-batch-metrics-to-file /home/lg/vidur_or/mixing_experiments_for_DJ/sglang_mixing/results_batch/batch_metrics_test.csv \
    --export-request-metrics-to-csv /home/lg/vidur_or/mixing_experiments_for_DJ/sglang_mixing/results_req/request_metrics_test.csv

# 运行测试（另一个终端）
cd /home/lg/vidur_or/mixing_experiments_for_DJ/sglang_mixing
python test_2.py  # 并行 burst
python test_3.py  # Engine 直接调用
```

---

## 相关文件

| 文件 | 用途 |
|------|------|
| `STATUS.md` | 当前状态和待办（本文件） |
| `NOTES.md` | 技术细节和已知信息 |
| `我的计划文件.md` | 历史记录（可归档） |
| `test_*.py` | 测试脚本 |
| `results_batch/*.csv` | Batch metrics 输出 |
| `results_req/*.csv` | Request metrics 输出 |
