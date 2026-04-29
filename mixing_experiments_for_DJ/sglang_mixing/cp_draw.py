"""
画图脚本：从 batch_metrics CSV 生成 4 个子图

用法:
    python cp_draw.py /path/to/exp_dir

输出:
    /path/to/exp_dir/output/fig/<exp_name>_batch_metrics.png
"""
import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def find_metrics_csv(output_dir: Path, kind: str) -> Path:
    """Find batch/request metrics CSV across coprime and non-coprime runs."""
    candidates = [
        output_dir / f"exp_two_coprime_{kind}.csv",
        output_dir / f"exp_two_non_coprime_{kind}.csv",
        output_dir / f"exp_two_not_coprime_{kind}.csv",
    ]

    for path in candidates:
        if path.exists():
            return path

    matches = sorted(output_dir.glob(f"*{kind}.csv"))
    if len(matches) == 1:
        return matches[0]

    if not matches:
        expected = ", ".join(str(p) for p in candidates)
        raise FileNotFoundError(f"No {kind} CSV found. Tried: {expected}")

    preferred = [p for p in matches if "exp_two" in p.name]
    if len(preferred) == 1:
        return preferred[0]

    names = ", ".join(str(p) for p in matches)
    raise FileNotFoundError(f"Multiple {kind} CSV files found; cannot choose automatically: {names}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python cp_draw.py /path/to/exp_dir")
        sys.exit(1)

    input_dir = Path(sys.argv[1]).resolve()
    metrics_dir = input_dir / "output"

    try:
        csv_path = find_metrics_csv(metrics_dir, "batch")
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    # 输出目录：input_dir 的父目录下的 fig/
    output_dir = input_dir / "output/fig"
    output_dir.mkdir(parents=True, exist_ok=True)

    # 文件名：使用父目录名作为前缀，如 "0424_exp.lg_batch_metrics.png"
    exp_name = input_dir.name
    output_path = output_dir / f"{exp_name}_batch_metrics.png"

    # 读取数据
    df = pd.read_csv(csv_path)
    print(f"Using batch CSV: {csv_path}")

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
    try:
        req_csv = find_metrics_csv(metrics_dir, "request")
    except FileNotFoundError:
        req_csv = None

    if req_csv is not None and req_csv.exists():
        req_df = pd.read_csv(req_csv)
        print(f"Using request CSV: {req_csv}")
        print(f"\nRequest Metrics Summary:")
        print(f"  Total requests: {len(req_df)}")
        if "retraction_count" in req_df.columns:
            print(f"  Avg retraction count: {req_df['retraction_count'].mean():.2f}")
        if "output_len" in req_df.columns:
            print(f"  Avg output length: {req_df['output_len'].mean():.1f}")


if __name__ == "__main__":
    main()
