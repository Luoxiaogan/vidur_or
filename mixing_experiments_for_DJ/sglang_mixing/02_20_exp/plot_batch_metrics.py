"""
Batch Metrics Visualization Script

绘制两个实验的 batch metrics 对比图：
- exp_single: 单类型请求实验
- exp_two: 两类型请求实验

每个实验一个大图，包含 4 个子图：
1. gpu_num_reqs
2. num_queue_reqs + num_total_queue_reqs
3. num_retracted_reqs
4. num_new_seqs
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# 配置
BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR

# 实验配置
EXPERIMENTS = {
    "exp_single": {
        "csv_path": BASE_DIR / "exp_single" / "batch_metrics_mix.csv",
        "start_batch_id": 12,  # dummy 之后的起始 batch_id
        "title": "Single Type Experiment",
        "output_name": "batch_metrics_exp_single.png",
    },
    "exp_two": {
        "csv_path": BASE_DIR / "exp_two" / "batch_metrics_mix.csv",
        "start_batch_id": 12,  # dummy 之后的起始 batch_id
        "title": "Two Types Experiment",
        "output_name": "batch_metrics_exp_two.png",
    },
}


def load_and_filter_data(csv_path: Path, start_batch_id: int) -> pd.DataFrame:
    """加载 CSV 并过滤 dummy 数据"""
    df = pd.read_csv(csv_path)
    # 过滤：只保留 batch_id >= start_batch_id
    df = df[df["batch_id"] >= start_batch_id].copy()
    # 重置 batch index（从 0 开始）
    df["batch_index"] = range(len(df))
    return df


def plot_experiment(exp_name: str, config: dict):
    """绘制单个实验的图"""

    print(f"Processing {exp_name}...")

    # 加载数据
    df = load_and_filter_data(config["csv_path"], config["start_batch_id"])
    print(f"  Loaded {len(df)} batches (after filtering)")

    # 创建图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(config["title"], fontsize=16, fontweight='bold')

    x = df["batch_index"]

    # 子图 1: token_usage (百分比)
    ax1 = axes[0, 0]
    ax1.plot(x, df["token_usage"] * 100, color='blue', linewidth=0.8)
    ax1.set_xlabel("Batch Index")
    ax1.set_ylabel("Token Usage (%)")
    ax1.set_title("Token Usage (%)")
    ax1.set_ylim(0, 105)  # 0-100% 范围
    ax1.grid(True, alpha=0.3)

    # 子图 2: num_queue_reqs + num_total_queue_reqs
    ax2 = axes[0, 1]
    ax2.plot(x, df["num_queue_reqs"], color='green', linewidth=0.8, label='num_queue_reqs')
    ax2.plot(x, df["num_total_queue_reqs"], color='red', linewidth=0.8, label='num_total_queue_reqs', linestyle='--')
    ax2.set_xlabel("Batch Index")
    ax2.set_ylabel("Queue Requests")
    ax2.set_title("Queue Requests (with/without retracted)")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图 3: num_retracted_reqs
    ax3 = axes[1, 0]
    ax3.plot(x, df["num_retracted_reqs"], color='orange', linewidth=0.8)
    ax3.set_xlabel("Batch Index")
    ax3.set_ylabel("num_retracted_reqs")
    ax3.set_title("Number of Retracted Requests (per batch)")
    ax3.grid(True, alpha=0.3)

    # 子图 4: num_new_seqs
    ax4 = axes[1, 1]
    ax4.plot(x, df["num_new_seqs"], color='purple', linewidth=0.8)
    ax4.set_xlabel("Batch Index")
    ax4.set_ylabel("num_new_seqs")
    ax4.set_title("Number of New Sequences (per batch)")
    ax4.grid(True, alpha=0.3)

    # 调整布局
    plt.tight_layout()

    # 保存
    output_path = OUTPUT_DIR / config["output_name"]
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"  Saved to: {output_path}")

    plt.close()


def main():
    print("=" * 60)
    print("Batch Metrics Visualization")
    print("=" * 60)

    for exp_name, config in EXPERIMENTS.items():
        plot_experiment(exp_name, config)

    print("\nDone!")


if __name__ == "__main__":
    main()
