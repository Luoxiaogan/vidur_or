# Vidur LLM 调度模拟器 - Claude Code 项目规范

## 项目概述

Vidur 是一个用于 LLM 推理服务调度研究的**事件驱动离散事件模拟器**。它模拟多副本集群环境下的请求调度、KV缓存管理和执行时间预测。

### 代码版本说明
- **原始版本**: `VIDUR_ORIGINAL/vidur/` (用于对比参考)
- **当前版本**: `vidur/` (包含 Booking Limit 调度器等扩展)
- **修改详情**: 参见 [docs_for_claude_code/代码修改差异说明.md](docs_for_claude_code/代码修改差异说明.md)

### 核心特性
- **两级调度架构**: GlobalScheduler(全局) + ReplicaScheduler(副本)
- **事件驱动仿真**: 基于优先级队列的离散事件模拟
- **多调度器支持**: 9种副本调度器(vLLM、Sarathi、ORCA等)
- **细粒度执行时间预测**: 24维度拆分(注意力、MLP、通信、CPU开销)
- **KV缓存显式管理**: 块级别内存分配/释放
- **请求抢占与恢复**: 支持请求重启和并行化处理

### 技术栈
- Python 3.8+
- 事件驱动模拟 (heapq)
- Dataclass 配置系统
- 注册表模式 (工厂模式)

---

## 项目架构

### 目录结构
```
vidur/
├── main.py                    # 入口: 解析配置, 运行模拟
├── simulator.py               # 事件循环核心
├── config/                    # 层次化配置系统
│   ├── config.py             # 主配置定义 (SimulationConfig)
│   ├── flat_dataclass.py     # CLI参数解析与重构
│   ├── model_config.py       # 模型配置
│   └── base_poly_config.py   # 多态配置基类
├── entities/                  # 核心数据实体
│   ├── request.py            # Request (请求生命周期)
│   ├── batch.py              # Batch (批处理)
│   ├── batch_stage.py        # BatchStage (Pipeline阶段)
│   ├── replica.py            # Replica (GPU副本)
│   └── cluster.py            # Cluster (集群)
├── scheduler/                 # 调度系统 (核心)
│   ├── global_scheduler/     # 全局调度: Random, RoundRobin, LOR
│   ├── replica_scheduler/    # 副本调度: vLLM, Sarathi, BookingLimit等
│   └── replica_stage_scheduler/  # Pipeline阶段调度
├── events/                    # 事件系统
│   ├── base_event.py         # 事件基类
│   ├── request_arrival_event.py
│   ├── global_schedule_event.py
│   ├── replica_schedule_event.py
│   └── batch_end_event.py
├── request_generator/         # 请求生成
│   ├── synthetic_request_generator.py
│   ├── trace_replay_request_generator.py
│   └── request_interval_generator/  # 到达分布: Poisson, Gamma
├── execution_time_predictor/  # 执行时间预测
│   ├── base_execution_time_predictor.py
│   ├── sklearn_execution_time_predictor.py
│   └── linear_regression_execution_time_predictor.py
├── metrics/                   # 指标收集
│   └── metrics_store.py      # E2E延迟, 吞吐量等
├── types/                     # 类型枚举
│   ├── global_scheduler_type.py
│   ├── replica_scheduler_type.py
│   └── event_type.py
└── utils/                     # 工具类
    ├── base_registry.py      # 注册表基类
    └── event_queue.py        # 事件队列

data/
├── profiling/
│   ├── compute/              # GPU计算性能数据
│   │   ├── a100/            # attention.csv, mlp.csv
│   │   ├── a40/
│   │   └── h100/
│   └── network/              # 网络通信数据
│       ├── a100_dgx/        # all_reduce.csv, send_recv.csv
│       └── h100_pairwise_nvlink/
└── processed_traces/          # 请求trace数据
    ├── splitwise_code.csv
    └── arxiv_summarization_stats_*.csv
```

### 核心类继承体系

