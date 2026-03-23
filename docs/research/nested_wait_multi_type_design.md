# Nested WAIT Multi-Type Scheduler 设计

## 算法概述

多类型 workload 下，不同请求类型有不同的 prefill/decode 长度。Nested booking limit 按 decode 长度边界划分 segment，每段有独立的 per-stage limit，实现 flow balance。

## Segment 划分

**输入**: prompt_types 列表，每个有 (prefill, decode, arrival_rate)

**步骤**:
1. 收集唯一 decode 值，排序: d₁ < d₂ < ... < dₘ
2. 按 decode 边界划分 segment:
   - Segment 0: stages 0 ~ d₁-1 (所有 type 都在)
   - Segment 1: stages d₁ ~ d₂-1 (只有 decode > d₁ 的 type)
   - Segment k: stages d_k ~ d_{k+1}-1

**示例 (2-type)**:
```
Type A: prefill=256, decode=10, rate=9.8
Type B: prefill=512, decode=50, rate=4.2

unique_decodes = [10, 50]

Segment 0: stages 0-9   (count=10, both A+B, arrival_sum=14.0)
Segment 1: stages 10-49 (count=40, only B,   arrival_sum=4.2)
```

## Per-Stage Limit 计算

**公式**:
```
weight_k = count_k × arrival_sum_k
total_weight = Σ weight_k

seg_total_limit_k = tl × (weight_k / total_weight)
per_stage_limit_k = ceil(seg_total_limit_k / count_k)
```

**示例 (2-type, tl=100)**:
```
weight_0 = 10 × 14.0 = 140
weight_1 = 40 × 4.2  = 168
total_weight = 308

seg0_total = 100 × 140/308 = 45.5 → per_stage_0 = ceil(45.5/10) = 5
seg1_total = 100 × 168/308 = 54.5 → per_stage_1 = ceil(54.5/40) = 2

结果:
  Stages 0-9:  每 stage 最多 5 个请求 (高流量段, A+B 都在)
  Stages 10-49: 每 stage 最多 2 个请求 (低流量段, 只有 B)
```

**示例 (不同 tl)**:
```
tl=21:  seg0: per_stage=ceil(9.5/10)=1,  seg1: per_stage=ceil(11.5/40)=1  ← 无区别!
tl=50:  seg0: per_stage=ceil(22.7/10)=3, seg1: per_stage=ceil(27.3/40)=1
tl=100: seg0: per_stage=5,               seg1: per_stage=2
tl=200: seg0: per_stage=10,              seg1: per_stage=3
```

**关键**: tl 太小时 per_stage 全为 1，nested 结构退化。tl ≥ 50 才开始有区别。

## Batch 构建

### Decode (Stage 1+): 按 segment per_stage_limit
```
for each segment:
    for each stage in segment:
        取 min(per_stage_limit, 可用请求数) 个请求
        每个请求处理 1 token
        advance_stage()
```

### Prefill (Stage 0): per-request chunk
```
每个 running prefill: min(remaining, per_req_budget) tokens
新 admit: 受 segment 0 的 remain + gate (total_budget) 限制
```

### Gate (total_budget)
```
total_budget = P × weighted_avg(l₀+l₁)
P = tl / weighted_avg_pipeline_depth

控制 batch 总 tokens 不超过 total_budget
→ 防止 batch 膨胀 (tl 大时 decode 多 → batch 大)
→ 让 tl 可以大 (nested 生效) 而 batch 不爆
```

## 参数设计

### 三参数
| 参数 | 控制 | 取值指导 |
|------|------|---------|
| tl | 总 in-system + nested 结构 | ≥ 50 (让 nested 生效) |
| cs | per-request prefill chunk | 128~256 (attention 节省 vs overhead) |
| gate | batch tokens 上限 | ON (必须, 防膨胀) |

### 派生量
```
对每个 type i:
  K_i = ceil(l₀_i / cs)
  pipeline_i = K_i + l₁_i

加权平均:
  pipeline_w = Σ(rate_i/total_rate × pipeline_i)
  avg_tokens = Σ(rate_i/total_rate × (l₀_i + l₁_i))

P = tl / pipeline_w
total_budget = P × avg_tokens
```

### 示例配置 (2-type)
```
Type A: prefill=256, decode=10, rate=70%
Type B: prefill=512, decode=50, rate=30%

pipeline_w = 0.7×(1+10) + 0.3×(2+50) = 7.7+15.6 = 23.3
avg_tokens = 0.7×266 + 0.3×562 = 186+169 = 355

tl=50, cs=256:
  P = 50/23.3 = 2.15
  total_budget = 2.15 × 355 = 763
  seg0 per_stage = 3 (stages 0-9)
  seg1 per_stage = 1 (stages 10-49)

tl=100, cs=256:
  P = 100/23.3 = 4.29
  total_budget = 4.29 × 355 = 1523
  seg0 per_stage = 5
  seg1 per_stage = 2
```

## 与 Single-Type 的关系

Single-type 是 multi-type 的特例:
- 1 个 segment, 覆盖所有 stages
- per_stage = ceil(tl / (K+l₁)) = ceil(P)
- 退化为全局 tl 控制

---
**日期**: 2026-03-23
