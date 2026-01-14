# PD 分离请求生成器 (PD Separated Request Generator)

## 功能概述

PD 分离请求生成器用于模拟 **Prefill-Decode 分离架构**场景。生成的请求在到达时已经"完成了 Prefill 阶段"，直接进入 Decode 阶段。

这适用于测试：
- Decode GPU 在 PD 分离架构下的调度行为
- 只关注 Decode 阶段的性能分析
- 对比不同调度器在 Decode-only 场景下的表现

## 支持的调度器

| 调度器 | 兼容性 | 说明 |
|--------|--------|------|
| vLLM | ✅ 完全兼容 | 自动识别 `is_prefill_complete` |
| Sarathi | ✅ 完全兼容 | 自动识别 `is_prefill_complete` |
| WAIT (GeneralizedNestedBookingLimit) | ✅ 兼容 | 自动跳过 stage 0 等待 |

---

## 使用方法

### CLI 参数

```bash
python -m vidur.main \
  --request_generator_config_type pd_separated \
  --p_d_separated_request_generator_config_num_requests <请求数量> \
  --p_d_separated_request_generator_config_prefill_tokens <prefill token数> \
  --p_d_separated_request_generator_config_decode_tokens <decode token数> \
  --p_d_separated_request_generator_config_arrival_rate <到达率> \
  --p_d_separated_request_generator_config_seed <随机种子> \
  --replica_scheduler_config_type <调度器类型> \
  ...
```

### 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `num_requests` | 1000 | 生成的请求总数 |
| `prefill_tokens` | 512 | 每个请求的 prefill token 数（决定 KV 缓存大小） |
| `decode_tokens` | 128 | 每个请求的 decode token 数 |
| `arrival_rate` | 10.0 | 请求到达率（Poisson 过程，单位：requests/sec） |
| `seed` | 42 | 随机种子，用于复现实验 |

### 完整示例

```bash
# 使用 vLLM 调度器
python -m vidur.main \
  --request_generator_config_type pd_separated \
  --p_d_separated_request_generator_config_num_requests 100 \
  --p_d_separated_request_generator_config_prefill_tokens 512 \
  --p_d_separated_request_generator_config_decode_tokens 64 \
  --p_d_separated_request_generator_config_arrival_rate 5 \
  --replica_scheduler_config_type vllm \
  --time_limit 200

# 使用 Sarathi 调度器
python -m vidur.main \
  --request_generator_config_type pd_separated \
  --p_d_separated_request_generator_config_num_requests 100 \
  --p_d_separated_request_generator_config_prefill_tokens 512 \
  --p_d_separated_request_generator_config_decode_tokens 64 \
  --p_d_separated_request_generator_config_arrival_rate 5 \
  --replica_scheduler_config_type sarathi \
  --time_limit 200

# 使用 WAIT 调度器
python -m vidur.main \
  --request_generator_config_type pd_separated \
  --p_d_separated_request_generator_config_num_requests 100 \
  --p_d_separated_request_generator_config_prefill_tokens 512 \
  --p_d_separated_request_generator_config_decode_tokens 64 \
  --p_d_separated_request_generator_config_arrival_rate 5 \
  --replica_scheduler_config_type general_nested_booking_limit \
  --general_nested_booking_limit_scheduler_config_total_num_requests 100 \
  --time_limit 200
```

### Python API 使用

```python
from vidur.request_generator import RequestGeneratorRegistry
from vidur.types import RequestGeneratorType
from vidur.config import PDSeparatedRequestGeneratorConfig

# 创建配置
config = PDSeparatedRequestGeneratorConfig(
    num_requests=1000,
    prefill_tokens=630,
    decode_tokens=20,
    arrival_rate=14.0,
    seed=42,
)

# 获取生成器实例
generator = RequestGeneratorRegistry.get(RequestGeneratorType.PD_SEPARATED, config)

# 生成请求
requests = generator.generate_requests()

# 验证请求属性
for r in requests[:3]:
    print(f"id={r.id}, prefill_complete={r.is_prefill_complete}, "
          f"stage={r.current_stage}, processed={r.num_processed_tokens}")
```

---

## 实现原理

### 核心思想

生成的每个请求设置以下属性，模拟"已完成 Prefill"的状态：

```python
request._is_prefill_complete = True           # 标记 prefill 已完成
request._num_processed_tokens = prefill_tokens  # 等于 prefill_tokens（不能 +1，否则会超出 vLLM 内存分配）
request.current_stage = 1                     # 跳过 stage 0（WAIT 调度器用）
```

**注意**：`num_processed_tokens` 必须等于 `prefill_tokens`，不能是 `prefill_tokens + 1`，否则会超出 vLLM 为新请求分配的 KV 缓存块空间（`ceil(prefill_tokens / block_size) * block_size`），导致断言失败。第一个 decode token 的 +1 会由 `on_batch_end` 自动处理。

