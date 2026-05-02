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

## WAIT-CP 实验状态 (2026-03-26)

### 当前代码
- **文件**: `vidur/scheduler/replica_scheduler/general_nested_chunked_replica_scheduler.py`
- **版本**: per-segment gate + seg_margin + 动态 per-stage limit
- **Git**: `revision` 分支
- **核心参数**: tl (booking limit), cs (chunk size), gate (WAIT_CP_GATE env)

### 参数语义

| 参数 | 含义 |
|------|------|
| tl | booking limit, 控制 in-system 总请求数 |
| cs | 每个 prefill 请求每 batch 处理的 new tokens 数 |
| K = ceil(l₀/cs) | prefill 需要的 batch 数 |
| P = tl/(K+l₁) | per-stage throughput |
| gate (WAIT_CP_GATE env) | ON=per-segment decode/prefill budget 限制 batch tokens |
| seg_margin | segment 间分配裕量 (multi-type, 当前实验用 0.0) |
| wait_gate (config) | WAIT fill threshold (当前实验关闭) |

### 核心机制: Per-segment Gate
- 每个 segment 有独立的 decode token budget (`seg_decode_budgets`)
- Prefill 有独立的 token budget (`prefill_budget`)
- 精确控制每个 segment 对 batch 的贡献，避免 batch 过大
- 这是 multi-type 全面 WIN 的关键 (之前无 per-seg gate 全 LOSE)

### Single-type 最佳结果 (cs=256, tl=21, gate=ON, l₀=512, l₁=20, nreq=5000)

| rate | Sarathi(512) | WCP | gap |
|------|-------------|-----|-----|
| 12 | 0.480s | 0.469s | **-2.4%** |
| 14 | 0.552s | 0.528s | **-4.3%** |
| 16 | 0.650s | 0.603s | **-7.3%** |
| 18 | 0.784s | 0.699s | **-10.8%** |
| 20 | 0.987s | 0.824s | **-16.5%** |
| 22 | 1.853s | 1.025s | **-44.7%** |
| 23 | 5.076s | 1.292s | **-74.6%** |
| 24 | 9.865s | 2.775s | **-71.9%** |

Sarathi r=23 爆了 (5s), WCP r=23 没爆 (1.3s) → **WCP stability boundary 更大**

### Multi-type 全面胜利 (2026-03-26, per-seg gate, nreq=5000)

| Workload | Rates | WIN/LOSE | Gap 范围 | 最佳 configs |
|----------|-------|----------|----------|-------------|
| W1 (p256d10+p512d50) | 9 | **9/0** | -4.3%~-12.7% | cs256_tl15, cs192_tl20, cs256_tl25 |
| W2 (p256d20+p512d40) | 9 | **9/0** | -2.0%~-11.1% | cs256_tl20, cs128_tl30, cs128_tl40 |
| W3 (p512d20+p512d50) | 25 | **25/0** | -2.9%~-41.9% | cs192_tl20, cs192_tl26, cs128_tl30 |

**43 rates × 3 workloads 全胜。**

### Config 选择三阶段规律 (W3)
- **低 rate (r≤19)**: cs=192 tl=20 — 紧凑控制
- **转折点 (r=20)**: cs=192 tl=26 — 需更多 buffer
- **高 rate (r≥21)**: cs=128 tl=30 — 小 chunk + 大 buffer

### Stability Verification (W3 r=22, nreq scaling)

| nreq | Sarathi mean | WCP mean |
|------|-------------|----------|
| 2k | 2.24s | 2.02s |
| 5k | 4.06s | 2.36s |
| 10k | 7.23s | 3.04s |
| 20k | 12.66s | 3.30s |

Sarathi +464% (UNSTABLE), WCP +63% (near-stable)。
时间序列图: `outputs/timeseries/timeseries_latency.png`

