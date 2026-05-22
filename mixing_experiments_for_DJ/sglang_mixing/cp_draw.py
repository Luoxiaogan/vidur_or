"""
画图脚本：从 batch_metrics CSV 生成 batch_metrics 和 pre_decode 对比图

用法:
    python cp_draw.py /path/to/exp_dir

输出:
    /path/to/exp_dir/output/fig/<exp_name>_batch_metrics.png
"""
import sys
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from glob import glob


def find_metrics_csv(output_dir: Path, kind: str) -> Path:
    """Find batch/request metrics CSV across coprime and non-coprime runs."""
    candidates = [
        output_dir / f"exp_two_coprime_{kind}.csv",
        output_dir / f"exp_two_non_coprime_{kind}.csv",
        output_dir / f"exp_two_not_coprime_{kind}.csv",
        output_dir / f"{kind}_metrics.csv",
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


def expand_input_dirs(args):
    input_dirs = []
    for arg in args:
        matches = sorted(glob(arg))
        if not matches:
            matches = [arg]
        input_dirs.extend(Path(match).resolve() for match in matches)
    return input_dirs


def plot_pre_decode_comparison(df: pd.DataFrame, output_dir: Path, exp_name: str):
    comparison_specs = [
        (
            "batch_size",
            "pre_decode_batch_size",
            "Batch Size",
            lambda series: series,
            None,
        ),
        (
            "batch_num_tokens",
            "pre_decode_batch_num_tokens",
            "Batch Tokens",
            lambda series: series,
            None,
        ),
        (
            "batch_num_tokens",
            "pre_decode_batch_num_tokens_after_one_decode",
            "Batch Tokens",
            lambda series: series,
            None,
        ),
        (
            "num_tokens",
            "pre_decode_num_tokens",
            "KV Tokens",
            lambda series: series,
            None,
        ),
        (
            "token_usage",
            "pre_decode_token_usage",
            "Token Usage (%)",
            lambda series: series * 100,
            (0, 105),
        ),
    ]

    available_specs = [
        spec for spec in comparison_specs if spec[0] in df.columns and spec[1] in df.columns
    ]
    if not available_specs:
        print("No pre_decode_* columns found; skip pre-decode comparison plot")
        return

    x = df["batch_index"]
    fig, axes = plt.subplots(
        len(available_specs), 3, figsize=(22, 3.0 * len(available_specs))
    )
    if len(available_specs) == 1:
        axes = [axes]

    fig.suptitle(
        f"Pre-decode Comparison: {exp_name}", fontsize=16, fontweight="bold"
    )

    for row_idx, (old_col, new_col, ylabel, transform, fixed_ylim) in enumerate(
        available_specs
    ):
        left_ax = axes[row_idx][0]
        right_ax = axes[row_idx][1]
        compare_ax = axes[row_idx][2]
        old_values = transform(df[old_col])
        new_values = transform(df[new_col])

        left_ax.plot(x, old_values, color="steelblue", linewidth=0.8)
        left_ax.set_title(old_col)
        left_ax.set_xlabel("Batch Index")
        left_ax.set_ylabel(ylabel)
        left_ax.grid(True, alpha=0.3)

        right_ax.plot(x, new_values, color="darkorange", linewidth=0.8, label=new_col)
        if (
            new_col == "pre_decode_batch_size"
            and "num_prev_completed_reqs" in df.columns
            and "num_new_seqs" in df.columns
        ):
            right_ax.plot(
                x,
                df["num_prev_completed_reqs"],
                color="brown",
                linewidth=0.8,
                linestyle="--",
                label="num_prev_completed_reqs",
            )
            right_ax.plot(
                x,
                df["num_new_seqs"],
                color="purple",
                linewidth=0.8,
                linestyle=":",
                label="num_new_seqs",
            )
            right_ax.legend()
        right_ax.set_title(new_col)
        right_ax.set_xlabel("Batch Index")
        right_ax.set_ylabel(ylabel)
        right_ax.grid(True, alpha=0.3)

        compare_ax.plot(
            x, old_values, color="steelblue", linewidth=0.8, label=old_col
        )
        compare_ax.plot(
            x, new_values, color="darkorange", linewidth=0.8, label=new_col
        )
        compare_ax.set_title(f"{old_col} vs {new_col}")
        compare_ax.set_xlabel("Batch Index")
        compare_ax.set_ylabel(ylabel)
        compare_ax.legend()
        compare_ax.grid(True, alpha=0.3)

        if fixed_ylim is not None:
            left_ax.set_ylim(*fixed_ylim)
            right_ax.set_ylim(*fixed_ylim)
            compare_ax.set_ylim(*fixed_ylim)
        else:
            y_min = min(old_values.min(), new_values.min())
            y_max = max(old_values.max(), new_values.max())
            if y_min == y_max:
                pad = max(abs(y_min) * 0.05, 1)
            else:
                pad = (y_max - y_min) * 0.05
            left_ax.set_ylim(y_min - pad, y_max + pad)
            if new_col == "pre_decode_batch_size":
                right_ax.set_ylim(bottom=0)
            else:
                right_ax.set_ylim(y_min - pad, y_max + pad)
            compare_ax.set_ylim(y_min - pad, y_max + pad)

    output_path = output_dir / f"{exp_name}_pre_decode_comparison.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved pre-decode comparison to: {output_path}")