```
调度器:
BaseGlobalScheduler (ABC)
├── RandomGlobalScheduler
├── RoundRobinGlobalScheduler
└── LORGlobalScheduler

BaseReplicaScheduler (ABC)
├── VLLMReplicaScheduler
├── SarathiReplicaScheduler
├── OrcaReplicaScheduler
├── LightLLMReplicaScheduler
├── FasterTransformerReplicaScheduler
├── BookingLimitReplicaScheduler
├── NestedBookingLimitReplicaScheduler
├── GeneralNestedBookingLimitReplicaScheduler
└── ModifiedBookingLimitReplicaScheduler

实体:
BaseEntity
├── Request
├── Batch
├── BatchStage
├── Replica
└── Cluster

事件:
BaseEvent (ABC)
├── RequestArrivalEvent
├── GlobalScheduleEvent
├── ReplicaScheduleEvent
├── ReplicaStageScheduleEvent
├── BatchEndEvent
├── BatchStageArrivalEvent
└── BatchStageEndEvent

配置:
BasePolyConfig (ABC)        # 多态配置 (通过get_type()识别)
├── BaseGlobalSchedulerConfig
├── BaseReplicaSchedulerConfig
├── BaseRequestGeneratorConfig
└── BaseExecutionTimePredictorConfig

BaseFixedConfig (ABC)       # 固定配置 (通过get_name()识别)
├── ModelConfig
├── DeviceConfig
└── NodeConfig
```

---

## 开发规范

### 代码组织原则

#### 1. 继承优于重写
- 新调度器必须继承 `BaseReplicaScheduler` 或 `BaseGlobalScheduler`
- 实现抽象方法，不修改基类逻辑
- 示例: 实现新调度器
```python
class MyScheduler(BaseReplicaScheduler):
    """
    自定义调度器 - 继承BaseReplicaScheduler

    继承关系: BaseReplicaScheduler -> MyScheduler
    兼容性: 完全兼容原有调度接口
    """

    def _get_next_batch(self) -> Batch:
        # 实现自定义批处理逻辑
        pass

    def on_batch_end(self, batch: Batch) -> None:
        # 实现批处理结束逻辑
        pass
```

#### 2. 接口兼容性设计
- **100%向后兼容**: 新组件必须可以直接替换原组件
- **配置驱动**: 通过配置控制功能启用，支持渐进式部署
- **非侵入扩展**: 通过组合模式添加功能，不修改原代码

#### 3. 注册表模式
所有可扩展组件必须注册到对应的Registry:
```python
# 在 replica_scheduler_registry.py 中注册
ReplicaSchedulerRegistry.register(
    ReplicaSchedulerType.MY_SCHEDULER,
    MyScheduler
)

# 使用时通过Registry获取
scheduler = ReplicaSchedulerRegistry.get(
    ReplicaSchedulerType.MY_SCHEDULER,
    replica_config=config,
    ...
)
```

---

### 文档和注释规范

#### 1. 模块级文档
```python
"""
模块名称 + 功能描述

详细功能说明，说明与原系统的关系

核心特性:
1. 特性描述
2. 兼容性说明

作者: Vidur Scheduling优化项目组
版本: 1.0.0
兼容: 原组件版本要求
"""
```

#### 2. 函数文档
```python
def schedule(self, requests: List[Request]) -> Dict[int, List[Request]]:
    """
    调度方法 - 与原接口完全兼容

    扩展原有调度逻辑，添加监控但不改变调度行为

    Args:
        requests: 请求列表 (与原版本相同)

    Returns:
        调度结果字典 (与原版本相同格式)
    """
```

---

### 配置系统规范

#### 1. 层次化配置
```python
# 基础配置 (兼容原系统)
BASE_CONFIG = {
    "hidden_size": 128,
    "layer_N": 2,
}

# 优化配置 (覆盖优化项)
CPU_OPTIMIZED_CONFIG = {
    **BASE_CONFIG,
    "hidden_size": 64,      # 性能优化
    "cpu_optimized": True,  # 功能标识
}
```

#### 2. 功能开关
```python
class FeatureFlags:
    ENABLE_TENSORBOARD = "enable_tensorboard"
    CPU_OPTIMIZATION = "cpu_optimization"

# 使用示例
if config.get(FeatureFlags.ENABLE_TENSORBOARD, False):
    self._setup_tensorboard()
```