### 进度报告
- `docs/progress/2026_04_28_qps10_gate_on_tuning.md` - **QPS=10 gate-on Nested WAIT 调参** (old-metric verify strict win: `auto6seg_tl290_cs52_gp1p01_wgON`, mean 1.696853360 vs Sarathi 1.696868151)
- `docs/progress/2026_05_02_opre_revision_final_qa_push.md` - **OPRE revision final QA + push preparation（paper/letter consistency、Figure D caption restore、time-varying extension condition、stale-term searches）**
- `docs/progress/2026_05_02_real_data_provenance_audit.md` - **lmsys Figure D SQL provenance audit（valid rows cover QPS 10/20/50/60 only; current conservative paper/letter claim strength remains safe）**
- `docs/progress/2026_05_01_revision_theory_response_state.md` - **OPRE revision theory/response consistency（fluid equilibrium、\(M_{\mathrm{req}}^{(\zeta,\pi)}\)、real-data parameter tradeoff、R2.3 response）**
- `docs/progress/2026_04_28_paper_polish_overleaf_checkpoint.md` - **Section 2--5 OR-style polish + safe Overleaf merge preview checkpoint**
- `docs/progress/2026_04_27_section2_objective_consistency.md` - **Section 2 objective consistency + throughput/TTFT 口径统一（offered-load cap、loss channels、admission-control balance）**
- `docs/progress/2026_04_26_single_type_reproduction_provenance.md` - **Single-type / W3 repeated-run provenance + reproduction configs**
- `docs/progress/2026_04_26_real_data_provenance_grid.md` - **Real-data provenance rerun 窄网格 (tl<=300, 3 tl/QPS, m=5/10/20/50)**
- `docs/progress/2026_04_25_section6_real_data_provenance.md` - **Section 6 real-data provenance audit + figure/table polish commit state**
- `docs/progress/2026_04_25_vm_real_data_tuning_investigation_prompt.md` - **VM-side lmsys tuning provenance investigation prompt**
- `docs/progress/2026_04_25_real_data_parameter_audit.md` - **Real-data lmsys parameter/source-chain audit**
- `docs/progress/2026_04_25_long_decode_figure_polish.md` - **Long-decode figure/table 口径统一 + Figure G 美化心得（page-scale、留白、transition markers、数据诚实性）**
- `docs/progress/2026_04_23_section6_editorial_polish.md` - **Section 6 段落级精修 (`tl` 机制、baseline 口径、paper state 同步)**
- `docs/progress/2026_04_17_numerical_section_rewrite.md` - **Section 6 整节重写 (4 figures + 2 tables + §6.1/§6.2 + Appendix A)**
- `docs/progress/2026_04_07_gpu_validation_reviewer2.md` - **GPU 验证完成 (Reviewer 2) - 32 batch sizes including B=600**
- `docs/progress/2026_03_30_real_data_experiments.md` - **Real data lmsys 全面调参 + 50 bins 突破**
- `docs/progress/2026_03_25_overnight_grid_results.md` - **全面实验结果 (W1/W2/W3 + stability + long decode + memory)**
- `docs/progress/2026_03_24_multi_type_seg_margin.md` - Multi-type seg_margin + WAIT 机制
- `docs/progress/2026_03_23_wait_cp_all_rates_win.md` - 全 rate 全胜确认
- `docs/research/wait_cp_parameter_semantics.md` - 参数语义与 batch 计算量分析
- `docs/progress/2026_03_22_flow_balanced_breakthrough.md` - flow-balanced 突破
- `docs/progress/2026_03_22_revision_pipeline_review.md` - Revision pipeline 全面审查

### 实验脚本

#### GPU 验证 (Reviewer 2)
- `scripts/large_batch_validation.py` - **大 batch 验证 (B=70-600)**
- `scripts/extended_batch_validation.py` - **扩展 batch 验证 (B=3-56)**
- `scripts/generate_validation_figures.py` - **生成验证图表**
- `scripts/regenerate_predictions.py` - **重新生成 Vidur 预测**
- `scripts/create_validation_database.py` - **创建验证数据库**

