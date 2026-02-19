# SGLang Mixing 实验 - 技术笔记

## 1. 环境配置

### 1.1 Conda 环境

```bash
conda activate sglang_mix
export LD_LIBRARY_PATH=$CONDA_PREFIX/lib:$LD_LIBRARY_PATH
```

### 1.2 RDMA 依赖

SGLang PD 分离模式需要 RDMA 库（即使没有真实硬件）：

```bash
conda install -c conda-forge rdma-core -y
```

---

## 2. SGLang Fake Decode 模式

### 2.1 概念

Fake decode 模式模拟 PD 分离架构中的 decode 节点：
- **跳过** prefill 计算
- **跳过** KV cache 传输（FakeKVReceiver 直接返回成功）
- **分配** KV cache 内存（基于 prompt_tokens 数量）
- **真实执行** decode
- **输出乱码**（KV cache 未初始化）

### 2.2 启动命令

```bash
python -m sglang.launch_server \
    --model-path /data/pretrained_models/Qwen2.5-1.5B-Instruct \
    --port 30000 \
    --disaggregation-mode decode \
    --disaggregation-decode-enable-fake-auto \
    --export-batch-metrics-to-file /path/to/batch.csv \
    --export-request-metrics-to-csv /path/to/request.csv
```

### 2.3 请求格式

```json
{
  "text": "your prompt here",
  "sampling_params": {"max_new_tokens": 100, "ignore_eos": true},
  "bootstrap_host": "2.2.2.2",
  "bootstrap_room": 0
}
```

- `bootstrap_host: "2.2.2.2"` 是 FAKE_BOOTSTRAP_HOST，表示使用 fake 模式
- `ignore_eos: true` 强制生成精确数量的 tokens

---

## 3. SGLang 代码修改

### 3.1 修改的文件

| 文件 | 修改内容 |
|------|----------|
| `server_args.py` | 添加 CLI 参数 `--export-batch-metrics-to-file`, `--export-request-metrics-to-csv` |
| `scheduler_metrics_mixin.py` | BatchMetrics (含 V3 新字段), RequestMetrics 数据类; CSV Exporter; 初始化和记录逻辑; V2/V3 清零逻辑 |
| `scheduler_output_processor_mixin.py` | `_export_request_metrics()` 方法; completion 时调用 |
| `io_struct.py` | `received_time`, `received_time_perf` 字段 |
| `tokenizer_manager.py` | 传递 `received_time`, `received_time_perf` |
| `scheduler.py` | 设置 `req.time_stats.lb_entry_time`, `lb_entry_time_perf`; V2: `_batch_retracted_reqs` |
| `collector.py` | TimeStats 添加 `lb_entry_time`, `lb_entry_time_perf` |
| `decode.py` | `_decode_queue_snapshot`, `_decode_retracted_queue_snapshot` (V3), `_decode_new_seqs_snapshot` (V2) |

### 3.2 Git 提交

```
commit 3bedccf69faf52127216b64dcc156d9c39382e0a
Author: WhiteGiver-Plus
Date:   Fri Jan 30 02:43:09 2026 +0800
Subject: My modifications for mixing experiments
```

---

## 4. Metrics 字段说明

### 4.1 Batch Metrics (17 列)

| 字段 | 类型 | 含义 |
|------|------|------|
| `batch_id` | int | 全局 batch 计数器 |
| `timestamp` | float | 记录时刻 (time.time()) |
| `forward_mode` | str | "prefill" 或 "decode" |
| `batch_size` | int | batch 中的请求数 |
| `num_tokens` | int | GPU KV cache 已占用 tokens |
| `token_usage` | float | GPU KV cache 使用率 (0~1) |
| `batch_num_tokens` | int | batch 中所有请求的 seq_len 之和 |
| `gpu_num_reqs` | int | GPU 上所有请求数 |
| `gen_throughput` | float | 生成吞吐量 (token/s) |
| `num_queue_reqs` | int | 等待队列长度 (不含 retracted) |
| `num_retracted_reqs` | int | 该 batch 被抢占的请求数 |
| `num_retracted_queue_reqs` | int | **(V3)** retracted 队列长度 |
| `num_total_queue_reqs` | int | **(V3)** 总队列长度 (含 retracted) |
| `num_new_seqs` | int | 新加入 GPU 的请求数 |
| `num_new_tokens` | int | (Prefill) 新输入的 token 数 |
| `num_cached_tokens` | int | (Prefill) prefix cache 命中 tokens |
| `cache_hit_rate` | float | (Prefill) prefix cache 命中率 |

### 4.2 Request Metrics (21 列)

| 字段 | 类型 | 含义 |
|------|------|------|
| `rid` | str | 请求 ID |
| `seqlen` | int | 总序列长度 |
| `extend_input_len` | int | extend batch 处理的 token 数 |
| `cached_tokens` | int | 缓存命中的 token 数 |
| `finished_reason` | str | 完成原因 (JSON) |
| `finished_len` | int | 完成位置 |
| `lb_entry_time` | float | HTTP 接收时间 (epoch) |
| `lb_entry_time_perf` | float | HTTP 接收时间 (perf_counter) |
| `decode_prealloc_queue_entry_time` | float | 进入预分配队列时间 |
| `decode_transfer_queue_entry_time` | float | 进入传输队列时间 |
| `wait_queue_entry_time` | float | 进入等待队列时间 |
| `forward_entry_time` | float | 进入 GPU 执行时间 |
| `completion_time` | float | 完成时间 |
| `retraction_count` | int | 被 retract 次数 |
| `is_retracted` | bool | 当前是否被 retract |
| `retracted_stain` | bool | 是否曾被 retract |
| `kv_committed_len` | int | 已提交的 KV 长度 |
| `kv_allocated_len` | int | 已分配的 KV 长度 |
| `input_len` | int | 输入长度 |
| `output_len` | int | 输出长度 |
| `disagg_mode` | str | 分离模式 |

