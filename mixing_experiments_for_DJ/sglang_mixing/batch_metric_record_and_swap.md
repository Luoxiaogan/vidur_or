# SGLang Batch Metrics 记录说明与 Preemption 策略分析

## 一、Batch Metrics 字段说明

### CSV 输出字段

| 字段名 | 类型 | 含义 | 数据来源 |
|--------|------|------|---------|
| `batch_id` | int | 全局 batch 计数器 | `self.forward_ct` |
| `timestamp` | float | 记录时刻的时间戳 | `time.time()` |
| `forward_mode` | str | "prefill" 或 "decode" | - |
| `batch_size` | int | batch 中的请求数 | `len(batch.reqs)` |
| `num_tokens` | int | GPU 上已占用的 KV tokens | `_get_token_info()` |
| `token_usage` | float | GPU KV cache 使用率 (0~1) | `num_used / max_total_num_tokens` |
| `batch_num_tokens` | int | **新增** batch 中所有请求的 seq_len 之和 | `batch.seq_lens_cpu.sum().item()` |
| `gpu_num_reqs` | int | **新增** GPU 上所有请求数 | `len(self.running_batch.reqs)` |
| `gen_throughput` | float | 生成吞吐量 (token/s) | `last_gen_throughput` (每40批更新) |
| `num_queue_reqs` | int | waiting_queue 长度 | `len(self.waiting_queue)` |
| `num_retracted_reqs` | int | 被抢占的请求数 | `self.num_retracted_reqs` |
| `num_new_seqs` | int | (Prefill) 本 batch 新加入的请求数 | `len(can_run_list)` |
| `num_new_tokens` | int | (Prefill) 本 batch 新输入的 token 数 | `adder.log_input_tokens` |
| `num_cached_tokens` | int | (Prefill) prefix cache 命中的 token 数 | `adder.log_hit_tokens` |
| `cache_hit_rate` | float | (Prefill) prefix cache 命中率 | `hit_tokens / total_tokens` |

### 两个维度的区分

| 维度 | 请求数字段 | Token数字段 | 含义 |
|------|-----------|------------|------|
| **Batch 维度** | `batch_size` | `batch_num_tokens` | 即将被执行的 batch |
| **GPU 维度** | `gpu_num_reqs` | `num_tokens` | 所有在 GPU KV cache 中的 |

### 记录时刻

| Batch 类型 | 记录函数 | 记录时刻 |
|-----------|---------|---------|
| Prefill batch | `log_prefill_stats()` | 调度之后，执行之前 |
| Decode batch | `log_decode_stats_every_iteration()` | 执行之后，下一轮调度之前 |

---

## 二、Preemption 策略：Recompute vs Swap

### 概念定义

当 KV cache 不足时，scheduler 需要抢占 (preempt/retract) 一些正在运行的请求来释放空间。被抢占的请求有两种恢复策略：

| 策略 | 说明 | KV cache 处理 |
|------|------|--------------|
| **Recompute** | 重新计算 | 直接释放，恢复时重新计算所有 tokens |
| **Swap** | 交换到 CPU | 保存到 CPU，恢复时从 CPU 加载回 GPU |

### SGLang 的实现

#### 普通模式 (Recompute)

```python
# schedule_batch.py - release_req()
def release_req(self, idx: int, ...):
    req = self.reqs[idx]

    # 普通模式：直接释放 KV cache，不保存
    release_kv_cache(req, self.tree_cache, is_insert=False)
    req.reset_for_retract()
```

恢复时：
```python
# init_next_round_input()
def init_next_round_input(self, tree_cache):
    self.fill_ids = self.origin_input_ids + self.output_ids  # 重建完整序列
    # 尝试匹配 prefix cache，减少需要重新计算的 tokens
    if tree_cache is not None:
        match_result = tree_cache.match_prefix(token_ids, ...)
```

#### PD 分离 Decode 模式 (Swap)

```python
# schedule_batch.py - release_req()
def release_req(self, idx: int, ...):
    req = self.reqs[idx]

    if server_args.disaggregation_mode == "decode":
        req.offload_kv_cache(...)  # 保存到 CPU

    release_kv_cache(req, self.tree_cache, is_insert=False)
    req.reset_for_retract()
```

恢复时：
```python
# decode.py - resume_retracted_reqs()
def resume_retracted_reqs(self, ...):
    req.is_retracted = False
    self._pre_alloc(req)  # 重新分配 GPU 内存
    req.load_kv_cache(...)  # 从 CPU 加载回 GPU
```

### 对比总结

| 模式 | Retract 时 KV cache | 恢复时 | 策略 | 需要重新计算 decode？ |
|------|---------------------|--------|------|---------------------|
| **普通模式** (默认) | 直接释放 | 重新计算 `fill_ids` | **Recompute** | 是 |
| **PD 分离 decode** | Offload 到 CPU | 从 CPU load 回 GPU | **Swap** | 否 |

### 为什么 PD 分离模式只能用 Swap？

1. **Decode worker 不具备 prefill 能力**：PD 分离架构中，decode worker 只负责 decode，不做 prefill 计算
2. **Fake decode 的 KV cache 来源**：
   - 正常 PD 分离：KV cache 从 prefill worker 传输
   - Fake decode：KV cache 是"假的"（伪造/跳过）
3. **Recompute 需要重新做 prefill**：decode worker 没有这个能力

### 为什么普通模式用 Recompute？

根据 vLLM 文档的解释：
> "Recomputation is used by default since it incurs lower overhead than swapping."

原因：
1. **内存效率**：不需要额外的 CPU 内存来保存 KV cache
2. **实现简单**：不需要 GPU↔CPU 数据传输
3. **Prefix cache 加速**：如果有 prefix cache 命中，recompute 开销可以大大减少

---

## 三、与 Vidur 的对应关系

| 概念 | SGLang | Vidur |
|------|--------|-------|
| 抢占请求数 | `num_retracted_reqs` | `num_restarts_in_scheduling` |
| 抢占操作 | `retract` | `restart` |
| PD 分离恢复 | `load_kv_cache()` 从 CPU 加载 | `_pd_restart()` 模拟加载 |

---

## 四、使用方式

```bash
# 启动 server（fake decode 模式）
python -m sglang.launch_server \
    --model-path /data/pretrained_models/Qwen2.5-1.5B-Instruct \
    --port 30000 \
    --disaggregation-mode decode \
    --disaggregation-decode-enable-fake-auto \
    --export-batch-metrics-to-file /path/to/batch_metrics.csv
```

输出示例：
```csv
batch_id,timestamp,forward_mode,batch_size,num_tokens,token_usage,batch_num_tokens,gpu_num_reqs,gen_throughput,num_queue_reqs,num_retracted_reqs,...
0,1705123456.123,decode,100,100201,0.043,100101,100,0.0,0,0,...
```
