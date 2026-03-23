"""
Overnight multi-type experiment: B2 (2 types) + B3 (3 types)
Also re-verify single-type across full rate grid.

Results stored in experiments.db.
Each run: clean simulator_output, run, extract metrics, record.

Expected runtime: ~6-8 hours.
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
]

cn = sqlite3.connect(DB)


def run_sim(extra_args, gate="on", nreq=5000, max_tokens=532):
    """Run simulation, return (mean, p99, n) or None."""
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = gate
    cmd = COMMON + [
        "--custom_request_generator_config_max_tokens", str(max_tokens),
        "--custom_request_generator_config_num_requests", str(nreq),
    ] + extra_args
    try:
        subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=1800, env=env)
    except subprocess.TimeoutExpired:
        return None
    dirs = os.listdir(OUT)
    if not dirs:
        return None
    csvs = glob.glob(f"{OUT}/{dirs[0]}/request_metrics_*.csv")
    if not csvs:
        return None
    df = pd.read_csv(csvs[0])
    s = df.iloc[len(df) // 4:max(len(df) // 4 + 1, len(df) - 500)]
    return s["request_e2e_time"].mean(), s["request_e2e_time"].quantile(0.99), len(s)


def record(alg, sem, cs, tl, rate, m, p99, n, workload="single", nreq=5000):
    cn.execute(
        "INSERT INTO experiments(timestamp,algorithm,chunk_semantics,chunk_size,total_limit,"
        "arrival_rate,l0,l1,nreq,K,per_stage_P,mean_latency,p99_latency,n_steady) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat() + f"_{workload}", alg, sem, cs, tl,
         rate, 0, 0, nreq, 0, 0, m, p99, n))
    cn.commit()


# ========================================================
# Workload B2: 2 types
# Type 1: prefill=256, decode=10, 70% traffic
# Type 2: prefill=512, decode=50, 30% traffic
# ========================================================
print("=" * 60)
print("B2: 2-type workload (short + long)")
print("=" * 60)

b2_nreq = 5000
b2_max_tokens = 562  # max(256+10, 512+50)

# Sweep total rates
b2_rates = [8, 10, 12, 14, 16, 18, 20]

# For each total rate, split 70/30
for total_rate in b2_rates:
    r1 = round(total_rate * 0.7, 1)
    r2 = round(total_rate * 0.3, 1)
    pt = json.dumps([
        {"type": "short", "prefill": 256, "decode": 10, "arrival_rate": r1},
        {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": r2},
    ])

    # Sarathi(512)
    res = run_sim([
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--sarathi_scheduler_config_batch_size_cap", "512",
    ], nreq=b2_nreq, max_tokens=b2_max_tokens)
    if res:
        m, p99, n = res
        record("sarathi", "total_budget", 512, None, total_rate, m, p99, n, "b2_2type", b2_nreq)
        sar_m = m
        print(f"  B2 Sar512 r={total_rate}: {m:.3f}s", flush=True)
    else:
        print(f"  B2 Sar512 r={total_rate}: FAIL", flush=True)
        continue

    # vLLM
    res = run_sim([
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "vllm",
        "--vllm_scheduler_config_batch_size_cap", "512",
    ], nreq=b2_nreq, max_tokens=b2_max_tokens)
    if res:
        m, p99, n = res
        record("vllm", "none", 0, None, total_rate, m, p99, n, "b2_2type", b2_nreq)
        print(f"  B2 vLLM  r={total_rate}: {m:.3f}s", flush=True)

    # WCP: sweep (tl, cs)
    wcp_configs = [
        (21, 256), (25, 256), (30, 256),
        (21, 128), (30, 128),
    ]
    for tl, cs in wcp_configs:
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt,
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", str(tl),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(b2_nreq),
            "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
            "--general_nested_chunked_scheduler_config_force_clear",
        ], nreq=b2_nreq, max_tokens=b2_max_tokens)
        if res:
            m, p99, n = res
            record("wait_cp", "nested_per_req", cs, tl, total_rate, m, p99, n, "b2_2type", b2_nreq)
            g = (m - sar_m) / sar_m * 100
            mk = "WIN" if g < -1 else ""
            print(f"  B2 WCP(tl={tl},cs={cs}) r={total_rate}: {m:.3f}s ({g:+.1f}%) {mk}", flush=True)


# ========================================================
# Workload B3: 3 types
# Type 1: prefill=128, decode=5, 50% traffic
# Type 2: prefill=512, decode=20, 30% traffic
# Type 3: prefill=1024, decode=100, 20% traffic
# ========================================================
print("\n" + "=" * 60)
print("B3: 3-type workload (short + medium + long)")
print("=" * 60)

b3_nreq = 3000
b3_max_tokens = 1124  # max(128+5, 512+20, 1024+100)

b3_rates = [6, 8, 10, 12, 14, 16]

for total_rate in b3_rates:
    r1 = round(total_rate * 0.5, 1)
    r2 = round(total_rate * 0.3, 1)
    r3 = round(total_rate * 0.2, 1)
    pt = json.dumps([
        {"type": "short", "prefill": 128, "decode": 5, "arrival_rate": r1},
        {"type": "medium", "prefill": 512, "decode": 20, "arrival_rate": r2},
        {"type": "long", "prefill": 1024, "decode": 100, "arrival_rate": r3},
    ])

    # Sarathi(512)
    res = run_sim([
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--sarathi_scheduler_config_batch_size_cap", "512",
    ], nreq=b3_nreq, max_tokens=b3_max_tokens)
    if res:
        m, p99, n = res
        record("sarathi", "total_budget", 512, None, total_rate, m, p99, n, "b3_3type", b3_nreq)
        sar_m = m
        print(f"  B3 Sar512 r={total_rate}: {m:.3f}s", flush=True)
    else:
        print(f"  B3 Sar512 r={total_rate}: FAIL", flush=True)
        continue

    # vLLM
    res = run_sim([
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "vllm",
        "--vllm_scheduler_config_batch_size_cap", "512",
    ], nreq=b3_nreq, max_tokens=b3_max_tokens)
    if res:
        m, p99, n = res
        record("vllm", "none", 0, None, total_rate, m, p99, n, "b3_3type", b3_nreq)
        print(f"  B3 vLLM  r={total_rate}: {m:.3f}s", flush=True)

    # WCP: sweep (tl, cs)
    wcp_configs = [
        (25, 256), (30, 256), (40, 256),
        (25, 128), (30, 128), (40, 128),
    ]
    for tl, cs in wcp_configs:
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt,
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", str(tl),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(b3_nreq),
            "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
            "--general_nested_chunked_scheduler_config_force_clear",
        ], nreq=b3_nreq, max_tokens=b3_max_tokens)
        if res:
            m, p99, n = res
            record("wait_cp", "nested_per_req", cs, tl, total_rate, m, p99, n, "b3_3type", b3_nreq)
            g = (m - sar_m) / sar_m * 100
            mk = "WIN" if g < -1 else ""
            print(f"  B3 WCP(tl={tl},cs={cs}) r={total_rate}: {m:.3f}s ({g:+.1f}%) {mk}", flush=True)


cn.close()
print(f"\nAll results saved to {DB}")
print("Done!")
