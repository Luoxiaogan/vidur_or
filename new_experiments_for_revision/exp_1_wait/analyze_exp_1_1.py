#!/usr/bin/env python3
"""
实验 1-1 分析脚本：Booking Limit (n) 参数敏感性分析

分析不同 booking limit n 对系统性能的影响，生成：
- A 类图：时间序列图（多曲线叠加）
- B 类图：对比图（横轴为 n）
- C 类图：Trade-off 图（Pareto 曲线）
- 汇总表格 summary.csv

使用方法：
    python analyze_exp_1_1.py --results_dir ./results --output_dir ./analysis
"""

import os
import re
import glob
import json
import argparse
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# =============================================================================
# 数据类定义
# =============================================================================

@dataclass
class ExperimentConfig:
    """实验参数配置（从文件夹名解析）"""
    n: int                  # booking limit
    lambda_rate: float      # arrival rate (qps)
    num_requests: int       # 请求数量
    prefill_tokens: int     # prefill token 数
    decode_tokens: int      # decode token 数
    timestamp: str          # 时间戳
    folder_path: str        # 完整路径


@dataclass
class ExperimentData:
    """单个实验的所有数据"""
    config: ExperimentConfig
    request_metrics: pd.DataFrame      # 请求级别指标
    throughput_series: pd.DataFrame    # 吞吐量时间序列
    batch_size_cdf: pd.DataFrame       # batch size CDF
    batch_tokens_cdf: pd.DataFrame     # batch tokens CDF
    memory_usage: Dict                 # 内存使用率


@dataclass
class SteadyStateMetrics:
    """稳态指标汇总"""
    n: int
    lambda_rate: float
    steady_state_throughput: float      # tokens/sec
    mean_e2e_latency: float             # seconds
    p50_e2e_latency: float
    p99_e2e_latency: float
    mean_scheduling_delay: float
    median_batch_size: float
    median_batch_tokens: float
    memory_usage_mean: float
    memory_usage_max: float
    total_time: float
    num_requests: int


# =============================================================================
# 数据加载类
# =============================================================================

class ExperimentDataLoader:
    """加载实验数据"""

    SCHEDULER_NAME = "general_nested_booking_limit"

    def __init__(self, results_dir: str):
        self.results_dir = results_dir

    def scan_experiment_folders(self) -> List[str]:
        """扫描所有实验文件夹"""
        pattern = os.path.join(self.results_dir, "n*_lambda*")
        folders = glob.glob(pattern)
        return sorted(folders)

    def parse_folder_name(self, folder_path: str) -> Optional[ExperimentConfig]:
        """解析文件夹名，提取实验参数"""
        folder_name = os.path.basename(folder_path)
        # 格式: n{X}_lambda{Y}_req{Z}_prefill{P}_decode{D}_{timestamp}
        pattern = r'n(\d+)_lambda([\d.]+)_req(\d+)_prefill(\d+)_decode(\d+)_(\d{8}_\d{6})'
        match = re.match(pattern, folder_name)
        if not match:
            print(f"警告: 无法解析文件夹名 {folder_name}")
            return None

        return ExperimentConfig(
            n=int(match.group(1)),
            lambda_rate=float(match.group(2)),
            num_requests=int(match.group(3)),
            prefill_tokens=int(match.group(4)),
            decode_tokens=int(match.group(5)),
            timestamp=match.group(6),
            folder_path=folder_path
        )

    def load_request_metrics(self, folder_path: str) -> pd.DataFrame:
        """加载请求级别指标"""
        file_path = os.path.join(
            folder_path,
            f"request_metrics_{self.SCHEDULER_NAME}.csv"
        )
        return pd.read_csv(file_path)

    def load_throughput_series(self, folder_path: str) -> pd.DataFrame:
        """加载吞吐量时间序列"""
        file_path = os.path.join(
            folder_path,
            f"throughput_{self.SCHEDULER_NAME}.csv"
        )
        return pd.read_csv(file_path)

    def load_batch_size_cdf(self, folder_path: str) -> pd.DataFrame:
        """加载 batch size CDF"""
        file_path = os.path.join(
            folder_path,
            "plots",
            f"batch_size_{self.SCHEDULER_NAME}.csv"
        )
        return pd.read_csv(file_path)

    def load_batch_tokens_cdf(self, folder_path: str) -> pd.DataFrame:
        """加载 batch tokens CDF"""
        file_path = os.path.join(
            folder_path,
            "plots",
            f"batch_num_tokens_{self.SCHEDULER_NAME}.csv"
        )
        return pd.read_csv(file_path)

    def load_memory_usage(self, folder_path: str) -> Dict:
        """加载内存使用率"""
        file_path = os.path.join(
            folder_path,
            "plots",
            "replica_1_memory_usage.json"
        )
        with open(file_path, 'r') as f:
            return json.load(f)

    def load_experiment(self, folder_path: str) -> Optional[ExperimentData]:
        """加载单个实验的所有数据"""
        config = self.parse_folder_name(folder_path)
        if config is None:
            return None

        return ExperimentData(
            config=config,
            request_metrics=self.load_request_metrics(folder_path),
            throughput_series=self.load_throughput_series(folder_path),
            batch_size_cdf=self.load_batch_size_cdf(folder_path),
            batch_tokens_cdf=self.load_batch_tokens_cdf(folder_path),
            memory_usage=self.load_memory_usage(folder_path)
        )

    def load_all_experiments(
        self,
        filter_lambda: Optional[float] = None
    ) -> Dict[int, ExperimentData]:
        """加载所有实验，按 n 值索引"""
        folders = self.scan_experiment_folders()
        experiments = {}

        for folder in folders:
            exp_data = self.load_experiment(folder)
            if exp_data is None:
                continue

            # 筛选 lambda
            if filter_lambda is not None:
                if abs(exp_data.config.lambda_rate - filter_lambda) > 0.01:
                    continue

            n = exp_data.config.n
            experiments[n] = exp_data

        return experiments