#### 3. 多态配置定义
新增配置类时:
```python
@dataclass
class MySchedulerConfig(BaseReplicaSchedulerConfig):
    my_param: int = field(
        default=100,
        metadata={"help": "自定义参数说明"}
    )

    @staticmethod
    def get_type() -> ReplicaSchedulerType:
        return ReplicaSchedulerType.MY_SCHEDULER
```

#### 4. CLI参数使用
```bash
python -m vidur.main \
  --replica_scheduler_config_type vllm \
  --replica_scheduler_config_block_size 16 \
  --global_scheduler_config_type round_robin \
  --request_generator_config_type synthetic \
  --time_limit 100
```

---

### 核心编程规范 - 严格执行

#### 关键原则

1. **使用知识库中已有的接口和函数** - 优先调用现有API，避免重复实现
2. **遵循项目现有的设计模式** - 保持架构一致性和代码风格统一
3. **避免硬编码，使用配置或常量** - 提高代码可维护性和可扩展性
4. **保持代码的可扩展性** - 设计时考虑未来功能扩展需求
5. **禁止使用try except!** - 碰见错误直接显示traceback并退出终止运行程序，方便从本质上解决问题
6. **禁止采用备用fallback等方案** - 如缺少属性直接报错返回，不允许降级处理

#### 错误处理强制规范

```python
# 严格禁止的fallback模式
try:
    result = complex_operation()
except Exception:
    result = fallback_operation()  # 禁止!

# 严格禁止的属性检查fallback
if hasattr(obj, 'attribute'):
    return obj.attribute
else:
    return default_value  # 禁止!

# 正确的错误处理方式
result = complex_operation()  # 让错误自然抛出
required_attribute = obj.attribute  # 直接访问，缺失时报错
```

#### 实现规范示例

```python
# 正确的实现方式
def extract_metrics_from_simulation(self, scheduler_name: str, run_id: int) -> EvaluationMetrics:
    """从仿真中提取真实指标 - 禁止使用fallback"""

    # 直接获取配置，不存在则报错
    scheduler_config = self._get_scheduler_config(scheduler_name)
    if scheduler_config is None:
        raise ValueError(f"调度器配置不存在: {scheduler_name}")

    # 直接运行仿真，失败则报错
    simulator, metric_store = self.run_simulation_runtime(scheduler_name, scheduler_config, run_id)
    if simulator is None or metric_store is None:
        raise RuntimeError(f"仿真运行失败: {scheduler_name}")

    # 直接访问必要属性，缺失则报错
    latencies = metric_store.request_metrics.e2e_times  # 不检查存在性
    return self._calculate_metrics(latencies)

# 禁止的fallback实现
def extract_metrics_from_simulation_bad(self, scheduler_name: str, run_id: int) -> EvaluationMetrics:
    try:
        simulator, metric_store = self.run_simulation_runtime(scheduler_name, scheduler_config, run_id)
        return self._extract_real_metrics(metric_store)
    except Exception as e:
        logger.warning(f"仿真失败，使用fallback指标: {e}")
        return self._get_fallback_metrics()  # 严格禁止!
```

#### 代码审查清单

**提交前必须检查**：
- [ ] 没有任何 `try-except` 块用于错误隐藏
- [ ] 没有任何 fallback 或降级逻辑
- [ ] 所有必要属性直接访问，不做存在性检查
- [ ] 错误直接抛出，不做捕获处理
- [ ] 使用项目已有的接口和设计模式
- [ ] 避免硬编码值，使用配置文件
- [ ] 新组件已注册到对应的Registry

---

## 关键文件快速参考

### 入口和核心
| 文件 | 功能 | 行数 |
|------|------|------|
| `vidur/main.py` | 程序入口 | 17 |
| `vidur/simulator.py` | 事件循环核心 | 165 |
| `vidur/config/config.py` | 主配置定义 | 791 |

### 实体
| 文件 | 功能 |
|------|------|
| `vidur/entities/request.py` | Request生命周期管理 |
| `vidur/entities/batch.py` | 批处理管理 |
| `vidur/entities/replica.py` | GPU副本属性 |

