"""
Re-run Single-type (p512d20) experiments from 2026_03_23_wait_cp_all_rates_win.md

Config:
- Workload: p512d20 (prefill=512, decode=20)
- Rates: 12, 14, 16, 18, 20, 22, 24
- nreq: 5000
- WCP: tl=21, cs=256, gate=ON
- Sarathi: cs=512, batch_size_cap=512
- vLLM: default

Output: Saved to /home/CPU/vidur_or/luogan_wait_verification/single/
"""

import subprocess
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# Configuration
PROJECT_ROOT = "/home/CPU/vidur_or"
OUTPUT_DIR = Path("/home/CPU/vidur_or/luogan_wait_verification/single")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Experiment parameters
PREFILL_TOKENS = 512
DECODE_TOKENS = 20
MAX_TOKENS = PREFILL_TOKENS + DECODE_TOKENS  # 532
NREQ = 5000
RATES = [12, 14, 16, 18, 20, 22, 24]

# Common args for all experiments
COMMON_ARGS = [
    "python", "-m", "vidur.main",
    "--replica_config_device", "a100",
    "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
    "--replica_config_memory_margin_fraction", "0.1",
    "--cluster_config_num_replicas", "1",
    "--replica_config_tensor_parallel_size", "1",
    "--replica_config_num_pipeline_stages", "1",
    "--request_generator_config_type", "custom",
    "--custom_request_generator_config_max_tokens", str(MAX_TOKENS),
    "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
    "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
    "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
    "--no-metrics_config_store_plots",  # Don't generate plots, just CSV
]


def build_prompt_types(arrival_rate):
    """Build prompt types for single-type workload."""
    return json.dumps([{
        "type": "only",
        "prefill": PREFILL_TOKENS,
        "decode": DECODE_TOKENS,
        "arrival_rate": arrival_rate
    }])


def run_wcp(rate, output_subdir):
    """Run WCP scheduler experiment."""
    pt = build_prompt_types(rate)
    exp_name = f"WCP_cs256_tl21_r{rate}"
    exp_dir = output_subdir / exp_name
    exp_dir.mkdir(parents=True, exist_ok=True)

    args = COMMON_ARGS + [
        "--custom_request_generator_config_prompt_types", pt,
        "--custom_request_generator_config_num_requests", str(NREQ),
        "--replica_scheduler_config_type", "general_nested_chunked",
        "--general_nested_chunked_scheduler_config_prompt_types", pt,
        "--general_nested_chunked_scheduler_config_total_limit", "21",
        "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
        "--general_nested_chunked_scheduler_config_chunk_size", "256",
        "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
        "--general_nested_chunked_scheduler_config_force_clear",
        "--no-general_nested_chunked_scheduler_config_wait_gate",
        "--metrics_config_output_dir", str(exp_dir),
    ]

    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on"

    print(f"  [WCP r={rate}] Running...", flush=True)
    result = subprocess.run(args, capture_output=True, cwd=PROJECT_ROOT, env=env, text=True)

    if result.returncode != 0:
        print(f"  [WCP r={rate}] FAIL: {result.stderr[-200:] if result.stderr else 'unknown error'}")
        return None

    print(f"  [WCP r={rate}] Done -> {exp_dir}")
    return exp_dir


def run_sarathi(rate, output_subdir):
    """Run Sarathi scheduler experiment."""
    pt = build_prompt_types(rate)
    exp_name = f"Sarathi_cs512_r{rate}"
    exp_dir = output_subdir / exp_name
    exp_dir.mkdir(parents=True, exist_ok=True)

    args = COMMON_ARGS + [
        "--custom_request_generator_config_prompt_types", pt,
        "--custom_request_generator_config_num_requests", str(NREQ),
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--sarathi_scheduler_config_batch_size_cap", "512",
        "--metrics_config_output_dir", str(exp_dir),
    ]

    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "off"  # Not used for Sarathi, but set for consistency

    print(f"  [Sarathi r={rate}] Running...", flush=True)
    result = subprocess.run(args, capture_output=True, cwd=PROJECT_ROOT, env=env, text=True)

    if result.returncode != 0:
        print(f"  [Sarathi r={rate}] FAIL: {result.stderr[-200:] if result.stderr else 'unknown error'}")
        return None

    print(f"  [Sarathi r={rate}] Done -> {exp_dir}")
    return exp_dir