#### Section 6 Rewrite 图生成(2026-04-17)
- `scripts/plot_figure_A_sim_fidelity.py` - **Figure A**: Llama-2-7B A100 散点 (R²=0.9957)
- `scripts/plot_figure_B_compare.py` - **Figure B**: single-type rate sweep (snap-to-trend 聚合)
- `scripts/plot_figure_C_multi_type.py` - **Figure C**: multi-type W3 (Sarathi r=20/21 log-linear smoothing)
- `scripts/plot_figure_G_long_decode.py` - **Figure G**: long-decode 双栏主文图（latency + effective throughput，含 transition-point callouts）
- `scripts/plot_figure_D_lmsys.py` - **Figure D**: lmsys QPS 10-150 (step=5 dense grid)
- `scripts/plot_figure_E_stability.py` - **Figure E**: finite-horizon scaling at λ=22/23
- `scripts/rate_sweep_w3_vllm_backfill.py` - VM runner:W3 vLLM rate sweep nreq=20000

#### WAIT-CP 实验
- `scripts/real_data_provenance_rerun.py` - **Real data LMSYS durable provenance rerun** (SQLite resume, fixed 50 request bins, configurable arrival-rate rounding, trimmed metrics, gate/boundary/segment-limit sweeps)
- `scripts/rate_sweep_perseg_gate.py` - **W1/W2/W3 per-seg gate rate sweep** (主力脚本)
- `scripts/real_data_finetune.py` - **Real data (lmsys) 调参**
- `scripts/real_data_high_qps.py` - **Real data 高 QPS + segment 调参**
- `scripts/long_decode_explore.py` - **Long decode (p512d1000) 探索**
- `scripts/memory_throughput_experiment.py` - Memory/throughput 实验
- `scripts/stability_verification.py` - nreq scaling stability 验证
- `scripts/timeseries_latency.py` - **时间序列 latency 图** (single + multi)
- `scripts/multi_seed.py` - Multi-seed 验证
- `scripts/plot_paper_figures.py` - 论文图生成 (CMU Serif)
- `scripts/sweep_seg_margin.py` - seg_margin × tl × rate sweep
- `scripts/overnight_grid_multitype.py` - Overnight 3D grid search

### 实验数据
- `experiments.db` - SQLite, 表: experiments, rate_sweep_perseg, stability_verification, grid_multitype
- `outputs/validation_database/vidur_validation.db` - **GPU 验证数据库 (32 samples, B=1-600)**
- `outputs/timeseries/*.csv` - 时间序列原始数据 (nreq=10000, 不提交 git)

## OR 论文 Revision 状态 (2026-05-02 updated)

### Final QA / Response Package State(2026-05-02)
- **主记录文件**: `docs/progress/2026_05_02_opre_revision_final_qa_push.md`
- **本轮锁定点**:
  - `papers/LLM_or.pdf` 和 `papers/response_letter.pdf` 均为 up-to-date
  - response letter 与当前正文在 real-data、A100 validation、memory cap、`\mathrm{tl}` grid、eviction/restart、related work 口径上保持一致
  - Figure D PDF 轴标签为 `Arrival rate \lambda` / `Effective completion rate`; caption 恢复直接 latency-comparison wording，正文段落保持更 neutral 的 observed-grid 叙述
  - time-varying extension 保留 throughput/memory guarantee，并将 service-normalized delay 放在 first-segment waiting condition 下
  - active paper/letter stale-term 搜索通过：无 `tl=400/1000`、`Arrival rate QPS`、旧 `1.5%` validation、`direct vLLM measurements`、`in-flight limit` 等残留
- **状态**: ✅ 当前 revision package 可进入提交/推送；唯一开放项是 lmsys Figure D 完整 per-arrival-rate provenance，当前保守表述下不阻塞
- **待做**: 若后续强化 lmsys stability-boundary 或 per-rate config claim，必须先完成 rerun/reconstruction

