#!/usr/bin/env python3
"""
Mean Latency vs Arrival Rate Experiment - Reviewer 3 Requirement

Generates the standard queueing theory plot: mean latency as a function of arrival rate.
This shows the stability region where latency diverges.

Requirements from Reviewer 3:
- "infinite(-or-long-enough)-horizon mean latency as a function of arrival rate"
- "policies with lower maximum throughput would have mean latency diverge to infinity at lower arrival rates"
"""

import subprocess
import json
import pandas as pd
import os
import shutil
import glob
import sqlite3
import tempfile
import sys
from datetime import datetime
from typing import List, Dict, Tuple, Optional

# Project configuration
PROJECT = "/home/archer/vidur_or"
DB = f"{PROJECT}/experiments.db"
OUTPUT_DIR = f"{PROJECT}/outputs/mean_latency_vs_rate"

# Common simulation parameters
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

def init_database():
    """Initialize SQLite database for storing results."""
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    cn = sqlite3.connect(DB)
    cn.execute("""
    CREATE TABLE IF NOT EXISTS mean_latency_vs_rate (
        timestamp TEXT,
        experiment_id TEXT,
        workload TEXT,
        algorithm TEXT,
        arrival_rate REAL,
        mean_latency_ms REAL,
        p50_latency_ms REAL,
        p99_latency_ms REAL,
        throughput REAL,
        n_requests INTEGER,
        n_completed INTEGER,
        config TEXT
    )""")
    cn.commit()
    cn.close()

def run_simulation(
    algorithm: str,
    arrival_rate: float,
    prompt_types: List[Dict],
    max_tokens: int,
    n_requests: int = 5000,
    extra_args: List[str] = None
) -> Optional[Dict]:
    """
    Run a single simulation and return metrics.

    Returns:
        Dict with mean_latency_ms, p50_latency_ms, p99_latency_ms, throughput, n_completed
        or None if simulation failed
    """
    tmpdir = tempfile.mkdtemp(prefix="vidur_mlr_")
    pt_json = json.dumps(prompt_types)

    cmd = COMMON + [
        "--custom_request_generator_config_num_requests", str(n_requests),
        "--custom_request_generator_config_prompt_types", pt_json,
        "--custom_request_generator_config_max_tokens", str(max_tokens),
        "--metrics_config_output_dir", tmpdir,
    ]

    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=PROJECT,
            timeout=1800,
            text=True
        )

        if result.returncode != 0:
            print(f"  Simulation failed: {result.stderr[:200]}")
            shutil.rmtree(tmpdir, ignore_errors=True)
            return None

        # Find and read metrics CSV
        csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
        if not csvs:
            print(f"  No metrics CSV found")
            shutil.rmtree(tmpdir, ignore_errors=True)
            return None

        df = pd.read_csv(csvs[0])
        shutil.rmtree(tmpdir, ignore_errors=True)

        # Calculate steady-state metrics (skip first 25%, skip last 500)
        start_idx = len(df) // 4
        end_idx = max(start_idx + 1, len(df) - 500)
        steady_df = df.iloc[start_idx:end_idx]

        if len(steady_df) == 0:
            return None

        # Calculate metrics
        mean_latency = steady_df["request_e2e_time"].mean()
        p50_latency = steady_df["request_e2e_time"].median()
        p99_latency = steady_df["request_e2e_time"].quantile(0.99)

        # Calculate throughput (requests per second)
        if len(steady_df) > 1:
            time_span = steady_df["completion_time"].max() - steady_df["arrival_time"].min()
            throughput = len(steady_df) / time_span if time_span > 0 else 0
        else:
            throughput = 0

        return {
            "mean_latency_ms": mean_latency * 1000,  # Convert to ms
            "p50_latency_ms": p50_latency * 1000,
            "p99_latency_ms": p99_latency * 1000,
            "throughput": throughput,
            "n_requests": n_requests,
            "n_completed": len(steady_df),
        }

    except subprocess.TimeoutExpired:
        print(f"  Simulation timeout")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    except Exception as e:
        print(f"  Simulation error: {e}")
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None

