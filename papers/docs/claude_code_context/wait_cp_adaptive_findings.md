# WAIT CP 自适应实验发现 - 2026-03-18

## 关键发现

### 1. Decode-First WAIT CP 在低 rate 下完美退化为 Sarathi

rate=14~21 所有 rate 下，WAIT CP (total_limit=725, decode-first) 与 Sarathi-512 的 e2e latency **完全一致**（差 0.0%，精确到小数点后 6 位）。

原因：total_limit=725 远大于自然在飞数 → remain 永远不 binding → 调度决策完全等价。

### 2. 自适应 n*(λ) 也没有 binding

理论公式 n* = (K+l₁)×d₀×λ / (1 - (K+l₁)×d₁×λ) 给出的 n*：
- rate=14: n*=15, 自然 L=10 → 不 binding
- rate=18: n*=20, 自然 L=10 → 不 binding（实测 in_sys=3-11）
- rate=20: n*=22, 自然 L≈10-15 → 不 binding

### 3. 根因：当前 workload 是 throughput-limited，不是 memory-limited

配置：l₀=630, l₁=20, A100 → GPU 内存容量 725 slots
自然在飞数：最高 ~15（即使 rate=21）
系统在 throughput 达到上限时，内存只用了 2% (15/725)

Sarathi 在高 rate 下的高 latency（如 rate=20 的 24s）不是因为内存过载，
而是因为**请求持续到达但处理速度跟不上** → 队列无限增长 → latency 线性增加。
这种过载不是 admission control 能解决的——限制入系统只会让队列在外面等，
总 e2e 不变。

### 4. Admission control 有价值的前提

WAIT CP 的 admission control 能赢 Sarathi 的条件：
- 系统是 **memory-limited**（内存先于 throughput 成为瓶颈）
- 具体：自然在飞数接近 GPU 内存容量
- 这时 Sarathi 会因为内存不足频繁 preempt/restart → 性能崩溃
- WAIT CP 通过 admission control 限制并发 → 避免 preempt → 稳定性优势

需要的实验参数：更大的 l₀（如 2048+）和/或更大的 l₁（如 128+），
使得 GPU 内存成为真正的瓶颈。

## 代码状态

当前代码已实现：
1. Decode-First 调度（三步：decode → running prefill → new request）
2. Decode tokens 计入 chunk 预算（与 Sarathi 一致）
3. 自适应 n* 基于 d₀/d₁ 公式（在 add_request 中更新 λ̂）
4. Step 3 的 remain = total_limit - in_system 准入控制

问题：准入控制在当前 workload 下永远不触发（in_system << total_limit）。

## 下一步

- [ ] 用 memory-limited workload 重新测试（l₀=2048, l₁=128）
- [ ] 或：缩小 GPU 内存（减小 memory_margin 或用更小的 GPU 如 a40）
- [ ] 验证在 memory-limited 场景下 WAIT CP 是否真正赢 Sarathi