### 4.3 时间戳类型

| 字段 | 时钟类型 | 用途 |
|------|----------|------|
| `lb_entry_time` | `time.time()` | epoch 时间戳，用于绝对排序 |
| `lb_entry_time_perf` | `time.perf_counter()` | 相对时间，用于精确间隔计算 |
| 其他 time_stats | `time.perf_counter()` | 相对时间 |

**计算示例**：
- 绝对排序: 使用 `lb_entry_time`
- 队列等待时间: `wait_queue_entry_time - lb_entry_time_perf`

---

## 5. 测试脚本说明

| 脚本 | 方式 | 特点 |
|------|------|------|
| `test_1.py` | HTTP + 泊松过程 | 按泊松到达时间发送，需要大连接池 |
| `test_2.py` | HTTP + 并行 burst | 一次性并行发送所有请求 |
| `test_3.py` | Engine 直接调用 | 绕过 HTTP，精确控制到达时间 |

### 5.1 test_3.py 关键代码

```python
# 直接调用 tokenizer_manager，设置精确的 received_time
req = GenerateReqInput(
    text=prompt,
    sampling_params=sampling_params,
    bootstrap_host="2.2.2.2",
    bootstrap_room=0,
    received_time=actual_submit_time,  # 精确控制到达时间
)
async for response in tokenizer_manager.generate_request(req, request=None):
    final_response = response
```

---

## 6. Preemption 策略

### 6.1 普通模式 (Recompute)

- Retract 时: 直接释放 KV cache
- 恢复时: 重新计算 `fill_ids`

### 6.2 PD 分离 Decode 模式 (Swap)

- Retract 时: `req.offload_kv_cache()` 保存到 CPU
- 恢复时: `req.load_kv_cache()` 从 CPU 加载回 GPU

**为什么 PD 分离只能用 Swap**: Decode worker 不具备 prefill 能力，无法 recompute。

---

## 7. 与 Vidur 的对应关系

| 概念 | SGLang | Vidur |
|------|--------|-------|
| 抢占请求数 | `num_retracted_reqs` | `num_restarts_in_scheduling` |
| 抢占操作 | `retract` | `restart` |
| PD 分离恢复 | `load_kv_cache()` | `_pd_restart()` |

---

## 8. V2/V3 修复记录

### 8.1 V2 修复 - Metrics 重复记录问题

**问题 1: `num_retracted_reqs` 重复记录**
- 现象：同一 retraction 被记录 40 次
- 原因：`self.num_retracted_reqs` 只在 `log_decode_stats()` 中清零（每 40 batch）
- 修复：添加独立计数器 `_batch_retracted_reqs`，在 `scheduler.py:2195` 设置，记录后清零

**问题 2: `num_new_seqs` 重复/保持旧值**
- 现象：无新请求时仍显示旧值
- 原因：`_decode_new_seqs_snapshot` 设置后不清零
- 修复：在 `get_new_prebuilt_batch()` 开头初始化为 0，记录后清零

### 8.2 V3 修复 - Retracted Queue 不可见问题

**问题: `num_queue_reqs` 突然跳变**
- 现象：retracted 请求被 resume 时，`num_queue_reqs` 突然增加
- 原因：`_decode_queue_snapshot` 不包含 `retracted_queue`

**修复方案：新增两个指标**
```python
# decode.py:985
self._decode_retracted_queue_snapshot = retracted_queue_len

# scheduler_metrics_mixin.py:639-640
num_retracted_queue_reqs=retracted_queue_reqs,
num_total_queue_reqs=queue_reqs + retracted_queue_reqs,
```

**指标含义：**
| 指标 | 含义 |
|------|------|
| `num_queue_reqs` | prealloc + transfer + waiting（不变） |
| `num_retracted_queue_reqs` | retracted 队列长度（新增） |
| `num_total_queue_reqs` | 全部队列总和（新增） |

---

## 9. 代码位置快速参考

| 功能 | 文件 | 行号 |
|------|------|------|
| BatchMetrics 定义 | `scheduler_metrics_mixin.py` | 59-84 |
| RequestMetrics 定义 | `scheduler_metrics_mixin.py` | 105-142 |
| Batch CSV 导出初始化 | `scheduler_metrics_mixin.py` | 234-239 |
| Request CSV 导出初始化 | `scheduler_metrics_mixin.py` | 241-246 |
| Prefill batch metrics 记录 | `scheduler_metrics_mixin.py` | 409-432 |
| Decode batch metrics 记录 | `scheduler_metrics_mixin.py` | 622-647 |
| Request metrics 导出 | `scheduler_output_processor_mixin.py` | 添加的方法 |
| _decode_queue_snapshot 设置 | `decode.py` | 980-985 |
| _decode_retracted_queue_snapshot 设置 | `decode.py` | 985 |
| _decode_new_seqs_snapshot 初始化 | `decode.py` | 964 |
| _batch_retracted_reqs 设置 | `scheduler.py` | 2195 |
| _get_num_queue_reqs | `scheduler_metrics_mixin.py` | 248-257 |