### 调度器
| 文件 | 功能 |
|------|------|
| `vidur/scheduler/global_scheduler/base_global_scheduler.py` | 全局调度基类 |
| `vidur/scheduler/global_scheduler/lor_global_scheduler.py` | LOR调度算法 |
| `vidur/scheduler/replica_scheduler/base_replica_scheduler.py` | 副本调度基类 |
| `vidur/scheduler/replica_scheduler/vllm_replica_scheduler.py` | vLLM调度实现 |
| `vidur/scheduler/replica_scheduler/nested_booking_limit_replica_scheduler.py` | Nested Booking Limit策略 |

### 事件
| 文件 | 功能 |
|------|------|
| `vidur/events/base_event.py` | 事件基类 |
| `vidur/events/request_arrival_event.py` | 请求到达事件 |
| `vidur/events/batch_end_event.py` | 批处理结束事件 |

### 配置和类型
| 文件 | 功能 |
|------|------|
| `vidur/config/flat_dataclass.py` | CLI参数解析 |
| `vidur/types/replica_scheduler_type.py` | 调度器类型枚举 |
| `vidur/utils/base_registry.py` | 注册表基类 |

---

## 核心数据流

### 请求生命周期

```
1. RequestGenerator.generate()
   └─> 创建 Request 对象列表

2. Simulator._init_event_queue()
   └─> 为每个Request创建 RequestArrivalEvent

3. RequestArrivalEvent.handle_event()
   └─> GlobalScheduler.add_request(request)
   └─> 触发 GlobalScheduleEvent

4. GlobalScheduleEvent.handle_event()
   └─> GlobalScheduler.schedule()
   └─> 返回 [(replica_id, request), ...]
   └─> ReplicaScheduler.add_request(request)
   └─> 触发 ReplicaScheduleEvent

5. ReplicaScheduleEvent.handle_event()
   └─> ReplicaScheduler.on_schedule()
   └─> 返回 [Batch, ...]
   └─> 分配KV缓存块
   └─> 触发 ReplicaStageScheduleEvent

6. ReplicaStageScheduleEvent -> BatchStageArrivalEvent -> BatchStageEndEvent
   └─> 执行各Pipeline阶段

7. BatchEndEvent.handle_event()
   └─> ReplicaScheduler.on_batch_end(batch)
   └─> 更新Request状态 (completed/preempted)
   └─> 释放KV缓存块
   └─> 收集指标

8. MetricsStore.plot()
   └─> 输出最终指标和可视化
```

### KV缓存管理流程

```
Request到达
└─> ReplicaScheduler.add_request()
    └─> 加入_request_queue

调度时:
└─> _get_next_batch()
    └─> 计算所需blocks: max_tokens // block_size
    └─> can_allocate(num_blocks)?
        ├─> YES: allocate(request_id, num_blocks)
        │        更新 _allocation_map[request_id] += num_blocks
        │        更新 _num_allocated_blocks += num_blocks
        └─> NO (vLLM策略): 重启被抢占请求腾出空间

批处理结束:
└─> on_batch_end(batch)
    └─> 对completed_requests: free(request_id)
        释放 _allocation_map.pop(request_id)
        更新 _num_allocated_blocks -= num_blocks
```

---

## 常见开发任务

### 添加新调度器

1. **定义类型枚举** (`vidur/types/replica_scheduler_type.py`):
```python
class ReplicaSchedulerType(BaseIntEnum):
    # ... 现有类型
    MY_SCHEDULER = 10
```

2. **定义配置** (`vidur/config/config.py`):
```python
@dataclass
class MySchedulerConfig(BaseReplicaSchedulerConfig):
    my_param: int = field(default=100, metadata={"help": "参数说明"})

    @staticmethod
    def get_type() -> ReplicaSchedulerType:
        return ReplicaSchedulerType.MY_SCHEDULER
```

