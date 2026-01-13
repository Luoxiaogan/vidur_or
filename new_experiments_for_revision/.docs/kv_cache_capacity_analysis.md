# KV Cache 容量 C 计算分析

## 1. 问题背景

在 LLM 推理服务中，**C（KV Cache 容量）** 是指 GPU 显存中可分配给 KV cache 的最大 token 数。这是系统的硬性约束，决定了：

- 最大并发请求数
- 最大批处理大小
- 系统吞吐量上限

在 WAIT 算法的理论分析中（见 `实验设计的思考.md`），我们需要知道 C 来：
1. 验证 $M^* < C$ 的稳态条件
2. 分析系统容量约束下的最优 threshold $n^*$

**关键发现**：C 可以从 GPU 和模型配置中**提前计算**，无需运行模拟。

---

## 2. Vidur 中的内存模型

### 2.1 核心类

| 类 | 文件 | 功能 |
|----|------|------|
| `MemoryPlanner` | `vidur/scheduler/utils/memory_planner.py` | 计算 KV cache 容量 |
| `ParamCounter` | `vidur/utils/param_counter.py` | 计算模型参数量 |
| `Replica` | `vidur/entities/replica.py` | GPU 副本属性 |

### 2.2 内存分配公式

GPU 显存分配：
```
总显存 = 模型参数内存 + KV Cache 内存 + 预留内存

可用显存 = 总显存 × (1 - memory_margin_fraction)
KV Cache 可用 = 可用显存 - 模型参数内存
```

---

## 3. 计算公式推导

### 3.1 模型参数内存

对于 Transformer 模型，每层参数包括：

**Attention 层**：
```
Wq: embedding_dim × (attention_head_dim × q_heads / TP)
Wk: embedding_dim × (attention_head_dim × kv_heads / TP)
Wv: embedding_dim × (attention_head_dim × kv_heads / TP)
Wo: embedding_dim × (attention_head_dim × q_heads / TP)
```

**MLP 层**（Gated MLP）：
```
3 × embedding_dim × mlp_hidden_dim / TP
```

**每设备参数总量**：
```
params_per_device = params_per_layer × (num_layers / num_pipeline_stages)
parameter_memory = params_per_device × 2  # FP16 = 2 bytes
```

### 3.2 KV Cache 内存

每层每请求的 KV cache：
```
kv_cache_per_layer = 2 × 2 × attention_head_dim × kv_heads_per_tp_worker × max_tokens
                   = 4 × attention_head_dim × kv_heads_per_tp_worker × max_tokens
```

其中：
- 第一个 2：FP16 = 2 bytes
- 第二个 2：Key 和 Value 各一份

每设备每请求的 KV cache：
```
kv_cache_per_request = kv_cache_per_layer × num_layers
```

### 3.3 容量 C 计算

**max_batch_size（最大并发请求数）**：
```
max_batch_size = (available_memory - parameter_memory) / kv_cache_per_request
```

**num_blocks（KV cache 块数）**：
```
max_blocks_per_sequence = max_tokens / block_size
num_blocks = max_blocks_per_sequence × max_batch_size × num_pipeline_stages
```

**C_tokens（总 token 容量）**：
```
C_tokens = num_blocks × block_size
```

---

## 4. 具体计算示例

### 4.1 配置

**GPU 配置 (A100 80GB)**：
```python
total_memory_gb = 80
memory_margin_fraction = 0.1  # 10% 预留
```

**模型配置 (Meta-Llama-3-8B)**：
```python
num_layers = 32
num_q_heads = 32
num_kv_heads = 8  # GQA
embedding_dim = 4096
mlp_hidden_dim = 14336
use_gated_mlp = True
```

**调度器配置**：
```python
block_size = 16
tensor_parallel_size = 1
num_pipeline_stages = 1
max_tokens = 260  # prefill(60) + decode(200)
```

### 4.2 计算过程

**Step 1: 基础维度**
```python
attention_head_dim = 4096 / 32 = 128
kv_heads_per_tp_worker = ceil(8 / 1) = 8
```

**Step 2: 模型参数内存**
```python
# Attention
attention_params = 4096 × 128 × (32 + 8 + 8 + 32) = 41,943,040

# MLP (gated)
mlp_params = 3 × 4096 × 14336 = 176,160,768

# 每层总参数
params_per_layer = 218,103,808

# 每设备参数 (32层, PP=1)
params_per_device = 218,103,808 × 32 = 6,979,321,856

# 参数内存 (FP16)
parameter_memory = 6,979,321,856 × 2 = 13.96 GB
```

**Step 3: KV Cache 内存**
```python
# 每层每请求
kv_cache_per_layer = 4 × 128 × 8 × 260 = 1,064,960 bytes

# 每设备每请求
kv_cache_per_request = 1,064,960 × 32 = 34,078,720 bytes = 32.5 MB
```

**Step 4: 容量计算**
```python
# 可用内存
available_memory = 80 × 0.9 × 1024³ = 77.31 GB

# KV cache 可用
memory_for_kv = 77.31 - 13.96 = 63.35 GB

# 最大批处理大小
max_batch_size = 63.35 GB / 32.5 MB ≈ 1,996 请求

# num_blocks
max_blocks_per_seq = 260 / 16 = 16.25 → 17 (向上取整)
num_blocks = 17 × 1996 × 1 = 33,932 blocks

# C_tokens
C_tokens = 33,932 × 16 = 542,912 tokens
```

### 4.3 不同 max_tokens 的影响

| max_tokens | max_batch_size | num_blocks | C_tokens |
|------------|----------------|------------|----------|
| 260 | ~1,996 | ~33,932 | ~542,912 |
| 512 | ~1,016 | ~32,512 | ~520,192 |
| 1024 | ~509 | ~32,576 | ~521,216 |
| 4096 (默认) | ~127 | ~32,512 | ~520,192 |

**观察**：C_tokens 相对稳定，因为总 KV cache 内存是固定的。

---

## 5. 与理论公式的对应

在 `实验设计的思考.md` 中，定义：
- $C$：GPU memory 决定的最大并发 token 数

对应到 vidur：
```
C = C_tokens = num_blocks × block_size
```

理论公式中的 Batch Token 数：
$$M(n) = n \cdot l_1 \cdot \bar{l}$$

稳态条件要求：
$$M^* = \frac{d_0 l_1 \bar{l} \lambda}{1 - d_1 l_1 \bar{l} \lambda} < C$$

---

## 6. 使用方法

使用 `compute_total_memory/compute_c.py` 脚本计算：

```bash
# 默认配置
python compute_c.py

# 指定配置
python compute_c.py \
    --device a100 \
    --model "meta-llama/Meta-Llama-3-8B" \
    --max-tokens 260 \
    --block-size 16
```

---

## 7. 关键发现总结

1. **C 可提前计算**：只依赖于硬件和模型配置，不需要运行模拟
2. **max_tokens 的选择**：影响 max_batch_size，但 C_tokens 相对稳定
3. **内存分配**：模型参数约占 18%，KV cache 约占 82%（在 A100 80GB + Llama-3-8B 配置下）
4. **与 vidur 代码对应**：`MemoryPlanner.get_max_batch_size()` 是核心计算方法
