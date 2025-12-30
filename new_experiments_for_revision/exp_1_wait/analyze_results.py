"""
实验 1: WAIT 算法 - 结果分析脚本

分析 Mean Latency vs Arrival Rate 数据并生成图表
"""

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# 结果目录
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")
PLOTS_DIR = os.path.join(os.path.dirname(__file__), "results", "plots")


def load_latency_data(results_dir: str = RESULTS_DIR) -> pd.DataFrame:
    """
    加载所有 latency 数据文件

    Returns:
        DataFrame with columns: arrival_rate, mean_latency, p50_latency, p99_latency
    """
    # 查找所有 latency 文件
    pattern = os.path.join(results_dir, "request_e2e_time*wait*.csv")
    files = glob.glob(pattern)

    if not files:
        print(f"未找到 latency 数据文件: {pattern}")
        return pd.DataFrame()

    results = []

    for file_path in files:
        # 从文件名提取 arrival_rate
        # 格式: request_e2e_time_wait_rate_{rate}_limit_{limit}.csv
        filename = os.path.basename(file_path)

        # 解析 rate
        if "rate_" in filename:
            rate_part = filename.split("rate_")[1]
            rate = float(rate_part.split("_")[0])
        else:
            continue

        # 读取数据
        df = pd.read_csv(file_path)

        # 计算统计量
        if "request_e2e_time" in df.columns:
            latencies = df["request_e2e_time"]
        elif len(df.columns) >= 2:
            # 假设第二列是 latency
            latencies = df.iloc[:, 1]
        else:
            continue

        mean_latency = latencies.mean()
        p50_latency = latencies.quantile(0.5)
        p99_latency = latencies.quantile(0.99)

        results.append({
            "arrival_rate": rate,
            "mean_latency": mean_latency,
            "p50_latency": p50_latency,
            "p99_latency": p99_latency,
            "num_requests": len(latencies)
        })

    if not results:
        return pd.DataFrame()

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values("arrival_rate")

    return result_df


def load_throughput_data(results_dir: str = RESULTS_DIR) -> pd.DataFrame:
    """
    加载所有 throughput 数据文件

    Returns:
        DataFrame with columns: arrival_rate, throughput
    """
    pattern = os.path.join(results_dir, "throughput*wait*.csv")
    files = glob.glob(pattern)

    if not files:
        print(f"未找到 throughput 数据文件: {pattern}")
        return pd.DataFrame()

    results = []

    for file_path in files:
        filename = os.path.basename(file_path)

        # 解析 rate
        if "rate_" in filename:
            rate_part = filename.split("rate_")[1]
            rate = float(rate_part.split("_")[0])
        else:
            continue

        # 读取数据
        df = pd.read_csv(file_path)

        # 获取 throughput
        if "throughput" in df.columns:
            throughput = df["throughput"].iloc[-1]  # 最终 throughput
        elif len(df.columns) >= 2:
            throughput = df.iloc[-1, 1]
        else:
            continue

        results.append({
            "arrival_rate": rate,
            "throughput": throughput
        })

    if not results:
        return pd.DataFrame()

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values("arrival_rate")

    return result_df


def plot_latency_vs_arrival_rate(data: pd.DataFrame, output_dir: str = PLOTS_DIR):
    """
    绘制 Mean Latency vs Arrival Rate 曲线
    """
    if data.empty:
        print("无数据可绘制")
        return

    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    # 绘制 mean latency
    ax.plot(data["arrival_rate"], data["mean_latency"],
            marker='o', linewidth=2, markersize=8, label="Mean Latency")

    # 绘制 p50 和 p99
    ax.plot(data["arrival_rate"], data["p50_latency"],
            marker='s', linewidth=1.5, markersize=6, linestyle='--', label="P50 Latency")
    ax.plot(data["arrival_rate"], data["p99_latency"],
            marker='^', linewidth=1.5, markersize=6, linestyle='--', label="P99 Latency")

    ax.set_xlabel("Arrival Rate (requests/second)", fontsize=12)
    ax.set_ylabel("Latency (seconds)", fontsize=12)
    ax.set_title("WAIT Algorithm: Latency vs Arrival Rate", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    # 保存
    output_path = os.path.join(output_dir, "latency_vs_arrival_rate.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {output_path}")

    plt.close()


def plot_throughput_vs_arrival_rate(data: pd.DataFrame, output_dir: str = PLOTS_DIR):
    """
    绘制 Throughput vs Arrival Rate 曲线
    """
    if data.empty:
        print("无数据可绘制")
        return

    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(data["arrival_rate"], data["throughput"],
            marker='o', linewidth=2, markersize=8, color='green')

    # 添加 y=x 参考线 (理想情况)
    max_rate = data["arrival_rate"].max()
    ax.plot([0, max_rate], [0, max_rate], 'k--', alpha=0.5, label="Ideal (y=x)")

    ax.set_xlabel("Arrival Rate (requests/second)", fontsize=12)
    ax.set_ylabel("Throughput (requests/second)", fontsize=12)
    ax.set_title("WAIT Algorithm: Throughput vs Arrival Rate", fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    output_path = os.path.join(output_dir, "throughput_vs_arrival_rate.png")
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"图表已保存: {output_path}")

    plt.close()


def generate_summary_table(latency_data: pd.DataFrame, throughput_data: pd.DataFrame) -> pd.DataFrame:
    """
    生成汇总表格
    """
    if latency_data.empty:
        return pd.DataFrame()

    summary = latency_data.copy()

    if not throughput_data.empty:
        summary = summary.merge(throughput_data, on="arrival_rate", how="left")

    # 判断稳定性 (简单启发式: 如果 latency > 10s 且持续增长，可能不稳定)
    # 这里需要根据实际情况调整
    summary["stable"] = summary["mean_latency"] < 10.0

    return summary


def main():
    """
    主函数：加载数据并生成分析结果
    """
    print("=" * 60)
    print("实验 1: WAIT 算法 - 结果分析")
    print("=" * 60)

    # 加载数据
    print("\n加载 latency 数据...")
    latency_data = load_latency_data()
    print(f"加载了 {len(latency_data)} 条记录")

    print("\n加载 throughput 数据...")
    throughput_data = load_throughput_data()
    print(f"加载了 {len(throughput_data)} 条记录")

    if latency_data.empty:
        print("\n未找到实验数据，请先运行 run_experiment.py")
        return

    # 生成汇总表
    print("\n生成汇总表...")
    summary = generate_summary_table(latency_data, throughput_data)
    print(summary.to_string(index=False))

    # 保存汇总表
    os.makedirs(PLOTS_DIR, exist_ok=True)
    summary_path = os.path.join(PLOTS_DIR, "summary.csv")
    summary.to_csv(summary_path, index=False)
    print(f"\n汇总表已保存: {summary_path}")

    # 绘制图表
    print("\n生成图表...")
    plot_latency_vs_arrival_rate(latency_data)
    plot_throughput_vs_arrival_rate(throughput_data)

    print("\n分析完成!")
    print("=" * 60)


if __name__ == "__main__":
    main()