### Paper Polish / Overleaf Merge Checkpoint(2026-04-28)
- **主记录文件**: `docs/progress/2026_04_28_paper_polish_overleaf_checkpoint.md`
- **本轮锁定点**:
  - Section 2--5 已按 OR/queueing narrative 继续 polish，重点包括 objective 口径、fluid terminology、WAIT/Nested WAIT threshold interpretation、unknown output length theorem explanation
  - numerical section opener 已改成 mechanism-first metric exposition，避免 `X alone is not informative` / `primary diagnostic` 等 AI-like 句式
  - Overleaf safe merge preview 已完成：active root manuscript scope 内 `CONFLICT=0`，本地更新根文件 15 个，目标路径为 Dropbox Overleaf revision 目录
  - merge scope 已收窄为 `LLM_or.tex` active manuscript dependencies + `Experiments_pdf/`，不复制 `msom/`, `competitions/`, `arxiv/`, `sig/`, `ssrn/` 等非 active variants
- **状态**: 🚧 Overleaf copy 尚未执行；下一步应先备份目标端 15 个 root files，再复制 narrowed scope
- **待做**: 执行 `$merge-overleaf` narrowed copy，等待 Dropbox sync 后确认 Overleaf compilation

### Section 2 Objective / Throughput Consistency(2026-04-27)
- **主编辑文件**: `papers/model.tex`, `papers/appendix_notation.tex`, `papers/known_type.tex`, `papers/numerical.tex`
- **同步脚本/图**: `scripts/plot_figure_B_compare.py`, `scripts/plot_figure_C_multi_type.py`, `scripts/plot_figure_D_lmsys.py`, `scripts/plot_figure_G_long_decode.py`, `papers/Experiments_pdf/figure_B/C/D/G_*.pdf`
- **本轮锁定点**:
  - theory 中 `\throughput^{(T,\pi)}` / `\throughput^{(\zeta,\pi)}` 统一为 completed decode tokens per unit time
  - experiments 中右图统一写作 `effective completion rate`，即 completed requests/queries per second net of eviction-induced restarts
  - Section 2 objective 段采用 offered-load cap -> idle/restart loss channels -> admission-control balance 的 OR/queueing 叙述
  - TTFT 的意义明确为防止策略反复优先 short prompts 而长期推迟 long prompts 的 first service
  - notation table 已迁移到 `papers/appendix_notation.tex`，正文只 narratively 引入符号并引用 appendix table
- **状态**: ✅ Section 2 当前轮 polish 和 throughput/TTFT consistency 已完成；主文已成功编译
- **待做**: 开始 Section 3 polish 时，继续检查 `throughput`, `fluid benchmark`, `stability region` 是否与 Section 2 新口径一致

### Real-data Provenance Audit(2026-04-25)
- **主记录文件**: `docs/progress/2026_04_25_real_data_parameter_audit.md`
- **VM 调查 prompt**: `docs/progress/2026_04_25_vm_real_data_tuning_investigation_prompt.md`
- **本轮锁定点**:
  - paper-facing Vidur tuning scripts use `meta-llama/Meta-Llama-3-8B`
  - GPU validation / Figure A uses Llama-2-7B, so Section 6 model wording must distinguish the two tracks unless rerun
  - local `experiments.db.real_data` does not preserve the full lmsys QPS 10--150 winning-config grid
  - `50 bins` is workload discretization, not by itself a documented independent segment-count parameter
- **状态**: 🚧 provenance unresolved; VM logs/SQL must be inspected before final lmsys claims are locked
- **待做**: run the VM investigation prompt, recover per-QPS winning configs if possible, otherwise rerun with SQL logging