### 模拟效果

| 行为 | 说明 |
|------|------|
| 内存分配 | 按 `prefill_tokens` 分配 KV 缓存块（模拟 KV 缓存已传输到 Decode GPU） |
| 执行时间 | 只计算 Decode 部分，跳过 Prefill 执行时间 |
| 调度行为 | 请求直接进入 Decode 调度流程 |

---

## 代码修改位置

### 新建文件

| 文件 | 说明 |
|------|------|
| `vidur/request_generator/pd_separated_request_generator.py` | Generator 实现（~70 行） |

### 修改文件

| 文件 | 行号 | 修改内容 |
|------|------|---------|
| `vidur/types/request_generator_type.py` | 第 8 行 | 添加枚举值 `PD_SEPARATED = 4` |
| `vidur/config/config.py` | 第 281-311 行 | 添加 `PDSeparatedRequestGeneratorConfig` 配置类 |
| `vidur/request_generator/request_generator_registry.py` | 第 8-10, 31-34 行 | 导入并注册新 Generator |
| `vidur/scheduler/replica_scheduler/general_nested_booking_limit_replica_scheduler.py` | 第 41-43 行 | WAIT 调度器补丁（自动跳过 stage 0） |

### 修改详情

#### 1. 枚举类型 (`vidur/types/request_generator_type.py`)

```python
class RequestGeneratorType(BaseIntEnum):
    SYNTHETIC = 1
    TRACE_REPLAY = 2
    CUSTOM = 3
    PD_SEPARATED = 4  # 新增
```

#### 2. 配置类 (`vidur/config/config.py`)

```python
@dataclass
class PDSeparatedRequestGeneratorConfig(BaseRequestGeneratorConfig):
    num_requests: int = 1000
    prefill_tokens: int = 512
    decode_tokens: int = 128
    arrival_rate: float = 10.0
    seed: int = 42

    @staticmethod
    def get_type():
        return RequestGeneratorType.PD_SEPARATED
```

#### 3. WAIT 调度器补丁 (`general_nested_booking_limit_replica_scheduler.py`)

```python
def add_request(self, request: Request) -> None:
    # PD分离补丁：已完成prefill的请求直接从stage 1开始
    if request._is_prefill_complete and request.current_stage == 0:
        request.current_stage = 1

    self._request_queue.append(request)
    ...
```

---

## 注意事项

1. **Request.restart() 会重置状态**：如果触发抢占重启，`is_prefill_complete` 会被重置为 False。这在 PD 分离场景下可能导致请求被重新 Prefill。

2. **prefill_completed_at 时间戳**：不会被设置，因为跳过了 `on_batch_end` 中的检测逻辑。Prefill 相关指标可能为 0 或异常。

3. **WAIT 的 segment 配置**：确保第一个 segment 的 start 是 0，这样 `current_stage=1` 的请求能正确被归类到第一个 segment 内部。

---

## 验证方法

运行后检查输出的 metrics：

```bash
# 查看请求 metrics
cat simulator_output/*/request_metrics_*.csv | head -20
```

### 预期结果

| 指标 | 预期值 | 说明 |
|------|--------|------|
| `request_num_prefill_tokens` | 等于配置值 | 正确 |
| `request_num_decode_tokens` | 等于配置值 | 正确 |
| `request_execution_time` | 正常值（~0.5-1s） | 只包含 decode 执行时间 |
| `request_num_restarts` | 0 | 无重启 |
| `prefill_e2e_time` | **负数** | 预期行为，见下文说明 |

### 关于 prefill_e2e_time 为负数

这是 **预期行为**，原因如下：

1. PD 分离场景下，prefill 在其他 GPU 完成，不在当前模拟的 Decode GPU 上执行
2. `prefill_completed_at` 时间戳未被设置（默认值为 0）
3. 导致 `prefill_e2e_time = prefill_completed_at - arrived_at = 0 - arrived_at = 负数`

### 应该关注的 Metrics

在 PD 分离场景下，分析结果时应该：

**关注这些指标**：
- `request_e2e_time` - 端到端延迟
- `request_execution_time` - 执行时间（仅 decode）
- `request_scheduling_delay` - 调度延迟
- `request_preemption_time` - 抢占时间
- `decode_time_execution_plus_preemption_normalized` - decode 阶段归一化时间
- `throughput` - 吞吐量

**忽略这些指标**（在 PD 分离场景下无意义）：
- `prefill_e2e_time` - 会是负数
- `prefill_time_execution_plus_preemption` - 会是负数
- `prefill_time_execution_plus_preemption_normalized` - 会是负数
