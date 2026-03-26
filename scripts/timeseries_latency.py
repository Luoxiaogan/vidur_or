"""
Time-series latency plot: e2e_time vs request arrival order.
Rerun key configs at critical rates with nreq=10000, save full CSV, plot.

Usage:
  python scripts/timeseries_latency.py          # run all
  python scripts/timeseries_latency.py --plot-only  # just plot from saved CSVs
"""
import subprocess, json, pandas as pd, os, shutil, glob, sys, tempfile
from pathlib import Path

PROJECT = "/persistent/vidur_or"
OUTDIR = Path(PROJECT) / "outputs" / "timeseries"
OUTDIR.mkdir(parents=True, exist_ok=True)

COMMON = [
    "python", "-m", "vidur.main",
    "--replica_config_device", "a100",
    "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
    "--replica_config_memory_margin_fraction", "0.1",
    "--cluster_config_num_replicas", "1",
    "--replica_config_tensor_parallel_size", "1",
    "--replica_config_num_pipeline_stages", "1",
    "--request_generator_config_type", "custom",
    "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
    "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
    "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
    "--no-metrics_config_store_plots",
]

NREQ = 10000

# W3 workload
def make_w3_pt(rate):
    return json.dumps([
        {"type": "short", "prefill": 512, "decode": 20, "arrival_rate": round(rate * 0.7, 2)},
        {"type": "long",  "prefill": 512, "decode": 50, "arrival_rate": round(rate * 0.3, 2)},
    ])

# Experiments: (label, rate, scheduler_args, gate)
EXPERIMENTS = []

for rate in [16, 20, 21, 22, 23, 24]:
    pt = make_w3_pt(rate)
    # Sarathi baseline
    EXPERIMENTS.append({
        "label": f"Sarathi_r{rate}",
        "rate": rate,
        "args": [
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", "562",
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ],
        "gate": False,
    })
    # Best WCP config per rate
    if rate <= 19:
        cs, tl = 192, 20
    elif rate == 20:
        cs, tl = 192, 26
    else:
        cs, tl = 128, 30
    EXPERIMENTS.append({
        "label": f"WCP_cs{cs}_tl{tl}_r{rate}",
        "rate": rate,
        "args": [
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", "562",
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", str(tl),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
            "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate",
        ],
        "gate": True,
    })


def run_and_save(exp):
    csv_path = OUTDIR / f"{exp['label']}.csv"
    if csv_path.exists():
        print(f"  {exp['label']}: cached", flush=True)
        return

    tmpdir = tempfile.mkdtemp(prefix="vidur_ts_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on" if exp["gate"] else "off"
    cmd = COMMON + [
        "--custom_request_generator_config_num_requests", str(NREQ),
        "--metrics_config_output_dir", tmpdir,
    ] + exp["args"]

    print(f"  {exp['label']}: running...", end="", flush=True)
    result = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=3600, env=env, text=True)

    if result.returncode != 0:
        print(" FAIL", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if not csvs:
        print(" NO CSV", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    # Copy CSV to output dir
    shutil.copy2(csvs[0], csv_path)
    shutil.rmtree(tmpdir, ignore_errors=True)
    df = pd.read_csv(csv_path)
    print(f" done ({len(df)} requests, mean={df['request_e2e_time'].mean():.3f}s)", flush=True)


def plot_timeseries():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rates = sorted(set(e["rate"] for e in EXPERIMENTS))
    fig, axes = plt.subplots(len(rates), 1, figsize=(14, 4 * len(rates)), squeeze=False)

    for i, rate in enumerate(rates):
        ax = axes[i, 0]

        for exp in EXPERIMENTS:
            if exp["rate"] != rate:
                continue
            csv_path = OUTDIR / f"{exp['label']}.csv"
            if not csv_path.exists():
                continue
            df = pd.read_csv(csv_path)

            # Use request index as x-axis (arrival order)
            algo = "Sarathi" if "Sarathi" in exp["label"] else "WCP"
            color = "#d62728" if algo == "Sarathi" else "#1f77b4"

            # Rolling average for smoothness
            window = max(50, len(df) // 100)
            rolling = df["request_e2e_time"].rolling(window=window, center=True).mean()

            ax.plot(range(len(rolling)), rolling, label=f"{algo} (mean={df['request_e2e_time'].mean():.2f}s)",
                    color=color, alpha=0.8, linewidth=1.5)
            # Light raw data
            ax.scatter(range(len(df)), df["request_e2e_time"], color=color, alpha=0.03, s=1)

        ax.set_title(f"W3 rate={rate} (nreq={NREQ})", fontsize=13, fontweight="bold")
        ax.set_xlabel("Request index (arrival order)")
        ax.set_ylabel("E2E latency (s)")
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        # Don't let unstable runs dominate y-axis too much
        ymax = ax.get_ylim()[1]
        if ymax > 50:
            ax.set_ylim(0, min(ymax, 80))

    plt.tight_layout()
    fig_path = OUTDIR / "timeseries_latency.png"
    plt.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"\nPlot saved: {fig_path}")


if __name__ == "__main__":
    plot_only = "--plot-only" in sys.argv

    if not plot_only:
        print("=== Running experiments ===", flush=True)
        for exp in EXPERIMENTS:
            run_and_save(exp)

    print("\n=== Plotting ===", flush=True)
    plot_timeseries()
    print("Done!")
