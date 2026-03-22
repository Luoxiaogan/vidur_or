"""
Profile Sarathi and vLLM baselines.
Clean run: deletes simulator_output before each simulation.
Results stored in experiments.db.
"""
import subprocess, json, pandas as pd, os, sqlite3, shutil, glob
from math import ceil
from datetime import datetime

PROJECT = "/home/CPU/vidur_or"
OUT = f"{PROJECT}/simulator_output"
DB = f"{PROJECT}/experiments.db"

l0, l1, nreq = 512, 20, 5000

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
    "--custom_request_generator_config_max_tokens", str(l0 + l1),
    "--custom_request_generator_config_num_requests", str(nreq),
]

cn = sqlite3.connect(DB)


def run_clean(extra_args):
    """Run simulation in a clean output directory. Return CSV path or None."""
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    result = subprocess.run(
        COMMON + extra_args,
        capture_output=True, text=True,
        cwd=PROJECT, timeout=1800
    )
    dirs = os.listdir(OUT)
    if not dirs:
        print(f"    ERROR: no output dir. rc={result.returncode}")
        if result.stderr:
            print(f"    stderr: {result.stderr[-300:]}")
        return None
    csvs = glob.glob(f"{OUT}/{dirs[0]}/request_metrics_*.csv")
    if not csvs:
        print(f"    ERROR: no CSV in {dirs[0]}")
        return None
    return csvs[0]


def metric(csv_path):
    df = pd.read_csv(csv_path)
    start = len(df) // 4
    end = max(start + 1, len(df) - 500)
    s = df.iloc[start:end]
    return (
        s["request_e2e_time"].mean(),
        s["request_e2e_time"].quantile(0.99),
        len(s),
    )


def record(alg, sem, cs, tl, rate, mean, p99, n):
    K = ceil(l0 / cs) if cs and cs > 0 else 0
    P = tl / (K + l1) if tl else 0
    cn.execute(
        "INSERT INTO experiments "
        "(timestamp,algorithm,chunk_semantics,chunk_size,total_limit,"
        "arrival_rate,l0,l1,nreq,K,per_stage_P,mean_latency,p99_latency,n_steady) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(), alg, sem, cs, tl,
         rate, l0, l1, nreq, K, round(P, 2), mean, p99, n),
    )
    cn.commit()


rates = [12, 14, 16, 18, 20]
sarathi_chunks = [128, 256, 512]

print(f"=== Baseline Profiling: l0={l0} l1={l1} nreq={nreq} ===\n")

# ---- Sarathi ----
print("--- Sarathi ---")
for cs in sarathi_chunks:
    K = ceil(l0 / cs)
    for rate in rates:
        pt = json.dumps([{"type": "t1", "prefill": l0, "decode": l1, "arrival_rate": rate}])
        csv = run_clean([
            "--custom_request_generator_config_prompt_types", pt,
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", str(cs),
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ])
        if csv:
            m, p, n = metric(csv)
            record("sarathi", "total_budget", cs, None, rate, m, p, n)
            print(f"  Sarathi cs={cs} K={K} r={rate}: {m:.3f}s p99={p:.3f}s n={n}", flush=True)
        else:
            print(f"  Sarathi cs={cs} r={rate}: FAILED", flush=True)

# ---- vLLM ----
print("\n--- vLLM ---")
for rate in rates:
    pt = json.dumps([{"type": "t1", "prefill": l0, "decode": l1, "arrival_rate": rate}])
    csv = run_clean([
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "vllm",
        "--vllm_scheduler_config_batch_size_cap", "512",
    ])
    if csv:
        m, p, n = metric(csv)
        record("vllm", "none", 0, None, rate, m, p, n)
        print(f"  vLLM r={rate}: {m:.3f}s p99={p:.3f}s n={n}", flush=True)
    else:
        print(f"  vLLM r={rate}: FAILED", flush=True)

# ---- Summary ----
print("\n=== Summary ===")
print(f"{'alg':>10} {'cs':>4} | " + " | ".join(f"r={r:>2}" for r in rates))
print("-" * 60)
for alg in ["sarathi", "vllm"]:
    if alg == "sarathi":
        for cs in sarathi_chunks:
            row = f"{'Sar'+str(cs):>10} {cs:>4} |"
            for r in rates:
                res = cn.execute(
                    "SELECT mean_latency FROM experiments "
                    "WHERE algorithm=? AND chunk_size=? AND arrival_rate=?",
                    (alg, cs, r)
                ).fetchone()
                row += f" {res[0]:>6.3f}s |" if res else "   FAIL |"
            print(row)
    else:
        row = f"{'vLLM':>10} {'':>4} |"
        for r in rates:
            res = cn.execute(
                "SELECT mean_latency FROM experiments "
                "WHERE algorithm=? AND arrival_rate=?",
                (alg, r)
            ).fetchone()
            row += f" {res[0]:>6.3f}s |" if res else "   FAIL |"
        print(row)

cn.close()
print(f"\nDB saved: {DB}")
