"""
Time-series latency plot: e2e_time vs request arrival order.
Three baselines: Sarathi, vLLM, WCP — rate step=1.

Usage:
  python scripts/timeseries_latency.py          # run all
  python scripts/timeseries_latency.py --plot-only  # just plot from saved CSVs
  python scripts/timeseries_latency.py single   # single-type only
  python scripts/timeseries_latency.py multi    # multi-type only
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

# ======================= Experiment Definitions =======================

EXPERIMENTS = []

# --- Single-type: p512d20, rate step=1 ---
for rate in range(12, 27):  # r=12..26
    pt_single = json.dumps([
        {"type": "only", "prefill": 512, "decode": 20, "arrival_rate": rate},
    ])
    # Sarathi
    EXPERIMENTS.append({
        "label": f"ST_Sarathi_r{rate}",
        "rate": rate, "workload": "single",
        "args": [
            "--custom_request_generator_config_prompt_types", pt_single,
            "--custom_request_generator_config_max_tokens", "532",
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ],
        "gate": False,
    })
    # vLLM
    EXPERIMENTS.append({
        "label": f"ST_vLLM_r{rate}",
        "rate": rate, "workload": "single",
        "args": [
            "--custom_request_generator_config_prompt_types", pt_single,
            "--custom_request_generator_config_max_tokens", "532",
            "--replica_scheduler_config_type", "vllm",
        ],
        "gate": False,
    })
    # WCP: best single-type config = cs=256, tl=21
    EXPERIMENTS.append({
        "label": f"ST_WCP_cs256_tl21_r{rate}",
        "rate": rate, "workload": "single",
        "args": [
            "--custom_request_generator_config_prompt_types", pt_single,
            "--custom_request_generator_config_max_tokens", "532",
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt_single,
            "--general_nested_chunked_scheduler_config_total_limit", "21",
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", "256",
            "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate",
        ],
        "gate": True,
    })

# --- Multi-type W3: p512d20 + p512d50 (70/30), rate step=1 ---
for rate in range(12, 27):  # r=12..26
    pt_multi = json.dumps([
        {"type": "short", "prefill": 512, "decode": 20, "arrival_rate": round(rate * 0.7, 2)},
        {"type": "long",  "prefill": 512, "decode": 50, "arrival_rate": round(rate * 0.3, 2)},
    ])
    # Sarathi
    EXPERIMENTS.append({
        "label": f"MT_Sarathi_r{rate}",
        "rate": rate, "workload": "multi",
        "args": [
            "--custom_request_generator_config_prompt_types", pt_multi,
            "--custom_request_generator_config_max_tokens", "562",
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ],
        "gate": False,
    })
    # vLLM
    EXPERIMENTS.append({
        "label": f"MT_vLLM_r{rate}",
        "rate": rate, "workload": "multi",
        "args": [
            "--custom_request_generator_config_prompt_types", pt_multi,
            "--custom_request_generator_config_max_tokens", "562",
            "--replica_scheduler_config_type", "vllm",
        ],
        "gate": False,
    })
    # Best WCP per rate
    if rate <= 19:
        cs, tl = 192, 20
    elif rate == 20:
        cs, tl = 192, 26
    else:
        cs, tl = 128, 30
    EXPERIMENTS.append({
        "label": f"MT_WCP_cs{cs}_tl{tl}_r{rate}",
        "rate": rate, "workload": "multi",
        "args": [
            "--custom_request_generator_config_prompt_types", pt_multi,
            "--custom_request_generator_config_max_tokens", "562",
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt_multi,
            "--general_nested_chunked_scheduler_config_total_limit", str(tl),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
            "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate",
        ],
        "gate": True,
    })

# ======================= Run =======================

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
        print(f" FAIL ({result.stderr[-200:] if result.stderr else 'no stderr'})", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if not csvs:
        print(" NO CSV", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return

    shutil.copy2(csvs[0], csv_path)
    shutil.rmtree(tmpdir, ignore_errors=True)
    df = pd.read_csv(csv_path)
    print(f" done ({len(df)} reqs, mean={df['request_e2e_time'].mean():.3f}s)", flush=True)


# ======================= Plot =======================

def plot_workload(workload_tag, title_prefix, fig_name):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    exps = [e for e in EXPERIMENTS if e["workload"] == workload_tag]
    rates = sorted(set(e["rate"] for e in exps))

    fig, axes = plt.subplots(len(rates), 1, figsize=(14, 3.2 * len(rates)), squeeze=False)

    colors = {"Sarathi": "#d62728", "vLLM": "#ff7f0e", "WCP": "#1f77b4"}

    for i, rate in enumerate(rates):
        ax = axes[i, 0]

        for exp in exps:
            if exp["rate"] != rate:
                continue
            csv_path = OUTDIR / f"{exp['label']}.csv"
            if not csv_path.exists():
                continue
            df = pd.read_csv(csv_path)

            if "Sarathi" in exp["label"]:
                algo = "Sarathi"
            elif "vLLM" in exp["label"]:
                algo = "vLLM"
            else:
                algo = "WCP"
            color = colors[algo]

            window = max(50, len(df) // 100)
            rolling = df["request_e2e_time"].rolling(window=window, center=True).mean()

            ax.plot(range(len(rolling)), rolling,
                    label=f"{algo} (mean={df['request_e2e_time'].mean():.2f}s)",
                    color=color, alpha=0.8, linewidth=1.5)
            ax.scatter(range(len(df)), df["request_e2e_time"], color=color, alpha=0.02, s=1)

        ax.set_title(f"{title_prefix} rate={rate} (nreq={NREQ})", fontsize=12, fontweight="bold")
        ax.set_xlabel("Request index (arrival order)")
        ax.set_ylabel("E2E latency (s)")
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        ymax = ax.get_ylim()[1]
        if ymax > 60:
            ax.set_ylim(0, min(ymax, 80))

    plt.tight_layout()
    fig_path = OUTDIR / fig_name
    plt.savefig(fig_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Plot saved: {fig_path}")


# ======================= Summary table =======================

def print_summary(workload_tag):
    exps = [e for e in EXPERIMENTS if e["workload"] == workload_tag]
    rates = sorted(set(e["rate"] for e in exps))
    print(f"\n{'rate':>4s} | {'Sarathi':>9s} | {'vLLM':>9s} | {'WCP':>9s} | {'WCP vs Sar':>10s}")
    print("-" * 55)
    for rate in rates:
        vals = {}
        for exp in exps:
            if exp["rate"] != rate:
                continue
            csv_path = OUTDIR / f"{exp['label']}.csv"
            if not csv_path.exists():
                continue
            df = pd.read_csv(csv_path)
            if "Sarathi" in exp["label"]:
                vals["Sarathi"] = df["request_e2e_time"].mean()
            elif "vLLM" in exp["label"]:
                vals["vLLM"] = df["request_e2e_time"].mean()
            else:
                vals["WCP"] = df["request_e2e_time"].mean()
        sar = vals.get("Sarathi")
        vlm = vals.get("vLLM")
        wcp = vals.get("WCP")
        gap = f"{(wcp - sar) / sar * 100:+.1f}%" if sar and wcp else ""
        print(f"  {rate:2d} | {sar:.3f}s" if sar else f"  {rate:2d} |     -    ",
              end="")
        print(f" | {vlm:.3f}s" if vlm else " |     -    ", end="")
        print(f" | {wcp:.3f}s" if wcp else " |     -    ", end="")
        print(f" | {gap:>10s}")


if __name__ == "__main__":
    plot_only = "--plot-only" in sys.argv
    target = None
    for arg in sys.argv[1:]:
        if arg in ("single", "multi"):
            target = arg

    selected = EXPERIMENTS
    if target:
        selected = [e for e in EXPERIMENTS if e["workload"] == target]

    if not plot_only:
        print("=== Running experiments ===", flush=True)
        for exp in selected:
            run_and_save(exp)

    print("\n=== Plotting ===", flush=True)
    if not target or target == "single":
        plot_workload("single", "Single-type (p512d20)", "timeseries_single.png")
        print_summary("single")
    if not target or target == "multi":
        plot_workload("multi", "Multi-type W3 (p512d20+p512d50)", "timeseries_multi.png")
        print_summary("multi")
    print("\nDone!")
