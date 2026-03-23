# 深度研究报告：WAIT-CP 如何在 Stable Region 超过 Sarathi

**日期**: 2026-03-19
**研究面向**: 5 个并行代理

---

## 执行摘要

5 个研究代理发现了 3 个可行的突破方向。最有前景的是 **Prefill 频率控制**——不是每个 batch 都做 prefill（Sarathi 的 f=1），而是自适应跳过部分 prefill（f*≈0.36 at rate=14），使 decode-only batch 仅需 ~12ms（vs 混合 batch ~44ms），理论上可将 TPOT 改善 1.9x。

---

## 核心发现

### 发现 1: Vidur 的 batch_time 模型是亚线性的（可利用！）

Vidur 的执行时间 = **固定开销（~8ms/step for MLP/norm）+ 边际成本（~0.055ms/token）**。

| Batch Size | Step Time | Per-Request | Speedup vs bs=1 |
|------------|-----------|-------------|------------------|
| 1 | 10.24ms | 10.24ms | 1.0x |
| 8 | 10.88ms | 1.36ms | 7.5x |
| 32 | 12.99ms | 0.41ms | 25.2x |

**在 bs=1~32 范围内亚线性效应最强**。这意味着 WAIT 的"凑大 batch"在小 batch 范围确实有规模收益。但当前 workload 的自然 batch ≈ 10，已经在效率区间，再凑大收益有限。

### 发现 2: Prefill 频率控制（最有前景的突破口）

**核心公式**：
```
Decode-only batch: ~12ms
Mixed batch (chunk=512): ~44ms
最优 prefill 频率: f* = K×λ×(d₀'+d₁×n) / (1 - K×λ×(d₀-d₀'))
```

rate=14 时 f*=0.36（只有 36% 的 batch 需要 prefill）→ TPOT 从 43.5ms 降到 22.5ms (1.9x)。

**为什么 Sarathi 不做这个**：Sarathi 的 stall-free 算法贪心地在每个 batch 塞 prefill（f=1），这优化了 TTFT 但牺牲了 TPOT。

**WAIT-CP 的优势**：booking limit 结构提供了"系统繁忙度"信息（decode_count），可以自适应决定是否跳过本次 prefill。

### 发现 3: 严格 Work-Conserving + 外部准入控制

论文 "Throughput-Optimal Scheduling"（arXiv:2504.07347）证明：**Sarathi 是 throughput-optimal 的**。任何"等凑批"机制违反 work-conservation → 牺牲 throughput → 在 stable region 不可能赢。

但 **admission control（控制谁能进系统）不违反 work-conservation**——GPU 始终在工作，只是限制了排队池的大小。这是 WAIT 的正确用法：
- ❌ "等凑够 n 个再发车"（违反 work-conservation，idle GPU）
- ✅ "GPU 始终工作，但限制同时进入系统的请求数"（admission control）

### 发现 4: Sarathi 的具体弱点

| 弱点 | 来源 | WAIT-CP 利用方式 |
|------|------|-----------------|
| 每个 batch 强制 prefill | FairBatching, Niyama | 跳过 prefill 做 decode-only batch |
| 不感知请求完成度 | ELIS, SOLA | 优先处理接近完成的请求（SRPT） |
| Batch size 不可控 | Throughput-Optimal论文 | Admission control 稳定 batch 组成 |
| FCFS 队列排序 | Learning-to-Rank (NeurIPS 2024) | SJF 队列重排序 |
| 贪心内存使用 | Past-Future, Jaillet 2025 | 前瞻性内存检查 |

---

## 推荐实施方案（按优先级）

### 方案 1: Prefill Skip（最高优先级）🔥

在 WAIT-CP 的 `_get_next_batch` 中：当 decode 数 > 阈值时，**跳过本次 prefill**，只做 decode-only batch。

```python
def _should_include_prefill(self, decode_count):
    # f* = 最优 prefill 频率
    # 当 decode 少时总是做 prefill（系统闲）
    # 当 decode 多时跳过 prefill（加速 decode 推进）
    if decode_count <= 2:
        return True  # 系统闲，不跳
    # 用计数器控制频率
    self._iter_count += 1
    return self._iter_count % self._prefill_period == 0
```

**预期改善**：TPOT 降低 ~40%（22.5ms vs 43.5ms），E2E 降低 ~20-30%。

### 方案 2: SJF 队列重排序

```python
# Step 3 中，不用 FCFS，按剩余 decode 数排序
self._request_queue.sort(key=lambda r: r.num_decode_tokens - (r.num_processed_tokens - r.num_prefill_tokens))
```

**预期改善**：减少 head-of-line blocking，E2E 降低 5-15%。

### 方案 3: 前瞻性内存检查

```python
def _can_allocate_request(self, request):
    peak_memory = self._num_allocated_blocks + sum(
        ceil(req.remaining_decode / block_size) for req in running_decodes
    ) + ceil(request.num_prefill_tokens / block_size)
    return peak_memory + watermark <= num_blocks
```

**预期改善**：在 memory-limited workload 下显著，原 workload 中等。

---

## 关键参考文献

| 论文 | 会议 | 核心机制 |
|------|------|---------|
| Fluid-Guided WAIT | NeurIPS 2025 | Fluid equilibrium threshold |
| SOLA | MLSys 2025 | State-aware per-iteration scheduling |
| Niyama | Microsoft 2025 | Dynamic chunking + eager relegation |
| Learning to Rank | NeurIPS 2024 | SJF via output length ranking |
| Past-Future Scheduler | ASPLOS 2025 | Forward-looking memory prediction |
| Throughput-Optimal | arXiv 2504.07347 | Work-conservation proof for Sarathi |
| DistServe | OSDI 2024 | Pull-based prefill-decode separation |
| FairBatching | arXiv 2510.14392 | Time-budget replacing token-budget |

---

**研究执行者**: 5 个并行代理
**咨询论文数**: ~40+
