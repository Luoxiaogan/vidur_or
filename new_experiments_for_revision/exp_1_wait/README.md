# 实验 1: WAIT 算法 - Mean Latency vs Arrival Rate

## 实验目标

绘制 **Mean Latency vs Arrival Rate** 曲线，展示 WAIT 算法在不同到达率下的稳定性表现。

## 快速开始

```bash
# 运行单个 arrival rate
python new_experiments_for_revision/exp_1_wait/run_experiment.py --rates 5 --limit 100

# 运行多个 arrival rate
python new_experiments_for_revision/exp_1_wait/run_experiment.py --rates 5 10 15 20 --limit 100

# 自定义所有参数
python new_experiments_for_revision/exp_1_wait/run_experiment.py \
    --rates 5 10 15 20 25 30 \
    --limit 100 \
    --num_requests 2000 \
    --prefill 60 \
    --decode 200
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--rates` | 5,10,15,...,50 | Arrival rate λ (qps) |
| `--limit` | 100 | Booking limit threshold n |
| `--num_requests` | 2000 | 每次实验的请求数 |
| `--prefill` | 60 | Prefill tokens |
| `--decode` | 200 | Decode tokens |
| `--output_dir` | ./results | 输出目录 |

## 输出结构

每次实验生成一个完整的结果文件夹：

```
results/
└── n100_lambda5.0_req2000_prefill60_decode200_20251230_143052/
    ├── config.json                 # 模拟配置
    ├── chrome_trace.json           # 执行轨迹
    ├── request_metrics_*.csv       # 请求级别指标
    ├── throughput_*.csv            # 吞吐量数据
    └── plots/                      # 自动生成的图表
        ├── request_e2e_time.png    # 端到端延迟 CDF
        ├── batch_size_*.png        # Batch 大小分布
        ├── request_completion_time_series_*.png  # 完成时间序列
        └── ...
```

文件夹命名格式：`n{n}_lambda{λ}_req{num}_prefill{prefill}_decode{decode}_{timestamp}`

## 实现说明

### 调度器选择

使用 `general_nested_booking_limit` 调度器 + 单一类型 `prompt_types`。

**原因**：当只有一种请求类型时，Nested WAIT 退化为 WAIT 算法，且支持通过命令行参数配置。

### 请求生成器

使用 `custom` 请求生成器，`arrival_rate` 直接作为 Poisson 过程的到达率 (qps)。

## 文件结构

```
exp_1_wait/
├── README.md              # 本文档
├── run_experiment.py      # 实验运行脚本
├── config.py              # 默认配置（已废弃，参数在 run_experiment.py 中）
├── analyze_results.py     # 结果分析脚本
├── results/               # 实验结果
└── docs/                  # 详细文档
    └── metrics_and_outputs.md  # 指标说明
```

## 相关链接

- [实验补充计划](../../docs_for_claude_code/实验补充计划.md)
- [运行模拟指南](../../docs_for_claude_code/运行模拟指南.md)
- [指标详解](./docs/metrics_and_outputs.md)

---

**最后更新**: 2025-12-30