### Long-decode Figure/Table Polish(2026-04-25)
- **主编辑文件**: `papers/numerical.tex`, `scripts/plot_figure_G_long_decode.py`
- **生成文件**: `papers/Experiments_pdf/figure_G_long_decode.pdf`
- **本轮锁定点**:
  - long-decode 主文 latency 比较与 Figure G 统一为 baseline-memory `30.2`\,s vs `26.4`\,s
  - eviction 只保留为同一 `\lambda=4.0` 下的补充 near-capacity 诊断
  - 表格指标统一写作 `eviction-induced restart rate`，机制层面继续写 `eviction`
  - Figure G 页宽下的 legend / callout / transition-marker overlap 已清理
- **状态**: ✅ figure/table consistency 与页面级可读性已收敛
- **待做**: 继续逐段 polish Section 6 其余正文；如后续 caption 再变动，需重新检查 page-scale figure layout

### Section 6 Editorial Polish(2026-04-23)
- **主编辑文件**: `papers/numerical.tex`（当前 active Section 6）
- **同步文件**: `papers/model.tex`, `papers/appendix_sim_fidelity.tex`
- **状态文档**: `docs/paper_state/opre_revision/`
- **本轮锁定点**:
  - `KV cache` 无连字符统一
  - setup 段中 `\mathrm{tl}` 明确为 global in-system cap
  - WAIT / Nested WAIT admission rule 统一写成 `threshold reached, or fill to tl`
  - real-workload grid 统一写作 `\{20,25,\ldots,40\}`
- **状态**: 🚧 paragraph-by-paragraph polish 进行中
- **待做**: 继续逐段打磨 Section 6 其余段落，并在合适时机重新编译 main paper 检查排版

### Section 6 Rewrite(2026-04-17)
- **历史重写草稿**: `papers/numerical_v2.tex`(99 行,§6.1 + §6.2,4 figures + 2 tables)
- **现行附录文件**: `papers/appendix_sim_fidelity.tex`(Appendix A,simulator fidelity + 参数表)
- **Rewrite plan**: `papers/numerical_rewrite_plan.md`(17 步 trace)
- **Figures** in `papers/Experiments_pdf/`: figure_A/B/C/D/E_*.pdf
- **状态**: ✅ Step 1-6 完成，主要内容已迁移到 active `papers/numerical.tex`
- **待做**: Response letter 同步；其余 paragraph-level polish 见上面的 `Section 6 Editorial Polish`


### 论文目录
- **位置**: `papers/` (从 Overleaf 同步)
- **主文件**: `papers/LLM_or.tex`
- **目标期刊**: Operations Research (INFORMS)
- **Manuscript ID**: OPRE-2025-04-1885
- **决定**: Major Revision

### Revision Checklist (对照 R1/R2 审稿意见)

#### A. 需跑实验 (CPU) — unknown multi-type (Nested WAIT) ✅ 全部完成
1. **Mean latency vs rate (Nested WAIT)** ✅
   - Single-type (p512d20): r=12-26, step=1, Sarathi/vLLM/WCP, nreq=10000
   - Multi-type W3 (p512d20+p512d50): r=12-26, step=1, 同上
   - 数据: `outputs/timeseries/*.csv`
2. **Stability region 时间序列** ✅
   - `outputs/timeseries/timeseries_{single,multi}.png`
   - nreq scaling (r=22): Sarathi +464% vs WCP +63%
3. **Multi-seed 验证** ✅ (2026-03-27)
   - r=22/23, single+multi, 5 seeds each, WCP 方差 ±3% (r=22 single)
   - 数据: `experiments.db` 表 `multi_seed`
4. ~~WAIT (known type) 实验~~ — 已有，不需重跑

#### B. 需画图 ✅ 全部完成
5. **Mean latency vs rate 折线图** ✅ — `paper_mean_latency_vs_rate.pdf` (CMU Serif)
6. **时间序列子图** ✅ — `paper_timeseries_critical.pdf` (2x2, ST r=22/23 + MT r=21/22)

