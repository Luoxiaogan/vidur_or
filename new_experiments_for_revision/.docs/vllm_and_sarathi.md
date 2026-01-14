# vLLM 与 Sarathi 调度器参数详解

本文档详细分析 vLLM 和 Sarathi 两种调度器的核心参数，以及如何与 WAIT 算法进行公平比较。

---

## 问题 1: vLLM 的 `max_tokens_in_batch`

### 代码分析

`vllm_replica_scheduler.py:81-83`:

```python
next_num_tokens = self._get_request_next_num_tokens(request)  # <- 关键

new_num_tokens = num_tokens + [next_num_tokens]
new_num_batch_tokens = len(new_num_tokens) * max(new_num_tokens)  # <- 矩形计算!
if new_num_batch_tokens > self._config.max_tokens_in_batch:
    break
```

`_get_request_next_num_tokens` 定义在 `base_replica_scheduler.py:95-101`:

```python
def _get_request_next_num_tokens(self, request: Request) -> int:
    if request.is_prefill_complete:
        return 1                         # decode -> 贡献 1
    return request.num_prefill_tokens    # prefill -> 贡献 630
```

### 关键公式

```
new_num_batch_tokens = len(requests) × max(num_tokens)
```

这是**矩形填充计算**（模拟 GPU padding）：

| Batch 组成 | 计算方式 | 结果 |
|-----------|---------|------|
| 1 个 prefill(630) + 10 个 decode(1) | 11 × max(630,1) | 6930 (不是 640) |
| 6 个 prefill(630) | 6 × 630 | 3780 |
| 100 个 decode(1) | 100 × 1 | 100 |

### 结论

`max_tokens_in_batch` 是这个 batch 要计算的 token 数（考虑 padding 开销），不是简单求和。

**默认值 4096** 意味着：最多约 6 个 prefill(630) 的请求，或者 4096 个纯 decode 请求。

---

## 问题 2: vLLM 的 `batch_size_cap`

### 代码分析

代码中有两处检查：

**检查 1** (`vllm_replica_scheduler.py:86`):

```python
if len(self._allocation_map) == self._config.batch_size_cap:
    break
```

`_allocation_map` 是所有当前持有 KV cache 的请求（包括 running + preempted）。

**检查 2** (`vllm_replica_scheduler.py:89`):

```python
if len(requests) == self._max_micro_batch_size:
    break
# 其中 self._max_micro_batch_size = batch_size_cap // num_stages
```

### 结论

- `batch_size_cap` 限制的是**系统中同时存在的请求数上限**（不只是单个 batch）
- `max_micro_batch_size = batch_size_cap // num_stages` 限制单个 batch 的请求数

对于 `pipeline_stages=1` 的情况：`max_micro_batch_size = batch_size_cap = 128`

---

## 问题 3: Sarathi 的 `chunk_size` 和 `batch_size_cap`

### `chunk_size`

Sarathi 重写了 `_get_request_next_num_tokens` (`sarathi_replica_scheduler.py:69-84`):

```python
def _get_request_next_num_tokens(
    self, request: Request, batch_contains_prefill: bool, num_batch_tokens: int
) -> int:
    if request.is_prefill_complete:
        return 1

    next_num_tokens = min(
        request.num_prefill_tokens - request.num_processed_tokens,  # 剩余 prefill
        self._config.chunk_size - num_batch_tokens,                 # chunk 剩余空间
    )
    return max(0, next_num_tokens)
```

然后在 `_get_next_batch` 中：

```python
num_batch_tokens += next_num_tokens  # <- 简单累加，不是矩形!
```

### 关键差异

**Sarathi 是简单求和，不是矩形计算。**

| Batch 组成 | 计算方式 | 结果 |
|-----------|---------|------|
| 1 个 partial prefill + 10 个 decode | sum | 实际 token 总和 |
| chunk_size=512, prefill=630 | 分块 | 第1批512, 第2批118 |

### 结论

`chunk_size` 是一个 batch 中实际要计算的 token 总数上限（简单求和）。

这就是 **Chunked Prefill** 的核心机制：
- prefill=630, chunk_size=512
- 第 1 个 batch：处理 512 tokens（prefill 未完成）
- 第 2 个 batch：处理剩余 118 tokens（prefill 完成）

### `batch_size_cap`

与 vLLM 相同：

```python
if len(self._allocation_map) == self._config.batch_size_cap:
    break
```

**结论**：系统中同时存在的请求数上限。

---

## 总结对比表

| 参数 | vLLM | Sarathi |
|-----|------|---------|
| token 计算 | `len × max` (矩形) | `sum` (实际) |
| `max_tokens_in_batch` | batch 计算量上限 (含 padding) | N/A |
| `chunk_size` | N/A | batch 计算量上限 (无 padding) |
| `batch_size_cap` | 系统中请求数上限 | 系统中请求数上限 |
| Chunked Prefill | 不支持 | 支持 |

---

## 你的配置下的影响

### PREFILL_TOKENS = 630 时：

**vLLM** (默认 `max_tokens_in_batch=4096`):
- 纯 prefill batch：最多 4096/630 ≈ 6 个请求
- 混合 batch (1 prefill + N decode)：受 prefill 拖累，4096/630 ≈ 6 个请求

