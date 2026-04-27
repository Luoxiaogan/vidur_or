"""
画图脚本：从 batch_metrics CSV 生成 4 个子图

用法:
    python tmp_draw.py /path/to/output_dir

输出:
    /path/to/output_dir/../fig/batch_metrics.png
"""
import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python tmp_draw.py /path/to/output_dir")
        sys.exit(1)

    input_dir = Path(sys.argv[1]).resolve()
    csv_path = input_dir / "output/exp_two_coprime_batch.csv"

    if not csv_path.exists():
        print(f"Error: {csv_path} not found")
        sys.exit(1)

    # 输出目录：input_dir 的父目录下的 fig/
    output_dir = input_dir / "output/fig"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 文件名：使用父目录名作为前缀，如 "0424_exp.lg_batch_metrics.png"
    exp_name = input_dir.name
    output_path = output_dir / f"{exp_name}_batch_metrics.png"

    # 读取数据
    df = pd.read_csv(csv_path)

    # 过滤 dummy 数据 (batch_id < 12)
    df = df[df["batch_id"] >= 12].copy()
    df["batch_index"] = range(len(df))

    print(f"Loaded {len(df)} batches (after filtering)")

    # 创建 2x2 子图
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"Batch Metrics: {input_dir.parent.name}", fontsize=16, fontweight='bold')

    x = df["batch_index"]

    # 子图 1: Token Usage (%)
    ax1 = axes[0, 0]
    ax1.plot(x, df["token_usage"] * 100, color='blue', linewidth=0.8)
    ax1.set_xlabel("Batch Index")
    ax1.set_ylabel("Token Usage (%)")
    ax1.set_title("GPU KV Cache Token Usage")
    ax1.set_ylim(0, 105)
    ax1.grid(True, alpha=0.3)

    # 子图 2: Queue Requests
    ax2 = axes[0, 1]
    ax2.plot(x, df["num_queue_reqs"], color='green', linewidth=0.8, label='num_queue_reqs')
    if "num_total_queue_reqs" in df.columns:
        ax2.plot(x, df["num_total_queue_reqs"], color='red', linewidth=0.8,
                 label='num_total_queue_reqs', linestyle='--')
    ax2.set_xlabel("Batch Index")
    ax2.set_ylabel("Queue Requests")
    ax2.set_title("Queue Length")
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # 子图 3: Retracted Requests
    ax3 = axes[1, 0]
    ax3.plot(x, df["num_retracted_reqs"], color='orange', linewidth=0.8)
    ax3.set_xlabel("Batch Index")
    ax3.set_ylabel("num_retracted_reqs")
    ax3.set_title("Retracted Requests (per batch)")
    ax3.grid(True, alpha=0.3)

    # 子图 4: New Sequences
    ax4 = axes[1, 1]
    ax4.plot(x, df["num_new_seqs"], color='purple', linewidth=0.8)
    ax4.set_xlabel("Batch Index")
    ax4.set_ylabel("num_new_seqs")
    ax4.set_title("New Sequences (per batch)")
    ax4.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"Saved to: {output_path}")

    # 可选：读取 request_metrics 并打印统计
    req_csv = input_dir / "output/exp_two_coprime_request.csv"
    if req_csv.exists():
        req_df = pd.read_csv(req_csv)
        print(f"\nRequest Metrics Summary:")
        print(f"  Total requests: {len(req_df)}")
        if "retraction_count" in req_df.columns:
            print(f"  Avg retraction count: {req_df['retraction_count'].mean():.2f}")
        if "output_len" in req_df.columns:
            print(f"  Avg output length: {req_df['output_len'].mean():.1f}")


if __name__ == "__main__":
    main()