def _classify_case(row):
    """Map a decode row to Case 1/2/3/0 (no retract)."""
    nr = row["num_retracted_reqs"]
    if nr == 0:
        return 0
    ra, rr, kn = row["real_admission"], row["real_retraction"], row["retracted_K_new"]
    if ra > 0 and rr == 0:
        return 1
    if ra == 0 and rr > 0 and kn > 0:
        return 2
    if ra == 0 and rr > 0 and kn == 0:
        return 3
    return -1  # unexpected combination


def plot_retraction_breakdown(df: pd.DataFrame, output_dir: Path, exp_name: str):
    """Decompose retraction into regulator (K_new) vs real, plus real_admission and case mix."""
    required = {"real_admission", "real_retraction", "retracted_K_new", "num_retracted_reqs"}
    if not required.issubset(df.columns):
        print("real_admission/real_retraction/retracted_K_new not in CSV; skip breakdown plot")
        return

    df = df.copy()
    df["case"] = df.apply(_classify_case, axis=1)
    x = df["batch_index"]

    counts = df["case"].value_counts().reindex([0, 1, 2, 3, -1], fill_value=0)
    identity_violations = int(
        (df["num_retracted_reqs"] != df["retracted_K_new"] + df["real_retraction"]).sum()
    )

    fig, axes = plt.subplots(2, 2, figsize=(20, 9))
    fig.suptitle(
        f"Retraction Breakdown: {exp_name} "
        f"(case counts: C1={counts[1]}, C2={counts[2]}, C3={counts[3]}, "
        f"no-retract={counts[0]}, bad={counts[-1]}; identity violations={identity_violations})",
        fontsize=14,
        fontweight="bold",
    )

    # (0,0) Stacked: K_new (regulator) below, real_retraction (real) on top
    ax = axes[0, 0]
    ax.stackplot(
        x,
        df["retracted_K_new"],
        df["real_retraction"],
        labels=["retracted_K_new (regulator, fresh)", "real_retraction (already-decoded)"],
        colors=["#9ecae1", "#e6550d"],
        alpha=0.85,
    )
    ax.plot(x, df["num_retracted_reqs"], color="black", linewidth=0.6, label="num_retracted_reqs")
    ax.set_xlabel("Batch Index")
    ax.set_ylabel("Retracted reqs")
    ax.set_title("Retraction decomposition: regulator vs real")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    # (0,1) real_admission over time
    ax = axes[0, 1]
    ax.plot(x, df["real_admission"], color="#2ca02c", linewidth=0.8, label="real_admission")
    if "num_new_seqs" in df.columns:
        ax.plot(
            x, df["num_new_seqs"], color="purple", linewidth=0.6,
            linestyle=":", label="num_new_seqs (next prebuilt)",
        )
    ax.set_xlabel("Batch Index")
    ax.set_ylabel("Requests")
    ax.set_title("real_admission (fresh reqs surviving this iter)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    # (1,0) Case category scatter
    ax = axes[1, 0]
    case_color = {0: "#bbbbbb", 1: "#1f77b4", 2: "#ff7f0e", 3: "#d62728", -1: "magenta"}
    case_label = {0: "no-retract", 1: "C1 regulator", 2: "C2 underflow", 3: "C3 pure pressure", -1: "bad"}
    for c, color in case_color.items():
        mask = df["case"] == c
        if mask.any():
            ax.scatter(
                df.loc[mask, "batch_index"], [c] * mask.sum(),
                s=18, color=color, label=f"{case_label[c]} ({int(mask.sum())})",
            )
    ax.set_yticks([0, 1, 2, 3])
    ax.set_yticklabels(["no-retract", "C1", "C2", "C3"])
    ax.set_xlabel("Batch Index")
    ax.set_ylabel("Case")
    ax.set_title("Per-iter classification along the run")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(True, alpha=0.3)

    # (1,1) Histogram of case counts
    ax = axes[1, 1]
    cats = ["no-retract", "C1", "C2", "C3"]
    vals = [counts[0], counts[1], counts[2], counts[3]]
    colors = ["#bbbbbb", "#1f77b4", "#ff7f0e", "#d62728"]
    bars = ax.bar(cats, vals, color=colors)
    for bar, v in zip(bars, vals):
        ax.text(
            bar.get_x() + bar.get_width() / 2, bar.get_height(),
            str(int(v)), ha="center", va="bottom", fontsize=10,
        )
    ax.set_ylabel("Decode rows")
    ax.set_title("Case mix")
    ax.grid(True, alpha=0.3, axis="y")

    output_path = output_dir / f"{exp_name}_retraction_breakdown.png"
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved retraction breakdown to: {output_path}")


def process_experiment(input_dir: Path):
    metrics_dir = input_dir / "output"

    try:
        csv_path = find_metrics_csv(metrics_dir, "batch")
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return False

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
    if "num_prev_completed_reqs" in df.columns:
        print(
            "  Completion/admission summary: "
            f"prev_completed_sum={df['num_prev_completed_reqs'].sum():.0f}, "
            f"new_seqs_sum={df['num_new_seqs'].sum():.0f}, "
            f"max_prev_completed={df['num_prev_completed_reqs'].max():.0f}, "
            f"max_new_seqs={df['num_new_seqs'].max():.0f}"
        )
    else:
        print("  num_prev_completed_reqs not found; plotting num_new_seqs only")

    # 创建 2x3 子图：前两列保留原始布局，第三列用于 completion/admission。
    fig, axes = plt.subplots(2, 3, figsize=(21, 10))
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

    # 子图 5: Previous Completions vs New Sequences
    ax5 = axes[0, 2]
    ax5.plot(x, df["num_new_seqs"], color='purple', linewidth=0.8,
             label='num_new_seqs')
    if "num_prev_completed_reqs" in df.columns:
        ax5.plot(x, df["num_prev_completed_reqs"], color='brown', linewidth=0.8,
                 label='num_prev_completed_reqs', linestyle='--')
    ax5.set_xlabel("Batch Index")
    ax5.set_ylabel("Requests")
    ax5.set_title("Previous Completions vs New Sequences")
    ax5.legend()
    ax5.grid(True, alpha=0.3)

    # 子图 6: Batch Size with Completions
    ax6 = axes[1, 2]
    ax6.plot(x, df["batch_size"], color='steelblue', linewidth=0.8,
             label='batch_size')
    if "pre_decode_batch_size" in df.columns:
        ax6.plot(x, df["pre_decode_batch_size"], color='darkorange',
                 linewidth=0.8, label='pre_decode_batch_size', linestyle='-.')
    if "num_prev_completed_reqs" in df.columns:
        ax6.plot(x, df["num_prev_completed_reqs"], color='brown', linewidth=0.8,
                 label='num_prev_completed_reqs', linestyle='--')
    ax6.set_xlabel("Batch Index")
    ax6.set_ylabel("Requests")
    ax6.set_title("Batch Size and Previous Completions")
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    print(f"Saved to: {output_path}")

    plot_pre_decode_comparison(df, output_dir, exp_name)
    plot_retraction_breakdown(df, output_dir, exp_name)

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
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python cp_draw.py /path/to/exp_dir [/path/to/exp_dir ...]")
        sys.exit(1)

    input_dirs = expand_input_dirs(sys.argv[1:])
    failed = 0
    for input_dir in input_dirs:
        print(f"\n=== Processing {input_dir} ===")
        if not process_experiment(input_dir):
            failed += 1

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