3. **实现调度器** (`vidur/scheduler/replica_scheduler/my_scheduler.py`):
```python
class MyScheduler(BaseReplicaScheduler):
    def __init__(self, ...):
        super().__init__(...)
        self._my_param = self._config.my_param

    def _get_next_batch(self) -> Batch:
        # 实现批处理选择逻辑
        pass

    def on_batch_end(self, batch: Batch) -> None:
        # 实现结束处理逻辑
        pass
```

4. **注册调度器** (`vidur/scheduler/replica_scheduler/replica_scheduler_registry.py`):
```python
ReplicaSchedulerRegistry.register(
    ReplicaSchedulerType.MY_SCHEDULER,
    MyScheduler
)
```

### 添加新事件类型

1. **定义事件类型** (`vidur/types/event_type.py`)
2. **创建事件类** (`vidur/events/my_event.py`):
```python
class MyEvent(BaseEvent):
    def __init__(self, time: float, ...):
        super().__init__(time, EventType.MY_EVENT)
        # 事件特定属性

    def handle_event(self, scheduler, metrics_store) -> List[BaseEvent]:
        # 处理逻辑，返回新事件列表
        return []

    def to_dict(self) -> dict:
        # 序列化
        pass
```

### 添加新指标

1. **在MetricsStore中添加** (`vidur/metrics/metrics_store.py`):
```python
class MetricsStore:
    def __init__(self, config):
        # ... 现有指标
        self.my_metric = DataSeries()

    def record_my_metric(self, value: float) -> None:
        self.my_metric.add(value)
```

2. **在事件处理中调用**:
```python
def handle_event(self, scheduler, metrics_store):
    # ... 处理逻辑
    metrics_store.record_my_metric(computed_value)
```

---

## Claude Code 使用规范

### 工具使用偏好
- 优先使用 `Read` 工具查看具体文件，而非 `Task` 工具搜索
- 使用 `Glob` 工具进行文件模式匹配
- 修改代码前必须先 `Read` 理解上下文
- **解释性文字直接写在回复里，禁止用 Bash 执行 python print 来输出文字说明**

### 本地修改 vs 网页端搜索判断规范

#### 直接本地修改的情况
**判断标准**: 已知解决方案或可从现有代码/文档推导出解决方案
- API调用方式错误（如参数名变化）
- 配置参数调整（如学习率、批次大小）
- 代码逻辑修复（如条件判断、循环结构）
- 文件路径或导入问题
- 已有成功案例可参考的问题
- 调度器实现细节（参考现有调度器）

#### 需要网页端搜索的情况
- 涉及算法原理或理论最佳实践
- 需要了解框架的最新变化
- 尝试了基本参数调整但仍未解决
- 需要替代方案或根本原因分析
- 外部库API变更

#### 决策流程
1. **问题出现** ->
2. **查看项目现有代码和文档** ->
3. **判断**:
   - 能从现有资源解决? -> **本地修改**
   - 需要外部专业知识? -> **网页端搜索** -> **更新问题库**
4. **执行解决方案** ->
5. **更新项目文档**

### 通用实现规范

- 始终先阅读现有代码理解其结构和约定
- 保持与现有代码风格一致
- 优先编辑现有文件而非创建新文件
- 重要修改前先备份或说明影响范围
- **遇到任何异常立即终止程序运行，便于定位根本问题**
- 新增功能必须遵循注册表模式

---

## 数据文件说明

### Profiling数据 (`data/profiling/`)

**计算性能数据** (`compute/{device}/{model}/`):
- `attention.csv`: 注意力层执行时间
- `mlp.csv`: MLP层执行时间

**网络通信数据** (`network/{topology}/`):
- `all_reduce.csv`: AllReduce集合通信时间
- `send_recv.csv`: 点对点通信时间

支持的设备: A40, A100, H100
支持的拓扑: pairwise_nvlink, dgx

### 请求Trace数据 (`data/processed_traces/`)

格式: CSV，包含字段:
- `num_prefill_tokens`: Prefill阶段token数
- `num_decode_tokens`: Decode阶段token数
- `num_total_tokens`: 总token数
- `pd_ratio`: Prefill/Decode比率

---

## 测试规范

