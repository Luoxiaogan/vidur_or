# Per-Request Metrics CSV Export Implementation Plan

## 目标

在每个请求完成时，将详细的 per-request metrics 导出到 CSV 文件，供后续分析使用。

---

## 前置条件 (用户已完成)

用户已修改代码使 `lb_entry_time` (HTTP接收时间) 可在 completion 时访问：
- `io_struct.py`: 添加 `received_time` 字段
- `tokenizer_manager.py`: 传递 `received_time`
- `scheduler.py:1478,1746`: 设置 `req.time_stats.lb_entry_time = recv_req.received_time`

---

## 需要记录的字段

| 字段 | 来源 | 说明 |
|------|------|------|
| rid | req.rid | 请求ID |
| seqlen | req.seqlen | 总序列长度 |
| extend_input_len | req.extend_input_len | extend batch 处理的 token 数 |
| cached_tokens | req.cached_tokens | 缓存命中的 token 数 |
| finished_reason | req.finished_reason.to_json() | 完成原因 |
| finished_len | req.finished_len | 完成位置 |
| lb_entry_time | req.time_stats.lb_entry_time | HTTP 接收时间 |
| decode_prealloc_queue_entry_time | req.time_stats.decode_prealloc_queue_entry_time | 进入预分配队列时间 |
| decode_transfer_queue_entry_time | req.time_stats.decode_transfer_queue_entry_time | 进入传输队列时间 |
| wait_queue_entry_time | req.time_stats.wait_queue_entry_time | 进入等待队列时间 |
| forward_entry_time | req.time_stats.forward_entry_time | 进入 GPU 执行时间 |
| completion_time | req.time_stats.completion_time | 完成时间 |
| retraction_count | req.retraction_count | 被 retract 次数 |
| is_retracted | req.is_retracted | 当前是否被 retract |
| retracted_stain | req.retracted_stain | 是否曾被 retract |
| kv_committed_len | req.kv_committed_len | 已提交的 KV 长度 |
| kv_allocated_len | req.kv_allocated_len | 已分配的 KV 长度 |
| input_len | len(req.origin_input_ids) | 输入长度 |
| output_len | len(req.output_ids) | 输出长度 |
| disagg_mode | req.time_stats.disagg_mode_str() | 分离模式 |

---

## 实现步骤

### Step 1: 添加 CLI 参数

**文件**: `sglang/python/sglang/srt/server_args.py`

1. 在 `ServerArgs` dataclass 中添加字段 (约 line 388，`export_batch_metrics_to_file` 附近):
```python
export_request_metrics_to_csv: Optional[str] = None
```

2. 在 `add_cli_args()` 中注册参数 (约 line 3283):
```python
parser.add_argument(
    "--export-request-metrics-to-csv",
    type=str,
    default=ServerArgs.export_request_metrics_to_csv,
    help="Export per-request metrics to CSV file path",
)
```

### Step 2: 定义 RequestMetrics 数据类

**文件**: `sglang/python/sglang/srt/managers/scheduler_metrics_mixin.py`

在 `BatchMetrics` 之后 (约 line 82) 添加:

```python
@dataclass
class RequestMetrics:
    """Per-request metrics for CSV export."""
    rid: str
    seqlen: int
    extend_input_len: int
    cached_tokens: int
    finished_reason: str
    finished_len: Optional[int]
    lb_entry_time: float
    decode_prealloc_queue_entry_time: float
    decode_transfer_queue_entry_time: float
    wait_queue_entry_time: float
    forward_entry_time: float
    completion_time: float
    retraction_count: int
    is_retracted: bool
    retracted_stain: bool
    kv_committed_len: int
    kv_allocated_len: int
    input_len: int
    output_len: int
    disagg_mode: str
```

### Step 3: 定义 RequestMetricsCSVExporter 类

**文件**: `sglang/python/sglang/srt/managers/scheduler_metrics_mixin.py`

在 `BatchMetricsCSVExporter` 之后 (约 line 100) 添加:

```python
class RequestMetricsCSVExporter:
    """Exports per-request metrics to CSV."""

    def __init__(self, filepath: str):
        self.filepath = filepath
        self._write_header()

    def _write_header(self):
        with open(self.filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([field.name for field in fields(RequestMetrics)])

    def record(self, metrics: RequestMetrics):
        with open(self.filepath, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(asdict(metrics).values())
```

