"""
Record representative WCP wait-on vs wait-off scenarios into SQLite for repro.

This script stores:
  1. scenario definitions
  2. per-run results for wait_gate on/off
  3. a compact comparison row per scenario

It is intentionally lightweight so we can append more scenarios later.
"""
import glob
import json
import os
import shutil
import sqlite3
import subprocess
import tempfile
from datetime import datetime

import pandas as pd

PROJECT = "/persistent/vidur_or"
DB = f"{PROJECT}/experiments.db"

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

# Keep this list small and representative. It can be extended later.
SCENARIOS = [
    {
        "name": "single_shortdecode_r18",
        "family": "single_type",
        "notes": "Single type, short decode.",
        "prompt_types": [
            {"type": "only", "prefill": 512, "decode": 20, "arrival_rate": 18.0},
        ],
        "max_tokens": 532,
        "total_limit": 21,
        "chunk_size": 256,
        "seg_margin": 0.0,
        "batch_gate": "on",
        "nreq": 1200,
    },
    {
        "name": "single_longdecode_r4",
        "family": "single_type",
        "notes": "Single type, very long decode.",
        "prompt_types": [
            {"type": "only", "prefill": 128, "decode": 1000, "arrival_rate": 4.0},
        ],
        "max_tokens": 1128,
        "total_limit": 980,
        "chunk_size": 128,
        "seg_margin": 0.0,
        "batch_gate": "on",
        "nreq": 1200,
    },
    {
        "name": "memory_limited_r3",
        "family": "memory_limited",
        "notes": "Large prefill to stress memory footprint.",
        "prompt_types": [
            {"type": "only", "prefill": 4096, "decode": 20, "arrival_rate": 3.0},
        ],
        "max_tokens": 4116,
        "total_limit": 22,
        "chunk_size": 512,
        "seg_margin": 0.0,
        "batch_gate": "on",
        "nreq": 1200,
    },
    {
        "name": "balanced_multitype_r20",
        "family": "multitype_balanced",
        "notes": "Balanced multi-type with similar decode lengths.",
        "prompt_types": [
            {"type": "a", "prefill": 256, "decode": 20, "arrival_rate": 10.0},
            {"type": "b", "prefill": 512, "decode": 20, "arrival_rate": 10.0},
        ],
        "max_tokens": 532,
        "total_limit": 30,
        "chunk_size": 256,
        "seg_margin": 0.0,
        "batch_gate": "on",
        "nreq": 1200,
    },
    {
        "name": "hetero_multitype_r20",
        "family": "multitype_heterogeneous",
        "notes": "Heterogeneous prefill/decode lengths.",
        "prompt_types": [
            {"type": "short", "prefill": 256, "decode": 10, "arrival_rate": 14.0},
            {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": 6.0},
        ],
        "max_tokens": 562,
        "total_limit": 50,
        "chunk_size": 256,
        "seg_margin": 0.3,
        "batch_gate": "on",
        "nreq": 1200,
    },
    {
        "name": "same_prefill_diff_decode_r20",
        "family": "multitype_same_prefill",
        "notes": "Same prefill, different decode lengths.",
        "prompt_types": [
            {"type": "short", "prefill": 512, "decode": 20, "arrival_rate": 14.0},
            {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": 6.0},
        ],
        "max_tokens": 562,
        "total_limit": 25,
        "chunk_size": 256,
        "seg_margin": 0.0,
        "batch_gate": "on",
        "nreq": 1200,
    },
]


def ensure_schema(cn: sqlite3.Connection) -> None:
    cn.execute(
        """CREATE TABLE IF NOT EXISTS wait_vs_nowait_scenarios (
            scenario_name TEXT PRIMARY KEY,
            family TEXT,
            notes TEXT,
            prompt_types_json TEXT,
            max_tokens INT,
            total_limit INT,
            chunk_size INT,
            seg_margin REAL,
            batch_gate TEXT,
            nreq INT,
            created_at TEXT
        )"""
    )
    cn.execute(
        """CREATE TABLE IF NOT EXISTS wait_vs_nowait_runs (
            timestamp TEXT,
            scenario_name TEXT,
            wait_gate INT,
            batch_gate TEXT,
            mean_latency REAL,
            p99_latency REAL,
            scheduling_delay_mean REAL,
            execution_time_mean REAL,
            short_mean REAL,
            long_mean REAL,
            n_steady INT,
            raw_prompt_types_json TEXT
        )"""
    )
    cn.execute(
        """CREATE TABLE IF NOT EXISTS wait_vs_nowait_summary (
            timestamp TEXT,
            scenario_name TEXT,
            mean_off REAL,
            mean_on REAL,
            delta_pct REAL,
            preferred_variant TEXT,
            notes TEXT
        )"""
    )
    cn.commit()


def upsert_scenario(cn: sqlite3.Connection, scenario: dict) -> None:
    cn.execute(
        """INSERT OR REPLACE INTO wait_vs_nowait_scenarios
           VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (
            scenario["name"],
            scenario["family"],
            scenario["notes"],
            json.dumps(scenario["prompt_types"], sort_keys=True),
            scenario["max_tokens"],
            scenario["total_limit"],
            scenario["chunk_size"],
            scenario["seg_margin"],
            scenario["batch_gate"],
            scenario["nreq"],
            datetime.now().isoformat(),
        ),
    )
    cn.commit()


def run_one(scenario: dict, wait_gate: bool) -> dict | None:
    tmpdir = tempfile.mkdtemp(prefix="vidur_wait_sql_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = scenario["batch_gate"]

    cmd = COMMON + [
        "--custom_request_generator_config_prompt_types", json.dumps(scenario["prompt_types"]),
        "--custom_request_generator_config_max_tokens", str(scenario["max_tokens"]),
        "--custom_request_generator_config_num_requests", str(scenario["nreq"]),
        "--metrics_config_output_dir", tmpdir,
        "--replica_scheduler_config_type", "general_nested_chunked",
        "--general_nested_chunked_scheduler_config_prompt_types", json.dumps(scenario["prompt_types"]),
        "--general_nested_chunked_scheduler_config_total_limit", str(scenario["total_limit"]),
        "--general_nested_chunked_scheduler_config_total_num_requests", str(scenario["nreq"]),
        "--general_nested_chunked_scheduler_config_chunk_size", str(scenario["chunk_size"]),
        "--general_nested_chunked_scheduler_config_seg_margin", str(scenario["seg_margin"]),
        "--general_nested_chunked_scheduler_config_force_clear",
    ]
    if not wait_gate:
        cmd.append("--no-general_nested_chunked_scheduler_config_wait_gate")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=PROJECT,
            env=env,
            timeout=3600,
        )
        if result.returncode != 0:
            return None
        csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
        if not csvs:
            return None
        df = pd.read_csv(csvs[0])
        steady = df.iloc[len(df) // 4:max(len(df) // 4 + 1, len(df) - 300)]

        out = {
            "mean_latency": float(steady["request_e2e_time"].mean()),
            "p99_latency": float(steady["request_e2e_time"].quantile(0.99)),
            "scheduling_delay_mean": float(steady["request_scheduling_delay"].mean()),
            "execution_time_mean": float(steady["request_execution_time"].mean()),
            "short_mean": None,
            "long_mean": None,
            "n_steady": int(len(steady)),
        }

        if "request_num_prefill_tokens" in steady.columns and steady["request_num_prefill_tokens"].nunique() >= 2:
            prefill_vals = sorted(steady["request_num_prefill_tokens"].unique())
            short_df = steady[steady["request_num_prefill_tokens"] == prefill_vals[0]]
            long_df = steady[steady["request_num_prefill_tokens"] == prefill_vals[-1]]
            out["short_mean"] = float(short_df["request_e2e_time"].mean())
            out["long_mean"] = float(long_df["request_e2e_time"].mean())

        return out
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def insert_run(cn: sqlite3.Connection, scenario: dict, wait_gate: bool, result: dict) -> None:
    cn.execute(
        """INSERT INTO wait_vs_nowait_runs
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(),
            scenario["name"],
            1 if wait_gate else 0,
            scenario["batch_gate"],
            result["mean_latency"],
            result["p99_latency"],
            result["scheduling_delay_mean"],
            result["execution_time_mean"],
            result["short_mean"],
            result["long_mean"],
            result["n_steady"],
            json.dumps(scenario["prompt_types"], sort_keys=True),
        ),
    )
    cn.commit()


def insert_summary(cn: sqlite3.Connection, scenario: dict, off: dict, on: dict) -> None:
    delta_pct = (on["mean_latency"] - off["mean_latency"]) / off["mean_latency"] * 100
    preferred_variant = "wait_on" if delta_pct < 0 else "wait_off"
    cn.execute(
        """INSERT INTO wait_vs_nowait_summary
           VALUES(?,?,?,?,?,?,?)""",
        (
            datetime.now().isoformat(),
            scenario["name"],
            off["mean_latency"],
            on["mean_latency"],
            delta_pct,
            preferred_variant,
            scenario["notes"],
        ),
    )
    cn.commit()


def main() -> None:
    cn = sqlite3.connect(DB)
    ensure_schema(cn)

    for scenario in SCENARIOS:
        upsert_scenario(cn, scenario)
        print(f"SCENARIO {scenario['name']}", flush=True)
        off = run_one(scenario, wait_gate=False)
        on = run_one(scenario, wait_gate=True)
        print(f"  off={off}", flush=True)
        print(f"  on ={on}", flush=True)
        if off is None or on is None:
            print("  skipped summary due to failed run", flush=True)
            continue
        insert_run(cn, scenario, False, off)
        insert_run(cn, scenario, True, on)
        insert_summary(cn, scenario, off, on)

    cn.close()
    print(f"\nRecorded scenarios and runs into {DB}", flush=True)


if __name__ == "__main__":
    main()