### 兼容性测试
新调度器必须通过以下测试:
1. 能够替代现有调度器运行完整仿真
2. 输出格式与现有调度器一致
3. 不引入新的依赖或改变核心接口

### 运行示例
```bash
# 基本仿真
python -m vidur.main \
  --replica_scheduler_config_type vllm \
  --time_limit 100

# 使用trace数据
python -m vidur.main \
  --request_generator_config_type trace_replay \
  --trace_request_generator_config_trace_file data/processed_traces/splitwise_code.csv
```

---

## 调度器详解

### 全局调度器 (Global Schedulers)

全局调度器负责将请求分配到不同的副本(Replica)。

#### 1. RoundRobinGlobalScheduler
**文件**: `vidur/scheduler/global_scheduler/round_robin_global_scheduler.py`

**算法**: 轮询分配
```python
replica_id = request_counter % num_replicas
request_counter += 1
```

**特点**:
- 最简单的负载均衡策略
- 不考虑副本当前负载
- 适用于请求大小均匀的场景

#### 2. LORGlobalScheduler (Least Outstanding Requests)
**文件**: `vidur/scheduler/global_scheduler/lor_global_scheduler.py`

**算法**: 最少未决请求优先
```python
# 维护每个副本的pending请求数
pending_requests_map = {
    replica_id: replica_scheduler.num_pending_requests
}
# 分配给pending最少的副本
replica_id = min(pending_requests_map.items(), key=lambda x: x[1])[0]
```

**特点**:
- 动态负载感知
- 适用于请求大小差异较大的场景
- 能更好地平衡各副本负载

#### 3. RandomGlobalScheduler
**文件**: `vidur/scheduler/global_scheduler/random_global_scheduler.py`

**算法**: 随机分配
- 随机选择一个副本

---

### 副本调度器 (Replica Schedulers)

副本调度器负责在单个GPU副本内管理请求队列、KV缓存分配和批处理组装。

#### 1. VLLMReplicaScheduler
**文件**: `vidur/scheduler/replica_scheduler/vllm_replica_scheduler.py`

**核心机制**:
- **Watermark机制**: 保留一定比例的blocks作为安全缓冲
  ```python
  watermark_blocks = watermark_blocks_fraction * num_blocks
  ```
- **抢占与重启**: 当内存不足时，抢占被preempted的请求，调用`request.restart()`
- **批处理约束**: `max_tokens_in_batch`, `batch_size_cap`

**调度流程**:
```
1. 尝试从_request_queue取新请求
   └─> 检查 can_allocate (需预留watermark)
   └─> 分配blocks: allocate(request_id, num_blocks)
   └─> 加入batch

2. 若_request_queue无法满足，处理_preempted_requests
   └─> 按arrived_at排序 (FIFO)
   └─> 内存不足时: 从队尾抢占victim, 调用restart(), free()
   └─> 将victim放回_request_queue队首
```

**配置参数**:
- `block_size`: KV缓存块大小 (默认16)
- `watermark_blocks_fraction`: 水位线比例 (默认0.01)
- `max_tokens_in_batch`: 批处理最大token数
- `batch_size_cap`: 批处理最大请求数

#### 2. SarathiReplicaScheduler
**文件**: `vidur/scheduler/replica_scheduler/sarathi_replica_scheduler.py`

**核心机制**:
- **Chunked Prefill**: 将大的prefill分成多个chunk处理
  ```python
  next_num_tokens = min(
      request.num_prefill_tokens - request.num_processed_tokens,
      chunk_size - num_batch_tokens
  )
  ```
- **Prefill-Decode分离**: 区分处理running_prefills和completed prefills

**调度流程**:
```
1. 处理_preempted_requests中的completed prefill请求 (decode阶段)
2. 处理_preempted_requests中的partial prefill请求
3. 处理_request_queue中的新请求
4. 每个请求最多处理chunk_size个tokens
```

**配置参数**:
- `chunk_size`: Prefill chunk大小 (如512, 1024)
- 继承vLLM的watermark和batch约束

#### 3. NestedBookingLimitReplicaScheduler
**文件**: `vidur/scheduler/replica_scheduler/nested_booking_limit_replica_scheduler.py`