# =============================================================================
# 指标计算类
# =============================================================================

class MetricsCalculator:
    """计算派生指标"""

    def __init__(self, warmup_fraction: float = 0.1):
        self.warmup_fraction = warmup_fraction

    def compute_warmup_cutoff(self, request_metrics: pd.DataFrame) -> int:
        """计算 warm-up 截止索引"""
        total_requests = len(request_metrics)
        cutoff_index = int(total_requests * self.warmup_fraction)
        return cutoff_index

    def compute_steady_state_throughput(
        self,
        throughput_series: pd.DataFrame
    ) -> float:
        """计算稳态吞吐量 (tokens/sec)"""
        df = throughput_series.copy()
        total_time = df['Time (sec)'].max()
        warmup_time = total_time * self.warmup_fraction

        # 筛选稳态部分
        steady_df = df[df['Time (sec)'] >= warmup_time]
        if len(steady_df) < 2:
            return 0.0

        # 计算吞吐率
        start_count = steady_df.iloc[0]['throughput']
        end_count = steady_df.iloc[-1]['throughput']
        start_time = steady_df.iloc[0]['Time (sec)']
        end_time = steady_df.iloc[-1]['Time (sec)']

        if end_time <= start_time:
            return 0.0

        return (end_count - start_count) / (end_time - start_time)

    def compute_latency_stats(
        self,
        request_metrics: pd.DataFrame
    ) -> Dict[str, float]:
        """计算延迟统计量（去除 warm-up）"""
        cutoff = self.compute_warmup_cutoff(request_metrics)
        steady_df = request_metrics.iloc[cutoff:]

        return {
            'mean_e2e_latency': steady_df['request_e2e_time'].mean(),
            'p50_e2e_latency': steady_df['request_e2e_time'].quantile(0.5),
            'p99_e2e_latency': steady_df['request_e2e_time'].quantile(0.99),
            'mean_scheduling_delay': steady_df['request_scheduling_delay'].mean()
        }

    def compute_batch_stats(
        self,
        batch_size_cdf: pd.DataFrame,
        batch_tokens_cdf: pd.DataFrame
    ) -> Dict[str, float]:
        """从 CDF 计算 batch 统计量（取中位数）"""
        # 取 cdf >= 0.5 的第一个值作为中位数
        size_median_row = batch_size_cdf[batch_size_cdf['cdf'] >= 0.5].iloc[0]
        tokens_median_row = batch_tokens_cdf[batch_tokens_cdf['cdf'] >= 0.5].iloc[0]

        return {
            'median_batch_size': size_median_row['batch_size'],
            'median_batch_tokens': tokens_median_row['batch_num_tokens']
        }

    def compute_all_metrics(self, exp_data: ExperimentData) -> SteadyStateMetrics:
        """计算单个实验的所有指标"""
        config = exp_data.config

        # 稳态吞吐量
        steady_throughput = self.compute_steady_state_throughput(
            exp_data.throughput_series
        )

        # 延迟统计
        latency_stats = self.compute_latency_stats(exp_data.request_metrics)

        # Batch 统计
        batch_stats = self.compute_batch_stats(
            exp_data.batch_size_cdf,
            exp_data.batch_tokens_cdf
        )

        # 内存使用率
        memory = exp_data.memory_usage

        # 总时间
        total_time = exp_data.throughput_series['Time (sec)'].max()

        return SteadyStateMetrics(
            n=config.n,
            lambda_rate=config.lambda_rate,
            steady_state_throughput=steady_throughput,
            mean_e2e_latency=latency_stats['mean_e2e_latency'],
            p50_e2e_latency=latency_stats['p50_e2e_latency'],
            p99_e2e_latency=latency_stats['p99_e2e_latency'],
            mean_scheduling_delay=latency_stats['mean_scheduling_delay'],
            median_batch_size=batch_stats['median_batch_size'],
            median_batch_tokens=batch_stats['median_batch_tokens'],
            memory_usage_mean=memory.get('replica_1_memory_usage_weighted_mean', 0),
            memory_usage_max=memory.get('replica_1_memory_usage_max', 0),
            total_time=total_time,
            num_requests=config.num_requests
        )


