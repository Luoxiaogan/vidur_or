# KV Cache 容量计算工具

计算给定 GPU 和模型配置下的 KV Cache 容量 C。

## 功能

- 直接使用 vidur 的 `MemoryPlanner` 和 `ReplicaConfig` 计算实际容量
- 支持 vidur 中定义的所有 GPU 和模型配置
- 输出 `max_batch_size`、`num_blocks`、`C_tokens` 等关键指标
- 支持 JSON 格式输出

## 前置要求

```bash
# 激活 conda 环境
conda activate qzh
```

## 使用方法

```bash
# 默认配置 (A100 + Llama-3-8B, max_tokens=4096)
python compute_c.py

# WAIT 实验配置 (prefill=60, decode=200 → max_tokens=260)
python compute_c.py --max-tokens 260

# 完整配置
python compute_c.py \
    --device a100 \
    --model "meta-llama/Meta-Llama-3-8B" \
    --max-tokens 260 \
    --block-size 16 \
    --memory-margin 0.1 \
    --tp 1 \
    --pp 1

# JSON 格式输出
python compute_c.py --max-tokens 260 --json
```

## 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--device` | a100 | GPU 类型 (a40, a100, h100) |
| `--model` | meta-llama/Meta-Llama-3-8B | 模型名称 |
| `--max-tokens` | 4096 | 单请求最大 token 数 |
| `--block-size` | 16 | KV cache block 大小 |
| `--memory-margin` | 0.1 | 内存预留比例 |
| `--tp` | 1 | Tensor parallel size |
| `--pp` | 1 | Pipeline parallel stages |
| `--json` | - | 输出 JSON 格式 |

## 关键参数计算原理

### max_tokens

**含义**：单个请求的最大序列长度（prefill + decode tokens）

**默认值**：4096（vidur 默认）

**计算影响**：
```
每请求 KV Cache = 4 × head_dim × kv_heads × num_layers × max_tokens
               = 4 × 128 × 8 × 32 × max_tokens
               = 131,072 × max_tokens bytes

max_batch_size = KV Cache 可用内存 / 每请求 KV Cache
```

**示例对比** (A100 + Llama-3-8B)：

| max_tokens | 每请求 KV Cache | max_batch_size | C_tokens |
|------------|----------------|----------------|----------|
| 260 (实际需要) | 32.5 MB | 1858 | ~505k |
| 4096 (默认) | 512 MB | 118 | ~483k |

**建议**：设置为实际的 `prefill + decode` 值，避免内存槽位浪费。

### memory_margin_fraction

**含义**：GPU 显存预留比例，用于激活值、临时缓冲区等动态内存

**默认值**：0.1（即 10%）

**计算影响**：
```
可用显存 = 总显存 × (1 - memory_margin_fraction)
KV Cache 可用 = 可用显存 - 模型参数内存

对于 A100 80GB + Llama-3-8B:
  可用显存 = 80 × 0.9 = 72 GB
  模型参数 = 13 GB
  KV Cache 可用 = 72 - 13 = 59 GB
```

### 总容量 C 的本质

**关键洞察**：KV Cache 的总内存容量是固定的（由 GPU 和模型决定），`max_tokens` 只影响如何"切分"这块内存：

- **小 max_tokens** → 多请求、短序列（如 1858 × 260）
- **大 max_tokens** → 少请求、长序列（如 118 × 4096）
- **总容量本质相同**：~59 GB

## 输出示例

```
============================================
KV Cache 容量计算结果
============================================

[配置]
  GPU: a100 (80 GB)
  模型: meta-llama/Meta-Llama-3-8B
  max_tokens: 260
  block_size: 16
  memory_margin: 0.1
  tensor_parallel: 1
  pipeline_stages: 1

[模型信息]
  num_layers: 32
  num_q_heads: 32
  num_kv_heads: 8
  embedding_dim: 4096
  attention_head_dim: 128

[内存分配]
  可用显存: 72.00 GB
  模型参数内存: 13.00 GB
  KV Cache 可用: 59.00 GB
  每请求 KV Cache: 32.50 MB

[容量结果]
  max_batch_size (C_requests): 1996
  max_request_slots: 1996
  num_blocks: 33932
  C_tokens: 542912
============================================
```

## 输出字段说明

| 字段 | 说明 |
|------|------|
| `max_batch_size` | 最大并发请求数（C in requests） |
| `max_request_slots` | 最大请求槽位数 = max_batch_size × pipeline_stages |
| `num_blocks` | KV cache 总块数 |
| `C_tokens` | KV cache 总 token 容量 = num_blocks × block_size |

## 与理论公式的对应

在 WAIT 算法分析中：
- $C$ = `C_tokens`
- $M^* < C$ 是稳态条件

详细分析见 [`../.docs/kv_cache_capacity_analysis.md`](../.docs/kv_cache_capacity_analysis.md)