**核心机制**:
- **Segment划分**: 按decode长度将请求分段
- **Booking Limit**: 每个segment/stage有独立的容量限制
- **按权重分配**: `weight = processing_count * arrival_rate_sum`

**Segment划分逻辑**:
```python
# 假设有4种请求类型: decode = [10, 20, 30, 40]
# Segment1 (stage 0-10): 所有请求, 处理1+decode_min=11次
# Segment2 (stage 11-20): decode>10的请求, 处理10次
# Segment3 (stage 21-30): decode>20的请求, 处理10次
```

**Booking Limit计算**:
```python
seg1_weight = seg1_processing * seg1_arrival_sum  # 11 * 0.86
seg2_weight = seg2_processing * seg2_arrival_sum  # 10 * 0.61
seg3_weight = seg3_processing * seg3_arrival_sum  # 10 * 0.11

# 按权重比例分配total_limit
seg1_total_limit = total_limit * (seg1_weight / total_weight)
seg1_per_stage = seg1_total_limit / seg1_processing
```

**调度流程**:
```
1. 将preempted请求归回队列
2. 按current_stage分组
3. 检查Segment1起始stage是否达到booking limit
   └─> 不足: 检查是否超时，超时则强制调度
   └─> 满足: 从各stage取limit数量的请求
4. 依次检查Segment2, Segment3
5. 选中请求调用advance_stage()推进阶段
```

**配置参数**:
- `total_limit`: 总容量限制
- `prompt_types`: 请求类型定义 (prefill, decode, arrival_rate)

#### 4. 其他调度器

| 调度器 | 特点 |
|--------|------|
| OrcaReplicaScheduler | ORCA论文实现，连续批处理 |
| LightLLMReplicaScheduler | LightLLM风格调度 |
| FasterTransformerReplicaScheduler | FasterTransformer风格，静态批处理 |
| BookingLimitReplicaScheduler | 基础booking limit策略 |
| GeneralNestedBookingLimitReplicaScheduler | 通用化的nested booking limit |
| ModifiedBookingLimitReplicaScheduler | 修改版booking limit |

---

### 调度器选择指南

| 场景 | 推荐全局调度器 | 推荐副本调度器 |
|------|---------------|---------------|
| 均匀负载，简单场景 | RoundRobin | vLLM |
| 异构请求，负载不均 | LOR | Sarathi |
| 多类型请求，需要公平性 | LOR | NestedBookingLimit |
| 长prefill，需要分块 | LOR | Sarathi |
| 基准测试，随机化 | Random | vLLM |

---

### 调度器扩展示例

#### 实现自定义全局调度器:
```python
# vidur/scheduler/global_scheduler/my_global_scheduler.py
from vidur.scheduler.global_scheduler.base_global_scheduler import BaseGlobalScheduler

class MyGlobalScheduler(BaseGlobalScheduler):
    """
    自定义全局调度器

    策略: 根据请求大小选择副本
    """

    def schedule(self) -> List[Tuple[int, Request]]:
        self.sort_requests()
        request_mapping = []

        while self._request_queue:
            request = self._request_queue.pop(0)
            # 大请求分配给负载低的副本
            if request.total_tokens > 1000:
                replica_id = self._find_least_loaded_replica()
            else:
                replica_id = self._request_counter % self._num_replicas
                self._request_counter += 1
            request_mapping.append((replica_id, request))

        return request_mapping

    def _find_least_loaded_replica(self) -> int:
        return min(
            self._replica_schedulers.items(),
            key=lambda x: x[1].num_pending_requests
        )[0]
```