# =============================================================================
# 绘图类
# =============================================================================

class PlotGenerator:
    """生成所有图表"""

    def __init__(
        self,
        output_dir: str,
        dpi: int = 150,
        figsize: Tuple[int, int] = (12, 6)
    ):
        self.output_dir = output_dir
        self.dpi = dpi
        self.figsize = figsize
        os.makedirs(output_dir, exist_ok=True)

    def _save_plot(self, fig, filename: str):
        """保存图表"""
        path = os.path.join(self.output_dir, filename)
        fig.savefig(path, dpi=self.dpi, bbox_inches='tight')
        plt.close(fig)
        print(f"  已保存: {filename}")

    # -------------------------------------------------------------------------
    # A 类图：时间序列（多曲线叠加）
    # -------------------------------------------------------------------------

    def plot_A1_throughput_time_series(
        self,
        experiments: Dict[int, ExperimentData]
    ):
        """A1: 时间 vs 平均吞吐量"""
        fig, ax = plt.subplots(figsize=self.figsize)

        for n in sorted(experiments.keys()):
            exp_data = experiments[n]
            df = exp_data.throughput_series.copy()
            # 计算瞬时吞吐量（差分）
            df['instant_throughput'] = df['throughput'].diff().fillna(0)
            df['time_diff'] = df['Time (sec)'].diff().fillna(1)
            df['rate'] = df['instant_throughput'] / df['time_diff'].replace(0, 1)
            # 滑动平均
            df['rate_smooth'] = df['rate'].rolling(window=10, min_periods=1).mean()

            ax.plot(
                df['Time (sec)'],
                df['rate_smooth'],
                label=f'n={n}',
                linewidth=1.5
            )

        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Throughput (tokens/sec)')
        ax.set_title('A1: Throughput Time Series by Booking Limit n')
        ax.legend()
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'A1_throughput_time_series.png')

    def plot_A2_cumulative_completed(
        self,
        experiments: Dict[int, ExperimentData]
    ):
        """A2: 时间 vs 累计完成请求数"""
        fig, ax = plt.subplots(figsize=self.figsize)

        for n in sorted(experiments.keys()):
            exp_data = experiments[n]
            df = exp_data.throughput_series

            ax.plot(
                df['Time (sec)'],
                df['throughput'],
                label=f'n={n}',
                linewidth=1.5
            )

        ax.set_xlabel('Time (sec)')
        ax.set_ylabel('Cumulative Completed Tokens')
        ax.set_title('A2: Cumulative Completed Tokens by Booking Limit n')
        ax.legend()
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'A2_cumulative_completed.png')

    def plot_A3_latency_time_series(
        self,
        experiments: Dict[int, ExperimentData]
    ):
        """A3: 时间 vs 平均延迟"""
        fig, ax = plt.subplots(figsize=self.figsize)

        for n in sorted(experiments.keys()):
            exp_data = experiments[n]
            df = exp_data.request_metrics.copy()

            # 按 Request Id 排序，计算累计平均延迟
            df = df.sort_values('Request Id')
            df['cumsum_latency'] = df['request_e2e_time'].cumsum()
            df['count'] = range(1, len(df) + 1)
            df['avg_latency'] = df['cumsum_latency'] / df['count']

            # 使用 Request Id 作为 x 轴（近似时间顺序）
            ax.plot(
                df['Request Id'],
                df['avg_latency'],
                label=f'n={n}',
                linewidth=1.5
            )

        ax.set_xlabel('Request ID (Time Order)')
        ax.set_ylabel('Average E2E Latency (sec)')
        ax.set_title('A3: Average Latency Over Time by Booking Limit n')
        ax.legend()
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'A3_latency_time_series.png')

    # -------------------------------------------------------------------------
    # B 类图：对比图（横轴为 n）
    # -------------------------------------------------------------------------

    def plot_B1_n_vs_throughput(self, summary_df: pd.DataFrame):
        """B1: n vs 稳态吞吐量"""
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(
            summary_df['n'],
            summary_df['steady_state_throughput'],
            marker='o',
            linewidth=2,
            markersize=8,
            color='blue'
        )

        ax.set_xlabel('Booking Limit (n)')
        ax.set_ylabel('Steady-State Throughput (tokens/sec)')
        ax.set_title('B1: Effect of Booking Limit on Throughput')
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'B1_n_vs_throughput.png')

    def plot_B2_n_vs_latency(self, summary_df: pd.DataFrame):
        """B2: n vs 平均延迟"""
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(
            summary_df['n'],
            summary_df['mean_e2e_latency'],
            marker='o',
            linewidth=2,
            markersize=8,
            color='red',
            label='Mean'
        )
        ax.plot(
            summary_df['n'],
            summary_df['p99_e2e_latency'],
            marker='s',
            linewidth=2,
            markersize=6,
            color='orange',
            linestyle='--',
            label='P99'
        )

        ax.set_xlabel('Booking Limit (n)')
        ax.set_ylabel('E2E Latency (sec)')
        ax.set_title('B2: Effect of Booking Limit on Latency')
        ax.legend()
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'B2_n_vs_latency.png')

    def plot_B3_n_vs_batch_size(self, summary_df: pd.DataFrame):
        """B3: n vs batch size"""
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(
            summary_df['n'],
            summary_df['median_batch_size'],
            marker='o',
            linewidth=2,
            markersize=8,
            color='green'
        )

        ax.set_xlabel('Booking Limit (n)')
        ax.set_ylabel('Median Batch Size')
        ax.set_title('B3: Effect of Booking Limit on Batch Size')
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'B3_n_vs_batch_size.png')

    def plot_B4_n_vs_batch_tokens(self, summary_df: pd.DataFrame):
        """B4: n vs batch tokens"""
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(
            summary_df['n'],
            summary_df['median_batch_tokens'],
            marker='o',
            linewidth=2,
            markersize=8,
            color='purple'
        )

        ax.set_xlabel('Booking Limit (n)')
        ax.set_ylabel('Median Batch Tokens')
        ax.set_title('B4: Effect of Booking Limit on Batch Token Count')
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'B4_n_vs_batch_tokens.png')

    def plot_B5_n_vs_memory(self, summary_df: pd.DataFrame):
        """B5: n vs memory usage"""
        fig, ax = plt.subplots(figsize=(10, 6))

        ax.plot(
            summary_df['n'],
            summary_df['memory_usage_mean'],
            marker='o',
            linewidth=2,
            markersize=8,
            color='brown',
            label='Mean'
        )
        ax.plot(
            summary_df['n'],
            summary_df['memory_usage_max'],
            marker='s',
            linewidth=2,
            markersize=6,
            color='darkred',
            linestyle='--',
            label='Max'
        )

        ax.set_xlabel('Booking Limit (n)')
        ax.set_ylabel('Memory Usage (%)')
        ax.set_title('B5: Effect of Booking Limit on Memory Usage')
        ax.legend()
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'B5_n_vs_memory.png')

    # -------------------------------------------------------------------------
    # C 类图：Trade-off
    # -------------------------------------------------------------------------

    def plot_C1_throughput_vs_latency(self, summary_df: pd.DataFrame):
        """C1: Throughput vs Latency (Pareto 曲线)"""
        fig, ax = plt.subplots(figsize=(10, 8))

        # 散点图
        ax.scatter(
            summary_df['steady_state_throughput'],
            summary_df['mean_e2e_latency'],
            s=100,
            c='blue',
            alpha=0.7
        )

        # 标注每个点的 n 值
        for _, row in summary_df.iterrows():
            ax.annotate(
                f"n={int(row['n'])}",
                (row['steady_state_throughput'], row['mean_e2e_latency']),
                textcoords="offset points",
                xytext=(5, 5),
                fontsize=9
            )

        # 连线（按 n 排序）
        sorted_df = summary_df.sort_values('n')
        ax.plot(
            sorted_df['steady_state_throughput'],
            sorted_df['mean_e2e_latency'],
            'b--',
            linewidth=1,
            alpha=0.5
        )

        ax.set_xlabel('Throughput (tokens/sec)')
        ax.set_ylabel('Mean E2E Latency (sec)')
        ax.set_title('C1: Throughput-Latency Trade-off')
        ax.grid(True, alpha=0.3)

        self._save_plot(fig, 'C1_throughput_vs_latency.png')

    # -------------------------------------------------------------------------
    # 绘制所有图
    # -------------------------------------------------------------------------

    def generate_all_plots(
        self,
        experiments: Dict[int, ExperimentData],
        summary_df: pd.DataFrame
    ):
        """生成所有图表"""
        print("\n生成图表...")

        # A 类图
        self.plot_A1_throughput_time_series(experiments)
        self.plot_A2_cumulative_completed(experiments)
        self.plot_A3_latency_time_series(experiments)

        # B 类图
        self.plot_B1_n_vs_throughput(summary_df)
        self.plot_B2_n_vs_latency(summary_df)
        self.plot_B3_n_vs_batch_size(summary_df)
        self.plot_B4_n_vs_batch_tokens(summary_df)
        self.plot_B5_n_vs_memory(summary_df)

        # C 类图
        self.plot_C1_throughput_vs_latency(summary_df)