def run_vllm_baseline(arrival_rate: float, prompt_types: List[Dict], max_tokens: int) -> Optional[Dict]:
    """Run vLLM baseline simulation."""
    return run_simulation(
        algorithm="vllm",
        arrival_rate=arrival_rate,
        prompt_types=prompt_types,
        max_tokens=max_tokens,
        extra_args=[
            "--replica_scheduler_config_type", "vllm",
            "--vllm_scheduler_config_max_tokens_in_batch", "4096",
        ]
    )

def run_sarathi_baseline(arrival_rate: float, prompt_types: List[Dict], max_tokens: int) -> Optional[Dict]:
    """Run Sarathi baseline simulation."""
    return run_simulation(
        algorithm="sarathi",
        arrival_rate=arrival_rate,
        prompt_types=prompt_types,
        max_tokens=max_tokens,
        extra_args=[
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ]
    )

def run_wait_cp(arrival_rate: float, prompt_types: List[Dict], max_tokens: int) -> Optional[Dict]:
    """Run WAIT-CP (Wait-Chunk-Prefill) simulation."""
    pt_json = json.dumps(prompt_types)

    # Use environment variable to enable per-segment gate
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on"

    return run_simulation(
        algorithm="wait_cp",
        arrival_rate=arrival_rate,
        prompt_types=prompt_types,
        max_tokens=max_tokens,
        extra_args=[
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt_json,
            "--general_nested_chunked_scheduler_config_total_limit", "25",
            "--general_nested_chunked_scheduler_config_total_num_requests", "5000",
            "--general_nested_chunked_scheduler_config_chunk_size", "192",
            "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate",
        ]
    )

def make_prompt_types(prefill: int, decode: int, arrival_rate: float) -> List[Dict]:
    """Create prompt types configuration for single-type workload."""
    return [{
        "type": "default",
        "prefill": prefill,
        "decode": decode,
        "arrival_rate": arrival_rate
    }]