#### 实现自定义副本调度器:
```python
# vidur/scheduler/replica_scheduler/my_replica_scheduler.py
from vidur.scheduler.replica_scheduler.base_replica_scheduler import BaseReplicaScheduler

class MyReplicaScheduler(BaseReplicaScheduler):
    """
    自定义副本调度器

    策略: 优先处理短请求
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._preempted_requests = []
        self._num_running_batches = 0

    def _get_next_batch(self) -> Batch:
        # 按请求大小排序
        self._request_queue.sort(key=lambda r: r.total_tokens)

        requests = []
        num_tokens = []

        while self._request_queue and len(requests) < self._max_batch_size:
            request = self._request_queue[0]

            num_blocks = ceil(request.num_prefill_tokens / self._config.block_size)
            if not self.can_allocate(num_blocks):
                break

            request = self._request_queue.pop(0)
            self.allocate(request.id, num_blocks)
            requests.append(request)
            num_tokens.append(self._get_request_next_num_tokens(request))

        if requests:
            return Batch(self._replica_id, requests, num_tokens)
        return None

    def on_batch_end(self, batch: Batch) -> None:
        self._num_running_batches -= 1
        for request in batch.requests:
            if request.completed:
                self.free(request.id)
            else:
                self._preempted_requests.append(request)
```

---

## WAIT-CP 实验状态 (2026-03-23)

### 当前代码
- **文件**: `vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py`
- **版本**: Flow-balanced per-request chunk + booking limit
- **Git**: `revision` 分支, commit `c1a708a`
- **参数**: tl (booking limit) + cs (per-request prefill chunk size)

### 参数语义 (详见 `docs/research/wait_cp_parameter_semantics.md`)

| 参数 | 含义 |
|------|------|
| tl | booking limit, 控制 in-system 总请求数 |
| cs | 每个 prefill 请求每 batch 处理的 new tokens 数 |
| K = ceil(l₀/cs) | prefill 需要的 batch 数 |
| P = tl/(K+l₁) | per-stage throughput |
| pipeline = K+l₁ | 请求从 admit 到 complete 的 batch 数 |

### Batch 计算量分解

| 组件 | WCP (tl=21,cs=256) | Sarathi(512) | WCP 优势 |
|------|-------------------|-------------|---------|
| prefill attention | 2×256²=131k | 502²=252k | **-48%** |
| decode attention | 19×522=9.9k | 10×522=5.2k | +90% |
| MLP/norm (new tokens) | 531 | 512 | +4% |
| CPU overhead (requests) | 21 | 11 | +91% |

**净效果: prefill attention 大幅节省 > decode + CPU 开销 → 小幅净赢**

### 最佳实验结果 (tl=21, cs=256, l₀=512, l₁=20, nreq=5000)

| rate | Sarathi(512) | WCP | gap |
|------|-------------|-----|-----|
| 12 | 0.480s | 0.468s | **-2.4%** |
| 14 | 0.552s | 0.528s | **-4.3%** |
| 16 | 0.567s | 0.603s | +6.3% |
| 18 | 0.784s | 0.699s | **-10.8%** |
| 20 | 0.987s | 0.824s | **-16.5%** |
| 22 | 1.853s | 1.024s | **-44.7%** |

**5/6 rates WIN。tl=21 是甜点 (P=0.955 < 1)。**

### 关键约束
- **tl=21 赢, tl≥22 全输**: P≥1 时 batch > Sarathi → throughput 下降 → 高 rate 崩溃
- **tl 越大越差**: 更多 decode requests → 更多 per-request overhead → 抵消 attention 节省
- **甜点条件**: P < 1 且 K > 1 (需要多 prefill 并行才有 attention 二次方优势)

### Baseline Profiling (存 `experiments.db`)

| 算法 | r=12 | r=14 | r=16 | r=18 | r=20 | r=22 | r=24 |
|------|------|------|------|------|------|------|------|
| Sarathi(512) | 0.480s | 0.552s | 0.567s | 0.784s | 0.987s | 1.853s | 9.865s |
| vLLM | 1.096s | 0.852s | 1.255s | 2.123s | 6.946s | - | - |

### 进度报告
- `docs/research/wait_cp_parameter_semantics.md` - 参数语义与 batch 计算量分析
- `docs/progress/2026_03_22_flow_balanced_breakthrough.md` - flow-balanced 突破
- `docs/progress/2026_03_21_wait_cp_verification.md` - 验证与假象排查
- `docs/progress/2026_03_21_chunk_size_reinterpretation.md` - chunk 语义重定义
- `docs/progress/2026_03_20_wait_cp_param_sweep.md` - 参数空间扫描