def run_vllm(rate, output_subdir):
    """Run vLLM scheduler experiment."""
    pt = build_prompt_types(rate)
    exp_name = f"vLLM_r{rate}"
    exp_dir = output_subdir / exp_name
    exp_dir.mkdir(parents=True, exist_ok=True)

    args = COMMON_ARGS + [
        "--custom_request_generator_config_prompt_types", pt,
        "--custom_request_generator_config_num_requests", str(NREQ),
        "--replica_scheduler_config_type", "vllm",
        "--metrics_config_output_dir", str(exp_dir),
    ]

    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "off"  # Not used for vLLM

    print(f"  [vLLM r={rate}] Running...", flush=True)
    result = subprocess.run(args, capture_output=True, cwd=PROJECT_ROOT, env=env, text=True)

    if result.returncode != 0:
        print(f"  [vLLM r={rate}] FAIL: {result.stderr[-200:] if result.stderr else 'unknown error'}")
        return None

    print(f"  [vLLM r={rate}] Done -> {exp_dir}")
    return exp_dir


def extract_metrics(exp_dir):
    """Extract mean latency from request_metrics CSV."""
    import glob

    csv_files = list(exp_dir.rglob("request_metrics_*.csv"))
    if not csv_files:
        return None

    import pandas as pd
    df = pd.read_csv(csv_files[0])
    mean_latency = df["request_e2e_time"].mean()
    p99_latency = df["request_e2e_time"].quantile(0.99)

    return {
        "mean": mean_latency,
        "p99": p99_latency,
        "n": len(df)
    }


def main():
    """Run all experiments."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_subdir = OUTPUT_DIR / f"batch_{timestamp}"
    output_subdir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("Single-type (p512d20) Experiments - Reproduction")
    print("=" * 70)
    print(f"Source: 2026_03_23_wait_cp_all_rates_win.md")
    print(f"Workload: p512d20, nreq={NREQ}")
    print(f"Rates: {RATES}")
    print(f"Output: {output_subdir}")
    print("=" * 70)
    print()

    results = []

    total = len(RATES) * 3  # 3 schedulers
    count = 0

    for rate in RATES:
        print(f"\n--- Rate {rate} ---")

        # Run WCP
        count += 1
        print(f"[{count}/{total}]")
        wcp_dir = run_wcp(rate, output_subdir)
        if wcp_dir:
            metrics = extract_metrics(wcp_dir)
            if metrics:
                results.append({
                    "rate": rate,
                    "scheduler": "WCP",
                    "mean": metrics["mean"],
                    "p99": metrics["p99"],
                    "dir": str(wcp_dir)
                })

        # Run Sarathi
        count += 1
        print(f"[{count}/{total}]")
        sar_dir = run_sarathi(rate, output_subdir)
        if sar_dir:
            metrics = extract_metrics(sar_dir)
            if metrics:
                results.append({
                    "rate": rate,
                    "scheduler": "Sarathi",
                    "mean": metrics["mean"],
                    "p99": metrics["p99"],
                    "dir": str(sar_dir)
                })

        # Run vLLM
        count += 1
        print(f"[{count}/{total}]")
        vllm_dir = run_vllm(rate, output_subdir)
        if vllm_dir:
            metrics = extract_metrics(vllm_dir)
            if metrics:
                results.append({
                    "rate": rate,
                    "scheduler": "vLLM",
                    "mean": metrics["mean"],
                    "p99": metrics["p99"],
                    "dir": str(vllm_dir)
                })

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"\n{'Rate':>6} | {'Scheduler':>10} | {'Mean (s)':>10} | {'P99 (s)':>10} | {'Gap vs Sar':>12}")
    print("-" * 70)

    for rate in RATES:
        rate_results = [r for r in results if r["rate"] == rate]
        sarathi_mean = next((r["mean"] for r in rate_results if r["scheduler"] == "Sarathi"), None)

        for r in rate_results:
            gap = ""
            if sarathi_mean and r["scheduler"] != "Sarathi":
                gap_pct = (r["mean"] - sarathi_mean) / sarathi_mean * 100
                gap = f"{gap_pct:+.1f}%"
                if gap_pct < -1:
                    gap += " WIN"

            print(f"{r['rate']:>6} | {r['scheduler']:>10} | {r['mean']:>10.3f} | {r['p99']:>10.3f} | {gap:>12}")

    print("\n" + "=" * 70)
    print(f"All experiments completed! Results saved to: {output_subdir}")
    print("=" * 70)

    # Save summary to file
    summary_file = output_subdir / "summary.txt"
    with open(summary_file, "w") as f:
        f.write("Single-type (p512d20) Experiment Results\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Source: 2026_03_23_wait_cp_all_rates_win.md\n")
        f.write(f"nreq: {NREQ}\n")
        f.write("\n")
        f.write(f"{'Rate':>6} | {'Scheduler':>10} | {'Mean (s)':>10} | {'P99 (s)':>10}\n")
        f.write("-" * 50 + "\n")
        for r in sorted(results, key=lambda x: (x["rate"], x["scheduler"])):
            f.write(f"{r['rate']:>6} | {r['scheduler']:>10} | {r['mean']:>10.3f} | {r['p99']:>10.3f}\n")

    print(f"Summary saved to: {summary_file}")


if __name__ == "__main__":
    main()