### Step 4: 初始化 exporter

**文件**: `sglang/python/sglang/srt/managers/scheduler_metrics_mixin.py`

在 `init_metrics()` 方法中 (约 line 178，batch_metrics_exporter 初始化之后):

```python
# Initialize request metrics exporter
self.request_metrics_exporter: Optional[RequestMetricsCSVExporter] = None
if self.server_args.export_request_metrics_to_csv:
    self.request_metrics_exporter = RequestMetricsCSVExporter(
        self.server_args.export_request_metrics_to_csv
    )
```

### Step 5: 添加导出方法

**文件**: `sglang/python/sglang/srt/managers/scheduler_output_processor_mixin.py`

添加辅助方法:

```python
def _export_request_metrics(self: Scheduler, req: Req):
    """Export per-request metrics to CSV."""
    import json

    finished_reason_str = ""
    if req.finished_reason is not None:
        finished_reason_str = json.dumps(req.finished_reason.to_json())

    metrics = RequestMetrics(
        rid=req.rid,
        seqlen=req.seqlen,
        extend_input_len=req.extend_input_len,
        cached_tokens=req.cached_tokens,
        finished_reason=finished_reason_str,
        finished_len=req.finished_len,
        lb_entry_time=req.time_stats.lb_entry_time,
        decode_prealloc_queue_entry_time=req.time_stats.decode_prealloc_queue_entry_time,
        decode_transfer_queue_entry_time=req.time_stats.decode_transfer_queue_entry_time,
        wait_queue_entry_time=req.time_stats.wait_queue_entry_time,
        forward_entry_time=req.time_stats.forward_entry_time,
        completion_time=req.time_stats.completion_time,
        retraction_count=req.retraction_count,
        is_retracted=req.is_retracted,
        retracted_stain=req.retracted_stain,
        kv_committed_len=req.kv_committed_len,
        kv_allocated_len=req.kv_allocated_len,
        input_len=len(req.origin_input_ids),
        output_len=len(req.output_ids),
        disagg_mode=req.time_stats.disagg_mode_str(),
    )
    self.request_metrics_exporter.record(metrics)
```

### Step 6: 在 completion 时调用导出

**文件**: `sglang/python/sglang/srt/managers/scheduler_output_processor_mixin.py`

在 `stream_output_generation()` 中 (line 1069，`req.log_time_stats()` 之后):

```python
            if (
                req.finished()
                and self.attn_tp_rank == 0
                and self.server_args.enable_request_time_stats_logging
            ):
                req.log_time_stats()

            # 新增: Export per-request metrics to CSV
            if (
                req.finished()
                and self.attn_tp_rank == 0
                and self.request_metrics_exporter is not None
            ):
                self._export_request_metrics(req)
```

### Step 7: 导入 RequestMetrics

**文件**: `sglang/python/sglang/srt/managers/scheduler_output_processor_mixin.py`

在文件顶部添加导入:

```python
from sglang.srt.managers.scheduler_metrics_mixin import RequestMetrics
```

---

## 需要修改的文件列表

| 文件 | 修改内容 |
|------|----------|
| `sglang/python/sglang/srt/server_args.py` | 添加 CLI 参数 |
| `sglang/python/sglang/srt/managers/scheduler_metrics_mixin.py` | 添加 RequestMetrics, RequestMetricsCSVExporter, 初始化逻辑 |
| `sglang/python/sglang/srt/managers/scheduler_output_processor_mixin.py` | 添加导出方法和调用 |

---

## 验证方案

### 1. 启动测试服务器

```bash
python -m sglang.launch_server \
    --model-path meta-llama/Llama-2-7b-chat-hf \
    --export-request-metrics-to-csv /tmp/request_metrics.csv \
    --enable-request-time-stats-logging \
    --disaggregation-mode decode \
    --disaggregation-decode-enable-fake-auto
```

### 2. 发送测试请求

使用 `mixing_experiments_for_DJ/sglang_mixing/test_1.py` 或简单的 curl 请求。

### 3. 验证 CSV 输出