# =============================================================================
# 主程序
# =============================================================================

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='分析实验 1-1: Booking Limit (n) 参数敏感性分析'
    )

    parser.add_argument(
        '--results_dir',
        type=str,
        required=True,
        help='实验结果目录（包含 n*_lambda* 文件夹）'
    )

    parser.add_argument(
        '--output_dir',
        type=str,
        default=None,
        help='输出目录（默认: {results_dir}/analysis）'
    )

    parser.add_argument(
        '--warmup_fraction',
        type=float,
        default=0.1,
        help='Warm-up 跳过比例（默认: 0.1）'
    )

    parser.add_argument(
        '--filter_lambda',
        type=float,
        default=None,
        help='筛选特定 lambda 值的实验'
    )

    parser.add_argument(
        '--dpi',
        type=int,
        default=150,
        help='图表 DPI（默认: 150）'
    )

    return parser.parse_args()


def main():
    args = parse_arguments()

    # 设置输出目录
    output_dir = args.output_dir or os.path.join(args.results_dir, 'analysis')
    os.makedirs(output_dir, exist_ok=True)

    print("=" * 60)
    print("实验 1-1 分析: Booking Limit (n) 参数敏感性")
    print("=" * 60)
    print(f"结果目录: {args.results_dir}")
    print(f"输出目录: {output_dir}")
    print(f"Warm-up 比例: {args.warmup_fraction}")
    if args.filter_lambda:
        print(f"筛选 lambda: {args.filter_lambda}")

    # 加载数据
    print("\n加载实验数据...")
    loader = ExperimentDataLoader(args.results_dir)
    experiments = loader.load_all_experiments(filter_lambda=args.filter_lambda)

    if not experiments:
        print("错误: 未找到任何实验数据")
        return

    print(f"已加载 {len(experiments)} 个实验 (n = {sorted(experiments.keys())})")

    # 计算指标
    print("\n计算稳态指标...")
    calculator = MetricsCalculator(warmup_fraction=args.warmup_fraction)
    summary_rows = []

    for n in sorted(experiments.keys()):
        exp_data = experiments[n]
        metrics = calculator.compute_all_metrics(exp_data)
        summary_rows.append({
            'n': metrics.n,
            'lambda': metrics.lambda_rate,
            'num_requests': metrics.num_requests,
            'steady_state_throughput': metrics.steady_state_throughput,
            'mean_e2e_latency': metrics.mean_e2e_latency,
            'p50_e2e_latency': metrics.p50_e2e_latency,
            'p99_e2e_latency': metrics.p99_e2e_latency,
            'mean_scheduling_delay': metrics.mean_scheduling_delay,
            'median_batch_size': metrics.median_batch_size,
            'median_batch_tokens': metrics.median_batch_tokens,
            'memory_usage_mean': metrics.memory_usage_mean,
            'memory_usage_max': metrics.memory_usage_max,
            'total_time': metrics.total_time
        })

    summary_df = pd.DataFrame(summary_rows)
    summary_df = summary_df.sort_values('n')

    # 生成图表
    plotter = PlotGenerator(output_dir=output_dir, dpi=args.dpi)
    plotter.generate_all_plots(experiments, summary_df)

    # 保存汇总表
    summary_path = os.path.join(output_dir, 'summary.csv')
    summary_df.to_csv(summary_path, index=False)
    print(f"\n汇总表已保存: {summary_path}")

    # 打印汇总
    print("\n" + "=" * 60)
    print("汇总统计")
    print("=" * 60)
    print(summary_df.to_string(index=False))
    print("=" * 60)
    print(f"\n所有图表已保存到: {output_dir}")


if __name__ == "__main__":
    main()
