# WCP (WAIT-CP) SGLang GPU 实现指南

## 概述

本文档描述如何在 SGLang 上实现 WCP (WAIT-CP) 算法，并与默认 vLLM 调度器进行 GPU 性能对比。

## WCP 算法核心特性

### 1. Nested Booking Limit
- 将请求按 decode 长度分段
- 每段有独立的 booking limit 控制
- 实现细粒度的容量管理

### 2. Per-Request Chunked Prefill
- 每个请求一次只处理 `chunk_size` 个 prefill tokens
- 避免单个请求垄断 batch
- 提高公平性和吞吐量

### 3. Per-Segment Gate
- 每个 segment 控制自己的 token budget
- 防止 batch 过大导致的内存问题
- 精确控制 decode/prefill 比例

## 文件结构

```
scripts/
├── wcp_sglang_integration.py      # WCP 调度器核心实现
├── wcp_vs_vllm_gpu_benchmark.py   # GPU 对比实验脚本
└── wcp_sglang_implementation.py   # 实现框架

outputs/wcp_benchmark/
├── results.json                    # 实验结果
└── benchmark_report.md             # 对比报告
```

## 使用方法

### 1. 直接运行模拟对比

```bash
python scripts/wcp_vs_vllm_gpu_benchmark.py \
    --model models/modelscope/Llama-2-7b-ms \
    --batch-sizes 1 4 8 16 32 \
    --prefill-lens 256 512 \
    --wcp-tl 21 \
    --wcp-cs 256
```

### 2. 在 SGLang 中集成 WCP

要在真正的 SGLang 中运行 WCP，需要修改 SGLang 源码：

#### 步骤 1: 复制 WCP 集成模块

```bash
# 将 WCP 模块复制到 SGLang 目录
cp scripts/wcp_sglang_integration.py \
   /persistent/miniforge3/lib/python3.11/site-packages/sglang/srt/managers/
```

#### 步骤 2: 修改 SGLang Scheduler

编辑 `/persistent/miniforge3/lib/python3.11/site-packages/sglang/srt/managers/scheduler.py`:

```python
# 在 scheduler.py 顶部添加
from sglang.srt.managers.wcp_sglang_integration import (
    WCPScheduler, WCPSchedulerConfig, SGLangWCPAdapter
)

# 在 Scheduler.__init__ 中添加 WCP 支持
class Scheduler:
    def __init__(self, ...):
        # ... existing code ...

        # Check for WCP mode
        if os.environ.get("SGLANG_SCHEDULER_POLICY") == "wcp":
            wcp_config = WCPSchedulerConfig(
                total_limit=int(os.environ.get("WCP_TOTAL_LIMIT", "21")),
                chunk_size=int(os.environ.get("WCP_CHUNK_SIZE", "256")),
                enable_gate=os.environ.get("WCP_GATE", "1") == "1",
            )
            self.wcp_scheduler = WCPScheduler(wcp_config)
            self.wcp_adapter = SGLangWCPAdapter(self.wcp_scheduler)
            self.use_wcp = True
        else:
            self.use_wcp = False
```

#### 步骤 3: 修改调度逻辑

在 `scheduler.py` 的 `get_next_batch` 方法中：

```python
def get_next_batch(self):
    if self.use_wcp:
        # Use WCP scheduling
        selected_requests, metadata = self.wcp_adapter.schedule(
            self, self.waiting_queue, self.running_queue
        )
        return self.build_batch(selected_requests, metadata)
    else:
        # Use default vLLM scheduling
        return self.default_schedule()
```

## WCP 配置参数

| 参数 | 含义 | 推荐值 |
|------|------|--------|
| `tl` (total_limit) | 全局 booking limit | 21 (single-type) |
| `cs` (chunk_size) | Per-request prefill chunk | 256 |
| `gate` | Per-segment gate 开关 | True |
| `wait_gate` | WAIT fill threshold | False |

## 预期结果

基于 Vidur 仿真数据，WCP 相对于 vLLM 的改进：

| Workload | 改进幅度 |
|----------|---------|
| Single-type p512d20 | -2% to -75% |
| Multi-type W1 | -4% to -13% |
| Multi-type W3 | -3% to -42% |

**关键优势**：
- 高负载时稳定性更好（不会爆 latency）
- 内存使用更可预测
- 公平性更好（无请求饿死）

## 实现注意事项

### 1. 与 SGLang 的兼容性

SGLang 的调度器架构与 Vidur 不同：
- SGLang 使用连续的调度循环
- Vidur 使用离散事件模拟
- 需要将 WCP 的逻辑适配到连续调度

### 2. 内存管理

WCP 的 booking limit 需要与 SGLang 的 KV cache 管理集成：
```python
# 在 WCP 中检查内存
if in_system >= self.config.total_limit:
    break  # 达到 booking limit

# 同时检查 SGLang 的内存
if not self._can_allocate_request(req):
    break  # 内存不足
```

### 3. Chunked Prefill 实现

在 SGLang 中实现 chunked prefill：
```python
# 每个请求只处理 chunk_size tokens
remaining = req.prefill_len - req.processed_tokens
chunk = min(remaining, self.config.chunk_size)

# 更新进度
req.processed_tokens += chunk

# 如果完成，进入 decode stage
if req.processed_tokens >= req.prefill_len:
    req.stage = 1
```

## 调试与验证

### 1. 日志输出

启用 WCP 详细日志：
```bash
export WCP_DEBUG=1
python -m sglang.launch_server --model ...
```

### 2. 指标监控

监控关键指标：
- Batch size distribution
- Prefill/decode ratio
- Booking limit utilization
- Memory usage

### 3. 正确性验证

验证 WCP 正确性：
- 所有请求最终完成
- 无内存泄漏
- Booking limit 不被突破
- Chunked prefill 进度正确

## 性能优化

### 1. GPU Kernel 优化

确保 chunked prefill 不会降低 GPU 利用率：
- 保持足够的 batch size
- 使用 CUDA graph
- 优化 attention kernel

### 2. 自适应参数

根据负载动态调整参数：
```python
if high_load:
    self.config.total_limit = 30  # 提高 limit
else:
    self.config.total_limit = 21  # 降低 limit
```

## 未来工作

1. **Multi-type Workload**: 完整实现多类型请求的 segment 划分
2. **Adaptive WCP**: 根据实时负载调整参数
3. **Hybrid Scheduling**: 结合 vLLM 和 WCP 的优点
4. **PD Separation**: 支持 prefill-decode 分离部署

## 参考

- Paper: "Optimizing LLM Inference: Fluid-Based Online Scheduling with Memory Constraints"
- Vidur: https://github.com/microsoft/vidur
- SGLang: https://github.com/sgl-project/sglang