```bash
# 检查 CSV 文件是否生成
head -5 /tmp/request_metrics.csv

# 验证列数和字段名
head -1 /tmp/request_metrics.csv | tr ',' '\n' | wc -l  # 应该是 20

# 检查时间戳是否合理 (非零)
awk -F',' 'NR>1 {print $7, $12}' /tmp/request_metrics.csv | head -5
```

### 4. 验证时间链完整性

检查每个请求的时间链：
- `lb_entry_time` < `decode_prealloc_queue_entry_time` < `wait_queue_entry_time` < `forward_entry_time` < `completion_time`

---

## 补充: 修复时间戳类型不一致问题

### 问题

| 字段 | 时钟类型 | 说明 |
|------|----------|------|
| `lb_entry_time` | `time.time()` | epoch 时间戳 (如 1706789012.123) |
| 其他 time_stats | `time.perf_counter()` | 相对时间 (如 12345.678) |

**问题**: `wait_queue_entry_time - lb_entry_time` 无法计算正确的时间间隔。

### 解决方案

添加 `lb_entry_time_perf` (perf_counter 版本)，用于与其他时间戳做差。

### Step 8: 添加 received_time_perf 到 TokenizedGenerateReqInput

**文件**: `sglang/python/sglang/srt/managers/io_struct.py`

在 `TokenizedGenerateReqInput` 中 (约 line 765，`received_time` 之后):
```python
received_time_perf: float = 0.0
```

### Step 9: 添加 lb_entry_time_perf 到 TimeStats

**文件**: `sglang/python/sglang/srt/metrics/collector.py`

在 `TimeStats` 中 (约 line 61，`lb_entry_time` 之后):
```python
lb_entry_time_perf: float = 0.0
```

### Step 10: 传递 received_time_perf

**文件**: `sglang/python/sglang/srt/managers/tokenizer_manager.py`

在 `_send_one_request()` 和 `_send_batch_request()` 中设置 `received_time_perf`:
```python
tokenized_obj.received_time_perf = time.perf_counter()
```

### Step 11: 设置 lb_entry_time_perf

**文件**: `sglang/python/sglang/srt/managers/scheduler.py`

在设置 `lb_entry_time` 的位置 (line 1478, 1746) 之后添加:
```python
req.time_stats.lb_entry_time_perf = recv_req.received_time_perf
```

### Step 12: 添加 lb_entry_time_perf 到 RequestMetrics

**文件**: `sglang/python/sglang/srt/managers/scheduler_metrics_mixin.py`

在 `RequestMetrics` 中 `lb_entry_time` 之后添加:
```python
lb_entry_time_perf: float
```

### Step 13: 在导出方法中使用 lb_entry_time_perf

**文件**: `sglang/python/sglang/srt/managers/scheduler_output_processor_mixin.py`

在 `_export_request_metrics()` 中添加:
```python
lb_entry_time_perf=req.time_stats.lb_entry_time_perf,
```

---

## 更新后的文件修改列表

| 文件 | 修改内容 |
|------|----------|
| `sglang/python/sglang/srt/server_args.py` | 添加 CLI 参数 ✓已完成 |
| `sglang/python/sglang/srt/managers/scheduler_metrics_mixin.py` | RequestMetrics, Exporter, 初始化 ✓已完成 + 添加 lb_entry_time_perf |
| `sglang/python/sglang/srt/managers/scheduler_output_processor_mixin.py` | 导出方法 ✓已完成 + 添加 lb_entry_time_perf |
| `sglang/python/sglang/srt/managers/io_struct.py` | 添加 received_time_perf |
| `sglang/python/sglang/srt/metrics/collector.py` | TimeStats 添加 lb_entry_time_perf |
| `sglang/python/sglang/srt/managers/tokenizer_manager.py` | 传递 received_time_perf |
| `sglang/python/sglang/srt/managers/scheduler.py` | 设置 lb_entry_time_perf |

---

## 使用示例

CSV 将包含 21 列 (新增 `lb_entry_time_perf`):

```csv
rid,...,lb_entry_time,lb_entry_time_perf,decode_prealloc_queue_entry_time,...
abc123,...,1706789012.123,12345.678,12345.789,...
```

**时间计算示例**:
- 绝对排序: 使用 `lb_entry_time` (epoch)
- 队列等待时间: `wait_queue_entry_time - lb_entry_time_perf` (perf_counter 差值)
