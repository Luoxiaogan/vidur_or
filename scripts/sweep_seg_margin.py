"""
Sweep seg_margin for multi-type Nested WAIT.

Paper constraint: n_{k+1}/n_k > p_k.
seg_margin=0 → equality (boundary), positive → stricter (more budget for later segs).

Sweep: seg_margin × tl × rate, fixed cs=256, gate=ON, B2 workload.
"""
import subprocess, json, pandas as pd, os, shutil, glob, sqlite3
from math import ceil
from datetime import datetime

PROJECT = "/home/CPU/vidur_or"
OUT = f"{PROJECT}/simulator_output"
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

# Ensure table has seg_margin column
try:
    cn.execute("ALTER TABLE experiments ADD COLUMN seg_margin REAL DEFAULT 0.0")
    cn.commit()
except sqlite3.OperationalError:
    pass  # column already exists


def run_sim(extra_args, gate="on", nreq=5000, max_tokens=562):
    import tempfile
    tmpdir = tempfile.mkdtemp(prefix="vidur_sim_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = gate
    cmd = COMMON + [
        "--custom_request_generator_config_max_tokens", str(max_tokens),
        "--custom_request_generator_config_num_requests", str(nreq),
        "--metrics_config_output_dir", tmpdir,
    ] + extra_args
    try:
        result = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=1800, env=env, text=True)
        if result.returncode != 0:
            err_lines = (result.stderr or "").strip().split("\n")
            for line in err_lines[-5:]:
                print(f"    [STDERR] {line}", flush=True)
            print(f"    [ERR] exit={result.returncode}", flush=True)
            shutil.rmtree(tmpdir, ignore_errors=True)
            return None
    except subprocess.TimeoutExpired:
        print("    [ERR] timeout", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    # CSV 可能在 tmpdir/ 直接下，也可能在 tmpdir/<timestamp>/ 下
    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if not csvs:
        print(f"    [ERR] no CSV in {tmpdir}", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    df = pd.read_csv(csvs[0])
    shutil.rmtree(tmpdir, ignore_errors=True)
    s = df.iloc[len(df) // 4:max(len(df) // 4 + 1, len(df) - 500)]
    return s["request_e2e_time"].mean(), s["request_e2e_time"].quantile(0.99), len(s)


def record(alg, cs, tl, rate, m, p99, n, seg_margin=0.0, workload="b2_2type", nreq=5000):
    cn.execute(
        "INSERT INTO experiments(timestamp,algorithm,chunk_semantics,chunk_size,total_limit,"
        "arrival_rate,l0,l1,nreq,K,per_stage_P,mean_latency,p99_latency,n_steady,seg_margin) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat() + f"_{workload}", alg, "nested_per_req", cs, tl,
         rate, 0, 0, nreq, 0, 0, m, p99, n, seg_margin))
    cn.commit()


# ========================================================
# B2: 2-type workload
# Type 1: prefill=256, decode=10, 70% traffic
# Type 2: prefill=512, decode=50, 30% traffic
# ========================================================
NREQ = 5000
MAX_TOKENS = 562
CS = 256

RATES = [12, 16, 20, 24, 30, 34, 38]
TLS = [10, 15, 20, 30, 50]
SEG_MARGINS = [0.0, 0.3]

print("=" * 70)
print("Sweep seg_margin: B2 2-type workload")
print(f"  rates={RATES}, tls={TLS}, seg_margins={SEG_MARGINS}, cs={CS}")
print("=" * 70)

# First run Sarathi baselines for each rate
baselines = {}
for total_rate in RATES:
    r1 = round(total_rate * 0.7, 1)
    r2 = round(total_rate * 0.3, 1)
    pt = json.dumps([
        {"type": "short", "prefill": 256, "decode": 10, "arrival_rate": r1},
        {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": r2},
    ])
    res = run_sim([
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--sarathi_scheduler_config_batch_size_cap", "512",
    ], nreq=NREQ, max_tokens=MAX_TOKENS)
    if res:
        m, p99, n = res
        baselines[total_rate] = m
        record("sarathi", 512, None, total_rate, m, p99, n, workload="b2_margin_sweep")
        print(f"  Sarathi(512) r={total_rate}: {m:.3f}s", flush=True)
    else:
        print(f"  Sarathi(512) r={total_rate}: FAIL", flush=True)

# Sweep WCP configs
for total_rate in RATES:
    r1 = round(total_rate * 0.7, 1)
    r2 = round(total_rate * 0.3, 1)
    pt = json.dumps([
        {"type": "short", "prefill": 256, "decode": 10, "arrival_rate": r1},
        {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": r2},
    ])
    sar_m = baselines.get(total_rate)
    if sar_m is None:
        continue

    for tl in TLS:
        for sm in SEG_MARGINS:
            for wg in [True, False]:
                wg_label = "W" if wg else "N"
                wg_args = [] if wg else ["--no-general_nested_chunked_scheduler_config_wait_gate"]
                res = run_sim([
                    "--custom_request_generator_config_prompt_types", pt,
                    "--replica_scheduler_config_type", "general_nested_chunked",
                    "--general_nested_chunked_scheduler_config_prompt_types", pt,
                    "--general_nested_chunked_scheduler_config_total_limit", str(tl),
                    "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
                    "--general_nested_chunked_scheduler_config_chunk_size", str(CS),
                    "--general_nested_chunked_scheduler_config_seg_margin", str(sm),
                    "--general_nested_chunked_scheduler_config_force_clear",
                ] + wg_args, nreq=NREQ, max_tokens=MAX_TOKENS)
                if res:
                    m, p99, n = res
                    g = (m - sar_m) / sar_m * 100
                    mk = "WIN" if g < -1 else ""
                    record("wait_cp", CS, tl, total_rate, m, p99, n, seg_margin=sm, workload=f"b2_{wg_label}")
                    print(f"  r={total_rate} tl={tl:3d} sm={sm:.1f} {wg_label}: {m:.3f}s ({g:+.1f}%) {mk}", flush=True)
                else:
                    print(f"  r={total_rate} tl={tl:3d} sm={sm:.1f} {wg_label}: FAIL", flush=True)

cn.close()
print(f"\nAll results saved to {DB}")
print("Done!")