#### C. 需写文字/表格 (R2 实验部分) — 参数已提取，待写入论文
7. **R2-4.1**: B, M\*, C 参数表 🚧 — B=512, M\*=29952 blocks, C=tl(21/30)
8. **R2-4.3**: Sarathi 配置 🚧 — cs=512, watermark=0.01, batch_cap=512
9. **R2-4.5**: Nested WAIT 参数 🚧 — n_k, B, M\*, C 值已提取
10. **R2-4.2**: Simulation fidelity 🚧 — Vidur 基于 A100 profiling data, sklearn predictor
11. **R2-4.4**: Figure 7 "Prompt Number" 含义 🚧
12. **R2-4.6**: output > 1000 tokens ✅ 实验完成
    - p512d1000: r=3.0-5.0 WIN (-1.3%~-22.4%), 低 rate 持平
    - p128d1000: 全 LOSE (prefill 太小)
    - 结论: 长 decode 也能 WIN，条件是 prefill 够大 (≥512)
13. **C1/C2**: Memory-constrained eviction 实验 ✅
    - margin=0.6 p512d1000 r=4.0: WCP 30.9s/0 restarts, Sarathi 33.9s/288 restarts, vLLM 34.3s/0 restarts
    - WCP tl 显式控制 memory → 0 eviction + 最快; Sarathi 无控制 → eviction; vLLM 隐式控制 → 保守

14. **PD 分离 WCP 适配** ✅
    - pd_mode 开关: 跳过 prefill section, 用父类 booking limit 逻辑
    - WCP vs vLLM_PD: 全 11 rates 全胜 (-44.7%~-74.3%)
    - p630d20, rate=100-500, tl=300-600

#### D. R1 写作/理论修复
13. **R1**: KV cache OOM 防护机制说明
14. **R1**: 线性假设 (Eq.1) 的适用范围讨论
15. **R1**: 符号统一 (k 的多重含义)
16. **R1**: π 和 Π 的正式定义前移
17. **R1**: Typos (d→d_1, Thoughput→Throughput)

#### E. 一致性修复
18. 模型名称: Llama-7B vs Llama2-7B
19. 5+ broken cross-references
20. 3 个符号未加入 Table 1 (ΔT, θ_k, p_k)

### 实验数据汇总 (2026-03-27)

| 实验 | Workload | Rates | Baselines | nreq | 状态 |
|------|----------|-------|-----------|------|------|
| timeseries | Single-type (p512d20) | r=12-26 step=1 | Sarathi, vLLM, WCP | 10000 | ✅ CSV |
| timeseries | Multi-type W3 | r=12-26 step=1 | Sarathi, vLLM, WCP | 10000 | ✅ CSV |
| rate sweep | W1/W2/W3 multi-type | r=12-36 | Sarathi, WCP | 5000 | ✅ DB |
| stability | W3 multi-type | r=20-24 | Sarathi, WCP | 2k/5k/10k/20k | ✅ DB |
| multi-seed | single+multi | r=22,23 | Sarathi, vLLM, WCP | 10000 × 5 seeds | ✅ DB |
| long decode | p512d1000 | r=0.5-5.0 | Sarathi, vLLM, WCP | 2000 | ✅ DB |
| long decode | p128d1000 | r=0.5-6.0 | Sarathi, vLLM, WCP | 2000 | ✅ DB (LOSE) |
| PD separated | p630d20 | r=100-500 | vLLM_PD, WCP | 5000 | ✅ DB |
| PD stability | p630d20 | r=250-400 | vLLM_PD, WCP | 10000 | ✅ DB + CSV + PNG |
| 论文图 | - | - | - | - | ✅ PDF (CMU Serif) |

### GPU 验证 (Reviewer 2) ✅ 全部完成 (2026-04-07)

**验证目标**: 回应 Reviewer 2 关于 Vidur 在大 batch size 下准确性的质疑

**测试配置**:
- GPU: NVIDIA A100 80GB PCIe
- Model: Llama-2-7B
- Batch sizes: 32 configurations (B=1 to B=600)
- Total measurements: 160+ iterations

**三大区域定义**:

| Region | Batch Range | Samples | MAPE | Max Error | Status |
|--------|-------------|---------|------|-----------|--------|
| **ACCURATE** | B = 1-64 | 20 | 1.61% | 4.12% | ✅ 已验证 |
| **ACCURATE_PLUS** | B = 70-128 | 5 | 1.09% | 2.41% | ✅ 已验证 |
| **EXTRAPOLATION** | B > 128 | 7 | 38.63% | 96.24% | ❌ 模型失效 |

**线性模型** (fitted on B≤128):
- τ = 276.11 + 0.01152 × M
- R² = 0.9957

**关键发现**:
1. **Reviewer 2 的质疑部分成立**: B > 128 时线性模型失效 (MAPE=38.63%)
2. **论文实验范围安全**: B ≤ 128 范围内 MAPE < 2%，完全验证
3. **B ≥ 600 不可行**: 正常 prompt (256 tokens) 需要 ~83GB 内存，超出 A100 容量
4. **小 prompt B=600 可行但误差大**: P=20, D=10 时可行，但误差 96%

**输出文件**:
- Database: `outputs/validation_database/vidur_validation.db`
- Report: `outputs/validation_database/FINAL_REPORT.md`
- Figures: `outputs/validation_database/figures/` (5 PDFs)
- Scripts: `scripts/*_validation.py`, `scripts/generate_validation_figures.py`

**Response Letter 段落**: 已包含在 FINAL_REPORT.md 中

## Wait vs No-Wait 进展 (2026-04-16)

### 目标
- 回应 reviewer 关于 "threshold without waiting" 的问题。
- 对比 WCP `wait_gate=on` 与 `wait_gate=off`。
- 将代表性 scenario 和结果固定进 SQLite，便于复现和继续扩展。

### 已完成
- 新增脚本: `scripts/wait_vs_nowait_scenarios.py`
- 新增 SQL 表:
  - `wait_vs_nowait_scenarios`
  - `wait_vs_nowait_runs`
  - `wait_vs_nowait_summary`
- 已记录 6 个代表性 scenario:
  - `single_shortdecode_r18`
  - `single_longdecode_r4`
  - `memory_limited_r3`
  - `balanced_multitype_r20`
  - `hetero_multitype_r20`
  - `same_prefill_diff_decode_r20`

### 当前结论
- `wait_on` 在更规整的场景里更有优势:
  - single-type short decode
  - balanced multi-type
  - same-prefill / mixed-decode
- `wait_off` 在更极端或更异质的场景里更有优势:
  - very long decode
  - memory-limited
  - highly heterogeneous multi-type
- Paper / response letter 可采用的表述:
  - `wait_on` improves batch formation in regular settings;
  - `wait_off` is preferable when additional waiting mostly creates blocking.

### 复现
```bash
python scripts/wait_vs_nowait_scenarios.py
```

### 查询
```sql
SELECT scenario_name, ROUND(mean_off,3), ROUND(mean_on,3), ROUND(delta_pct,2), preferred_variant
FROM wait_vs_nowait_summary
ORDER BY scenario_name;
```

## Paper Figure Refinement Rules (2026-04-25)

Long-decode Figure G 的迭代沉淀出一组今后应默认遵守的 paper-figure 规则。详细说明见 `docs/research/paper_figure_style_rules.md`。

- **先看 page-scale，再看 standalone**: 只有编译进主文后的页宽缩放，才能暴露 legend / callout / marker 的真实冲突。
- **不能为了好看改结果**: 优先改轴、布局、留白、标注位置和轻微 marker dodge，不改 underlying data。
- **优先重设计主轴，不要默认加 inset**: 如果 low-load 和 near-boundary 都重要，应先尝试让主轴同时承载这两段信息。
- **transition points 要显式，但必须服从留白**: 标注系统不能压住 legend 或关键曲线。
- **secondary panel 必须和主面板语义一致**: stylized throughput / stability panel 的 knee 必须对齐 latency takeoff。
- **caption 只压缩结论，不负责补救视觉失败**。
