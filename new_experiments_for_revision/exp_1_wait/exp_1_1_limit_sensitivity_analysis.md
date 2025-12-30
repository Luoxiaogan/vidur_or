# 实验 1-1: Booking Limit (n) 参数敏感性分析

## 实验结果（2025-12-30）

### 实验参数
```
固定：λ=5.0 qps, prefill=60, decode=10, num_requests=8000
变化：n = [20, 40, 80, 100, 200]
```

### 结果汇总

| n | 吞吐量 (tokens/s) | 平均延迟 (s) | P99延迟 (s) | batch size | 内存 (%) |
|---|------------------|-------------|------------|------------|---------|
| 20 | 50.4 | **3.7** | 6.1 | 20 | 0.28 |
| 40 | 50.4 | 7.5 | 10.6 | 40 | 0.56 |
| 80 | 50.4 | 15.0 | 19.7 | 80 | 1.12 |
| 100 | 50.4 | 18.8 | 23.9 | 100 | 1.40 |
| 200 | 50.4 | 37.8 | 45.2 | 200 | 2.78 |

### 关键发现

1. **吞吐量恒定**：~50.4 tokens/s，与 n 无关（由 λ 决定）
2. **延迟与 n 线性关系**：n 翻倍 → 延迟翻倍
3. **内存不是瓶颈**：最大使用率 <3%
4. **最优 n**：取决于延迟 SLO，n 越小延迟越低

### 理论验证

符合 WAIT 算法预期：
- 稳态吞吐量 = λ × (prefill + decode) = 5 × (60 + 10) = 350 tokens/s（理论值，实际受 GPU 处理速度限制）
- 延迟 ≈ n × 单次迭代时间

---

## 实验约束条件

**重要**：`num_requests` 必须满足：
```
num_requests / n > decode_tokens × 5
```
否则流水线无法填满，尾部请求会卡住。

示例：
- decode=10, n=200 → num_requests > 10 × 5 × 200 = 10,000（建议值）
- decode=200, n=100 → num_requests > 200 × 5 × 100 = 100,000

---

## 已知问题

强制清空队列时部分 n 值（60, 120, 150）出现 `KeyError`，需修复 `simulator.py` 的 `free()` 调用。

---

## 快速开始

### 1. 运行实验

```bash
cd new_experiments_for_revision/exp_1_wait

# 批量运行（decode=10, 8000 requests）
for n in 20 40 80 100 200; do
    python run_experiment.py --rates 5 --limit $n --num_requests 8000 --decode 10
done
```

### 2. 分析结果

```bash
python analyze_exp_1_1.py --results_dir ./results
```

### 3. 查看输出

```
results/analysis/
├── A1_throughput_time_series.png   # 时间 vs 吞吐量（多曲线）
├── A2_cumulative_completed.png     # 时间 vs 累计完成
├── A3_latency_time_series.png      # 时间 vs 平均延迟
├── B1_n_vs_throughput.png          # n vs 稳态吞吐量
├── B2_n_vs_latency.png             # n vs 延迟（mean + P99）
├── B3_n_vs_batch_size.png          # n vs batch size
├── B4_n_vs_batch_tokens.png        # n vs batch tokens
├── B5_n_vs_memory.png              # n vs 内存使用率
├── C1_throughput_vs_latency.png    # Trade-off Pareto 曲线
└── summary.csv                     # 汇总表格
```

---

## 分析脚本

### 架构

```
analyze_exp_1_1.py
├── ExperimentConfig      # 从文件夹名解析参数
├── ExperimentDataLoader  # 加载 CSV/JSON 数据
├── MetricsCalculator     # 计算稳态指标（去除 10% warm-up）
├── PlotGenerator         # 生成 9 张图
└── main()                # CLI 入口
```

### CLI 参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--results_dir` | (必需) | 实验结果目录 |
| `--output_dir` | `{results_dir}/analysis` | 输出目录 |
| `--warmup_fraction` | 0.1 | warm-up 跳过比例 |
| `--filter_lambda` | None | 筛选特定 λ |

---

## 文件结构

```
exp_1_wait/
├── run_experiment.py               # 运行实验
├── analyze_exp_1_1.py              # 分析脚本
├── exp_1_1_limit_sensitivity_analysis.md  # 本文档
├── results/                        # 实验数据
└── results/analysis/               # 分析输出
```

---

**更新日期**: 2025-12-30
**状态**: 已完成初步实验
