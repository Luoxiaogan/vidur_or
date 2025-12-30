# Vidur 模拟器输出指标说明

## 概述

运行 `run_experiment.py` 后，PNG 和 CSV 文件**不是由实验脚本直接生成**，而是由 Vidur 模拟器的 `MetricsStore.plot()` 方法自动生成。

## 输出目录结构

```
simulator_output/{timestamp}/
├── config.json                    # 模拟配置
├── chrome_trace.json              # Chrome tracing 格式的执行轨迹
├── request_metrics_{scheduler}.csv # 请求级别指标
├── throughput_{scheduler}.csv      # 吞吐量时间序列
└── plots/                         # 自动生成的图表
    ├── request_*.png/csv          # 请求相关指标
    ├── batch_*.png/csv            # Batch 相关指标
    ├── prefill_*.png/csv          # Prefill 相关指标
    ├── decode_*.png/csv           # Decode 相关指标
    └── replica_*.json             # Replica 利用率指标
```

## 图表生成逻辑

来源：`vidur/metrics/metrics_store.py` 的 `plot()` 方法

```python
def plot(self) -> None:
    self._store_request_metrics(dir_plot_path)    # 请求指标
    self._store_batch_metrics(dir_plot_path)      # Batch 指标
    self._store_completion_metrics(dir_plot_path) # 完成时间序列
    self._store_operation_metrics(dir_plot_path)  # 操作级指标
    self._store_utilization_metrics(dir_plot_path) # 利用率指标
```

## 指标详解（来自 metrics.md）

### 时间点 vs 时间段

| 指标类型 | 含义 |
|---------|------|
| Request arrival time ($a_r$) | 请求进入系统的时间点 |
| Request schedule time ($s_r$) | 请求首次被调度的时间点 |
| Request completion time ($c_r$) | 请求完成的时间点 |
| Request prefill completion time ($f_r$) | Prefill 完成、首个输出 token 产生的时间点 |
| Request execution time ($e_r$) | 请求实际在 GPU 上执行的总时间段 |
| Request preemption time ($p_r$) | 请求被分配但未执行的总时间段（抢占、流水线气泡等）|
| Request scheduling delay ($d_r$) | 请求等待调度的时间段 ($s_r - a_r$) |

### 关键指标公式

| 指标 | 计算公式 | 含义 |
|------|---------|------|
| E2E Latency | $c_r - a_r$ | 端到端延迟 |
| Scheduling Delay | $s_r - a_r$ | 调度延迟 |
| TTFT (Time to First Token) | $f_r - a_r$ | 首 token 延迟 |
| Execution + Preemption | $c_r - s_r$ | 系统内处理时间 |

### 生成的图表类型

#### 1. Request 相关 (CDF 图)

| 文件名 | 含义 |
|--------|------|
| `request_e2e_time.png` | 端到端延迟 CDF |
| `request_e2e_time_normalized.png` | 按输出 token 数归一化的延迟 CDF |
| `request_scheduling_delay.png` | 调度延迟 CDF |
| `request_execution_time.png` | 执行时间 CDF |
| `request_preemption_time.png` | 抢占时间 CDF |
| `request_num_restarts.png` | 重启次数分布（vLLM/Sarathi 特有）|

#### 2. Batch 相关 (CDF 图)

| 文件名 | 含义 |
|--------|------|
| `batch_size_{scheduler}.png` | Batch 大小分布 |
| `batch_num_tokens_{scheduler}.png` | Batch 内 token 数分布 |
| `batch_execution_time.png` | Batch 执行时间分布 |

#### 3. 时间序列图

| 文件名 | 含义 |
|--------|------|
| `request_completion_time_series_{scheduler}.png` | 请求完成数随时间变化（斜率 = QPS）|
| `request_arrival_time_series_{scheduler}.png` | 请求到达时间序列 |
| `throughput_{scheduler}.png` | 累计吞吐量（tokens）|

#### 4. Prefill/Decode 相关

| 文件名 | 含义 |
|--------|------|
| `prefill_e2e_time.png` | TTFT 分布 |
| `prefill_time_execution_plus_preemption.png` | Prefill 处理时间 |
| `decode_time_execution_plus_preemption_normalized.png` | 归一化的 Decode 时间 |

#### 5. 利用率指标 (JSON)

| 文件名 | 含义 |
|--------|------|
| `replica_1_memory_usage.json` | Replica 内存使用率 |
| `replica_1_stage_1_busy_time_percent.json` | Replica Stage 繁忙时间百分比 |
| `replica_1_stage_1_mfu.json` | Model FLOPS Utilization |

## run_experiment.py 的作用

`run_experiment.py` **只做两件事**：

1. **调用模拟器**：通过 `subprocess.run()` 执行 `python -m vidur.main ...`
2. **复制结果文件**：只复制部分 CSV 到 `results/` 目录
   - `copy_throughput_csv()`: 复制 throughput CSV
   - `copy_latency_not_normalized_csv()`: 复制 e2e_time CSV

所有 PNG 文件都是模拟器自动生成，保存在 `simulator_output/{timestamp}/plots/`。

## 配置控制

可以通过 `MetricsConfig` 控制生成哪些指标：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `write_metrics` | True | 是否写入指标 |
| `store_plots` | True | 是否生成 PNG 图表 |
| `store_request_metrics` | True | 是否记录请求指标 |
| `store_batch_metrics` | True | 是否记录 Batch 指标 |
| `store_operation_metrics` | False | 是否记录操作级指标 |
| `store_utilization_metrics` | True | 是否记录利用率指标 |
| `store_token_completion_metrics` | False | 是否记录 token 级完成指标 |

## 对于 WAIT 实验的关键指标

对于 "Mean Latency vs Arrival Rate" 实验，最重要的指标是：

1. **`request_e2e_time.csv`**: 每个请求的端到端延迟
2. **`request_completion_time_series_{scheduler}.csv`**: 请求完成时间序列（判断稳定性）
3. **`throughput_{scheduler}.csv`**: 吞吐量时间序列
4. **`batch_size_{scheduler}.csv`**: Batch 大小分布（验证 booking limit 生效）

---

**创建日期**: 2025-12-30
