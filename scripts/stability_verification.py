"""
Stability Verification: Prove WCP has larger stability region than Sarathi.

Method: At critical rates near the stability boundary, run with increasing nreq.
- If stable: mean latency converges as nreq grows (bounded queue)
- If unstable: mean latency grows as nreq grows (queue builds up)

This directly proves: ∃ λ where WCP stable but Sarathi unstable → stability region larger.
"""
import subprocess, json, pandas as pd, os, shutil, glob, sqlite3, tempfile, sys
from datetime import datetime

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

cn = sqlite3.connect(DB)
cn.execute("""CREATE TABLE IF NOT EXISTS stability_verification (
    timestamp TEXT, workload TEXT, algorithm TEXT, config_name TEXT,
    arrival_rate REAL, nreq INT, mean_latency REAL, p99_latency REAL,
    tail_mean REAL, n_steady INT
)""")
cn.commit()

# W3 workload - critical rates near boundary
W3_TYPES = [
    {"type": "short", "prefill": 512, "decode": 20, "arrival_rate_frac": 0.7},
    {"type": "long",  "prefill": 512, "decode": 50, "arrival_rate_frac": 0.3},
]

# Critical rates: Sarathi boundary ~22, WCP should be stable further
# Test rates where we expect Sarathi unstable but WCP stable
RATES = [20, 21, 22, 23, 24]
NREQS = [2000, 5000, 10000, 20000]


def make_prompt_types(rate):
    return json.dumps([
        {"type": t["type"], "prefill": t["prefill"], "decode": t["decode"],
         "arrival_rate": round(rate * t["arrival_rate_frac"], 2)}
        for t in W3_TYPES
    ])


def already_done(algorithm, config_name, rate, nreq):
    r = cn.execute(
        "SELECT 1 FROM stability_verification WHERE algorithm=? AND config_name=? AND arrival_rate=? AND nreq=? LIMIT 1",
        (algorithm, config_name, rate, nreq)
    ).fetchone()
    return r is not None


def run_sim(extra_args, nreq, gate=True):
    tmpdir = tempfile.mkdtemp(prefix="vidur_stab_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on" if gate else "off"
    cmd = COMMON + [
        "--custom_request_generator_config_num_requests", str(nreq),
        "--metrics_config_output_dir", tmpdir,
    ] + extra_args
    # Longer timeout for large nreq
    timeout = max(1800, nreq // 2)
    result = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=timeout, env=env, text=True)
    if result.returncode != 0:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if not csvs:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    df = pd.read_csv(csvs[0])
    shutil.rmtree(tmpdir, ignore_errors=True)
    # Steady-state: skip first 25%, skip last 500
    start = len(df) // 4
    end = max(start + 1, len(df) - 500)
    s = df.iloc[start:end]
    # Also compute tail mean: last 25% of requests (shows if latency still growing)
    tail_start = 3 * len(df) // 4
    tail = df.iloc[tail_start:]
    return s["request_e2e_time"].mean(), s["request_e2e_time"].quantile(0.99), tail["request_e2e_time"].mean(), len(s)


for rate in RATES:
    pt = make_prompt_types(rate)
    print(f"\n=== rate={rate} ===", flush=True)

    for nreq in NREQS:
        # Sarathi baseline
        if not already_done("sarathi", "Sarathi512", rate, nreq):
            res = run_sim([
                "--custom_request_generator_config_prompt_types", pt,
                "--custom_request_generator_config_max_tokens", "562",
                "--replica_scheduler_config_type", "sarathi",
                "--sarathi_scheduler_config_chunk_size", "512",
                "--sarathi_scheduler_config_batch_size_cap", "512",
            ], nreq=nreq, gate=False)
            if res:
                m, p99, tail_m, n = res
                cn.execute("INSERT INTO stability_verification VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (datetime.now().isoformat(), "W3", "sarathi", "Sarathi512",
                            rate, nreq, m, p99, tail_m, n))
                cn.commit()
                print(f"  Sar  nreq={nreq:5d} mean={m:.3f}s tail={tail_m:.3f}s", flush=True)
            else:
                print(f"  Sar  nreq={nreq:5d} FAIL", flush=True)
        else:
            row = cn.execute("SELECT mean_latency, tail_mean FROM stability_verification WHERE algorithm='sarathi' AND arrival_rate=? AND nreq=?", (rate, nreq)).fetchone()
            print(f"  Sar  nreq={nreq:5d} mean={row[0]:.3f}s tail={row[1]:.3f}s [cached]", flush=True)

        # WCP (cs128_tl30 - best for high rates)
        if not already_done("wcp", "cs128_tl30", rate, nreq):
            res = run_sim([
                "--custom_request_generator_config_prompt_types", pt,
                "--custom_request_generator_config_max_tokens", "562",
                "--replica_scheduler_config_type", "general_nested_chunked",
                "--general_nested_chunked_scheduler_config_prompt_types", pt,
                "--general_nested_chunked_scheduler_config_total_limit", "30",
                "--general_nested_chunked_scheduler_config_total_num_requests", str(nreq),
                "--general_nested_chunked_scheduler_config_chunk_size", "128",
                "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
                "--general_nested_chunked_scheduler_config_force_clear",
                "--no-general_nested_chunked_scheduler_config_wait_gate",
            ], nreq=nreq, gate=True)
            if res:
                m, p99, tail_m, n = res
                cn.execute("INSERT INTO stability_verification VALUES(?,?,?,?,?,?,?,?,?,?)",
                           (datetime.now().isoformat(), "W3", "wcp", "cs128_tl30",
                            rate, nreq, m, p99, tail_m, n))
                cn.commit()
                print(f"  WCP  nreq={nreq:5d} mean={m:.3f}s tail={tail_m:.3f}s", flush=True)
            else:
                print(f"  WCP  nreq={nreq:5d} FAIL", flush=True)
        else:
            row = cn.execute("SELECT mean_latency, tail_mean FROM stability_verification WHERE algorithm='wcp' AND arrival_rate=? AND nreq=?", (rate, nreq)).fetchone()
            print(f"  WCP  nreq={nreq:5d} mean={row[0]:.3f}s tail={row[1]:.3f}s [cached]", flush=True)

cn.close()

# Print analysis
print("\n=== Stability Analysis ===")
cn = sqlite3.connect(DB)
for rate in RATES:
    print(f"\nrate={rate}:")
    for algo in ["sarathi", "wcp"]:
        label = "Sar" if algo == "sarathi" else "WCP"
        rows = cn.execute(
            "SELECT nreq, mean_latency, tail_mean FROM stability_verification WHERE algorithm=? AND arrival_rate=? ORDER BY nreq",
            (algo, rate)
        ).fetchall()
        if len(rows) >= 2:
            first_m = rows[0][1]
            last_m = rows[-1][1]
            growth = (last_m - first_m) / first_m * 100
            tail_growth = (rows[-1][2] - rows[0][2]) / rows[0][2] * 100
            verdict = "STABLE" if growth < 20 else "UNSTABLE"
            print(f"  {label}: nreq {rows[0][0]}→{rows[-1][0]}: mean {first_m:.3f}→{last_m:.3f}s ({growth:+.0f}%) tail_growth={tail_growth:+.0f}% → {verdict}")
cn.close()
print("\nDone!")
