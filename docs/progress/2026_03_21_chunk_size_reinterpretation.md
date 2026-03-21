# WAIT-CP chunk_size 语义重新定义 - 2026-03-21

## 状态
🚧 进行中（发现关键实现错误，准备重写）

## 概要

发现 Sarathi 的 chunk_size 实现（total batch token budget）与 WAIT-CP paper 的 chunk_size 语义（per-request chunk 大小）存在根本差异。这个差异导致 booking limit 被完全架空，是之前所有实验 TIE/LOSE 的根因。

## 核心发现

### chunk_size 的两种语义

| | Sarathi 实现 | WAIT-CP paper 意图 |
|---|---|---|
| chunk_size 含义 | batch 总 token 预算 | 每个请求的 prefill chunk 大小 |
| 每 batch prefill 请求数 | 通常 1 个（预算被 1 个占满） | per_stage_limit 个（多个并行） |
| batch 总 tokens | = chunk_size（固定） | = P × chunk_size + n_decode（随 P 变化） |
| booking limit 作用 | 被架空（chunk 是真正瓶颈） | 控制 P → 控制 batch 大小 |

### 为什么之前 booking limit 永远不生效

```
Sarathi 实现: chunk_size = 512 (batch 总预算)
  → 10 decode (10 tokens) + 1 prefill (502 tokens) = 512
  → 每 batch 只能 admit 1 个 prefill
  → in-system ≈ 1 + l₁/K = 11 (结构性上限)
  → 任何 tl ≥ 11 不 binding → = Sarathi
  → 任何 tl < 11 降 throughput → 更差

正确实现: chunk_size = 512 (per-request chunk)
  → per_stage_limit P = tl / (K + l₁)
  → 每 batch: P 个请求各做 512 tokens prefill
  → batch 总 tokens = P × 512 + n_decode
  → in-system = tl (booking limit 直接控制！)
  → tl 成为真正的 admission controller
```

### 正确的 flow balance

```
P = tl / (K + l₁)                    # 每 batch 完成 prefill 的请求数
K = ceil(l₀ / chunk_size)            # 每个 prefill 的 chunk 数
in_system = P × (K + l₁) = tl       # 总 in-system = booking limit

每 batch:
  prefill tokens = P × chunk_size     # P 个请求各做一个 chunk
  decode tokens  = P × l₁            # P × l₁ 个 decode 各 1 token
  总 tokens = P × (chunk_size + l₁)

示例 (tl=100, chunk=128, l₀=630, l₁=20):
  K = ceil(630/128) = 5
  P = 100 / (5+20) = 4
  每 batch: 4 × 128 + 80 = 592 prefill + 80 decode = 672 tokens
  in-system = 100 (booking limit 控制)
```

### 对 Sarathi 对比的影响

同 chunk_size=128 (per-request)：
- **Sarathi（无 booking limit）**: P 不受限 → in-system 增长到内存上限 → batch 巨大 → 慢
- **WCP（tl=100）**: P=4 → in-system=100 → batch 受控 → 快

**这才是 booking limit 发挥作用的正确场景！**

## 需要的代码改动

### `_get_next_batch()` 重写要点

```python
# 旧实现 (Sarathi 语义)
num_batch_tokens = batch_count  # decode tokens
available = self._chunk_size - num_batch_tokens  # 剩余预算
next_num = min(remaining_prefill, available)  # 一个请求占满预算

# 新实现 (per-request chunk 语义)
# 每个 prefill 请求最多处理 chunk_size tokens（独立预算）
# 同时处理多个 prefill 请求（数量由 booking limit 控制）
next_num = min(remaining_prefill, self._chunk_size)  # per-request 独立
# 循环处理 remain 个请求，每个各自 chunk
```

### Sarathi baseline 也需要更新

为公平对比，Sarathi 也应该使用 per-request chunk 语义（或保持原实现作为"无 booking limit"的对照）。

## 实验结果 (2026-03-21 验证通过!)

**重写 `_get_next_batch()` 后全 rate 全胜：**

chunk=128 (per-request), rate={12..20}, 掐头去尾 metric:

| rate | Sarathi | WCP tl=50 | gap | WCP tl=100 | gap | WCP tl=200 | gap |
|------|---------|-----------|-----|------------|-----|------------|-----|
| 12 | 2.711s | 0.996s | **-63%** | 1.029s | **-62%** | 1.029s | **-62%** |
| 13 | 9.178s | 1.311s | **-86%** | 1.428s | **-85%** | 1.428s | **-85%** |
| 14 | 15.867s | 1.752s | **-89%** | 2.048s | **-87%** | 2.069s | **-87%** |
| 15 | 21.664s | 2.723s | **-87%** | 3.369s | **-85%** | 3.590s | **-83%** |
| 16 | 26.737s | 4.009s | **-85%** | 5.327s | **-80%** | 6.384s | **-76%** |
| 17 | 31.213s | 6.537s | **-79%** | 7.633s | **-76%** | 11.874s | **-62%** |
| 18 | 35.191s | 10.244s | **-71%** | 11.694s | **-67%** | 16.072s | **-54%** |
| 19 | 38.751s | 14.643s | **-62%** | 14.761s | **-62%** | 20.179s | **-48%** |
| 20 | 41.954s | 17.273s | **-59%** | 17.897s | **-57%** | 23.080s | **-45%** |

**tl=50 全 rate 最优 (-59% ~ -89%)**

## 下一步

- [x] 重写 `_get_next_batch()`：chunk_size 改为 per-request 含义
- [x] 每 batch 允许 P = remain 个 prefill 请求各做一个 chunk
- [x] 测试 rate={12..20} × tl={50,100,200} × chunk=128
- [ ] 添加 early termination（最后 100 个 req 时截断）
- [ ] 多 chunk_size 验证（64, 256）
- [ ] 自适应 tl

---
**作者**: Claude Code + 用户协作
**日期**: 2026-03-21