**Sarathi** (默认 `chunk_size=512`):
- 每个 batch 最多 512 tokens
- prefill=630 需要 2 个 batch 完成
- 几乎不可能在一个 batch 中同时处理 prefill 和 decode

---

## 公平比较的几种思路

### 思路 1: 移除人为限制，只保留物理约束（内存）

```python
vLLM:    max_tokens_in_batch = 1000000, batch_size_cap = 2000
Sarathi: chunk_size = 1000000, batch_size_cap = 2000
WAIT:    total_limit = 720
```

| 优点 | 缺点 |
|-----|------|
| 三者都只受内存约束，比较的是调度策略本身 | vLLM/Sarathi 会退化成"尽可能塞满内存"的模式 |

---

### 思路 2: 让稳态吞吐能力对齐

**核心思想**：调整参数使三种调度器在稳态下能处理相似的最大吞吐量，然后比较 latency。

但这有个问题：三种调度器的工作模式不同：

| 调度器 | 稳态行为 |
|-------|---------|
| WAIT | 固定 batch_size=720，等 threshold 满足才调度 |
| vLLM | 动态 batch_size，只要有请求+有内存就调度 |
| Sarathi | 动态 batch_size + Chunked Prefill |

**vLLM/Sarathi 没有"等待"的概念，它们会立即调度。**

---

### 思路 3: 让计算资源对齐

让每个 batch 处理相似的计算量。

你的 WAIT 稳态：`batch_num_tokens ≈ 23364`

**问题**：
- vLLM 用矩形计算：设 `max_tokens_in_batch = 23364` 会导致纯 prefill batch 只有 23364/630 ≈ 37 个请求
- 但混合 batch (prefill + decode) 会被 prefill 拖累，请求数更少

这导致 vLLM 在高负载下处理能力被削弱，不公平。

---

## 建议：分层比较

### 第一层：相同内存约束，移除人为限制

**目的**：比较调度策略在内存瓶颈下的表现

```python
# 共同参数
GPU = "a100"
MODEL = "meta-llama/Meta-Llama-3-8B"
MEMORY_MARGIN = 0.1
BLOCK_SIZE = 16

# vLLM - 移除 token 限制
max_tokens_in_batch = 1000000  # 足够大，不成为瓶颈
batch_size_cap = 2000

# Sarathi - 移除 chunk 限制
chunk_size = 1000000           # 足够大，不成为瓶颈
batch_size_cap = 2000

# WAIT - 使用你计算的最优 threshold
total_limit = 720              # n* × l1 = 36 × 20
```

**比较内容**：
- 在 arrival_rate = 17, 18, 19, 20, 21 等不同负载下
- throughput（吞吐量）
- mean latency（平均延迟）
- P99 latency（尾部延迟）

---

### 第二层（可选）：真实部署配置

如果想模拟真实系统的行为：

```python
# vLLM 典型配置（针对长 prefill 调大）
max_tokens_in_batch = 16384    # 常见值：4096, 8192, 16384
batch_size_cap = 256

# Sarathi 典型配置
chunk_size = 2048              # 常见值：512, 1024, 2048
batch_size_cap = 256
```

---

## 为什么思路 1 是最公平的？

**核心论点**：三种调度器解决的是同一个问题——在有限 GPU 内存下，如何调度请求以优化 throughput-latency 权衡。

| 方面 | 说明 |
|-----|------|
| 相同的物理约束 | GPU 内存是真实限制，无法绕过 |
| 公平的起点 | 三者都有相同的内存容量 |
| 策略差异凸显 | WAIT 主动控制 vs vLLM/Sarathi 被动适应 |

移除 `max_tokens_in_batch` 和 `chunk_size` 的人为限制后：
- **vLLM** 会贪婪地塞满内存
- **Sarathi** 也会贪婪地塞满内存（但可能有 partial prefill）
- **WAIT** 会等待到 threshold 才调度

### 预期结果差异

| 场景 | 预期表现 |
|-----|---------|
| 低负载 | vLLM/Sarathi 可能 latency 更低（立即调度）|
| 高负载 | WAIT 可能 throughput 更稳定（避免内存碎片和抢占）|
| 尾部延迟 | WAIT 可能更稳定（batch 大小固定）|

---

## 具体实验参数建议

```python
# ============ 公共配置 ============
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"
PREFILL_TOKENS = 630
DECODE_TOKENS = 20
MAX_TOKENS = 650
MEMORY_MARGIN_FRACTION = 0.1
NUM_REQUESTS = 6000
ARRIVAL_RATES = [17, 18, 19, 20, 21, 22]  # 测试不同负载

# ============ WAIT ============
WAIT_CONFIG = {
    "total_limit": 720,  # n* × l1
}

# ============ vLLM ============
VLLM_CONFIG = {
    "max_tokens_in_batch": 1000000,  # 不限制
    "batch_size_cap": 2000,          # 不限制
    "watermark_blocks_fraction": 0.01,
}

# ============ Sarathi ============
SARATHI_CONFIG = {
    "chunk_size": 1000000,  # 不限制
    "batch_size_cap": 2000, # 不限制
    "watermark_blocks_fraction": 0.01,
}
```