def experiment_single_type_known():
    """
    Experiment B1: Single type, known output
    - Workload: p512d20 (prefill 512, decode 20)
    - Arrival rates: 10-30 qps
    - Algorithms: WAIT-CP vs vLLM vs Sarathi
    """
    print("\n" + "="*80)
    print("Experiment: Single Type, Known Output (p512d20)")
    print("="*80)

    cn = sqlite3.connect(DB)
    experiment_id = f"single_p512d20_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Arrival rates from 10 to 30 qps
    rates = list(range(10, 31))
    prefill, decode = 512, 20
    max_tokens = prefill + decode + 10

    results = []

    for rate in rates:
        print(f"\nRate = {rate} qps:")
        prompt_types = make_prompt_types(prefill, decode, rate)

        # Run vLLM
        print("  Running vLLM...", end=" ")
        res = run_vllm_baseline(rate, prompt_types, max_tokens)
        if res:
            print(f"mean={res['mean_latency_ms']:.1f}ms")
            cn.execute(
                """INSERT INTO mean_latency_vs_rate
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), experiment_id, "single_p512d20", "vllm",
                 rate, res["mean_latency_ms"], res["p50_latency_ms"], res["p99_latency_ms"],
                 res["throughput"], res["n_requests"], res["n_completed"], "baseline")
            )
            cn.commit()
            results.append({"rate": rate, "algorithm": "vLLM", **res})
        else:
            print("FAILED")

        # Run Sarathi
        print("  Running Sarathi...", end=" ")
        res = run_sarathi_baseline(rate, prompt_types, max_tokens)
        if res:
            print(f"mean={res['mean_latency_ms']:.1f}ms")
            cn.execute(
                """INSERT INTO mean_latency_vs_rate
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), experiment_id, "single_p512d20", "sarathi",
                 rate, res["mean_latency_ms"], res["p50_latency_ms"], res["p99_latency_ms"],
                 res["throughput"], res["n_requests"], res["n_completed"], "baseline")
            )
            cn.commit()
            results.append({"rate": rate, "algorithm": "Sarathi", **res})
        else:
            print("FAILED")

        # Run WAIT-CP
        print("  Running WAIT-CP...", end=" ")
        res = run_wait_cp(rate, prompt_types, max_tokens)
        if res:
            print(f"mean={res['mean_latency_ms']:.1f}ms")
            cn.execute(
                """INSERT INTO mean_latency_vs_rate
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (datetime.now().isoformat(), experiment_id, "single_p512d20", "wait_cp",
                 rate, res["mean_latency_ms"], res["p50_latency_ms"], res["p99_latency_ms"],
                 res["throughput"], res["n_requests"], res["n_completed"], "cs192_tl25")
            )
            cn.commit()
            results.append({"rate": rate, "algorithm": "WAIT-CP", **res})
        else:
            print("FAILED")

    cn.close()
    print(f"\nExperiment {experiment_id} completed!")
    return results

def generate_plots():
    """Generate mean latency vs arrival rate plots."""
    import matplotlib.pyplot as plt
    import matplotlib
    matplotlib.use('Agg')

    cn = sqlite3.connect(DB)

    # Get all data
    df = pd.read_sql_query(
        "SELECT * FROM mean_latency_vs_rate ORDER BY arrival_rate",
        cn
    )

    if len(df) == 0:
        print("No data to plot")
        cn.close()
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Plot 1: Single workload comparison
    fig, ax = plt.subplots(figsize=(10, 6))

    for algo in df["algorithm"].unique():
        algo_df = df[df["algorithm"] == algo]
        ax.plot(algo_df["arrival_rate"], algo_df["mean_latency_ms"],
                marker='o', label=algo, linewidth=2)

    ax.set_xlabel("Arrival Rate (requests/sec)", fontsize=12)
    ax.set_ylabel("Mean Latency (ms)", fontsize=12)
    ax.set_title("Mean Latency vs Arrival Rate\n(Single Type: p512d20)", fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/mean_latency_vs_rate_single.png", dpi=300)
    plt.savefig(f"{OUTPUT_DIR}/mean_latency_vs_rate_single.pdf")
    print(f"\nSaved plot to {OUTPUT_DIR}/mean_latency_vs_rate_single.png")

    # Plot 2: Throughput comparison
    fig, ax = plt.subplots(figsize=(10, 6))

    for algo in df["algorithm"].unique():
        algo_df = df[df["algorithm"] == algo]
        ax.plot(algo_df["arrival_rate"], algo_df["throughput"],
                marker='s', label=algo, linewidth=2)

    # Add reference line: throughput = arrival_rate (stable system)
    max_rate = df["arrival_rate"].max()
    ax.plot([0, max_rate], [0, max_rate], 'k--', alpha=0.5, label='Ideal (stable)')

    ax.set_xlabel("Arrival Rate (requests/sec)", fontsize=12)
    ax.set_ylabel("Throughput (requests/sec)", fontsize=12)
    ax.set_title("Throughput vs Arrival Rate\n(Stability Region Visualization)", fontsize=14, fontweight='bold')
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/throughput_vs_rate_single.png", dpi=300)
    plt.savefig(f"{OUTPUT_DIR}/throughput_vs_rate_single.pdf")
    print(f"Saved plot to {OUTPUT_DIR}/throughput_vs_rate_single.png")

    cn.close()

def main():
    """Main entry point."""
    init_database()

    print("\n" + "="*80)
    print("Mean Latency vs Arrival Rate Experiment")
    print("Addressing Reviewer 3's requirement for stability region analysis")
    print("="*80)

    # Run experiments
    results = experiment_single_type_known()

    # Generate plots
    generate_plots()

    print("\n" + "="*80)
    print("Experiment completed!")
    print(f"Results saved to: {DB} (table: mean_latency_vs_rate)")
    print(f"Plots saved to: {OUTPUT_DIR}/")
    print("="*80)

if __name__ == "__main__":
    main()
