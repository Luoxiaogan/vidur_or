"""
Per-segment Gate rate sweep: W3/W1/W2 workloads.
Extends r=12-36 with correct config space for per-seg gate.
Results to SQL table: rate_sweep_perseg

Config space based on discovered patterns:
  - Low rate: cs=192 tl=20
  - Mid rate: cs=192 tl=26 or cs=128 tl=30
  - High rate: cs=128 tl=30-40, cs=96 tl=35-50
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
cn.execute("""CREATE TABLE IF NOT EXISTS rate_sweep_perseg (
    timestamp TEXT, workload TEXT, algorithm TEXT, config_name TEXT,
    arrival_rate REAL, total_limit INT, chunk_size INT, seg_margin REAL,
    nreq INT, mean_latency REAL, p99_latency REAL, n_steady INT
)""")
cn.commit()

NREQ = 5000

# Workload definitions
WORKLOADS = {
    "W3": {
        "types": [
            {"type": "short", "prefill": 512, "decode": 20, "arrival_rate_frac": 0.7},
            {"type": "long",  "prefill": 512, "decode": 50, "arrival_rate_frac": 0.3},
        ],
        "max_tokens": 562,
        "rates": list(range(12, 37)),
    },
    "W1": {
        "types": [
            {"type": "short", "prefill": 256, "decode": 10, "arrival_rate_frac": 0.7},
            {"type": "long",  "prefill": 512, "decode": 50, "arrival_rate_frac": 0.3},
        ],
        "max_tokens": 562,
        "rates": [12, 14, 16, 18, 20, 22, 24, 28, 32],
    },
    "W2": {
        "types": [
            {"type": "short", "prefill": 256, "decode": 20, "arrival_rate_frac": 0.7},
            {"type": "long",  "prefill": 512, "decode": 40, "arrival_rate_frac": 0.3},
        ],
        "max_tokens": 552,
        "rates": [12, 14, 16, 18, 20, 22, 24, 28, 32],
    },
}

# Per-seg gate configs to test
# W3 (same prefill 512): cs=192/128/96/64 covers K=3-8
# W1/W2 (mixed prefill 256+512): cs=256 key — short K=1 (no penalty), long K=2 (75% savings)
WCP_CONFIGS = [
    {"name": "cs256_tl15", "cs": 256, "tl": 15, "sm": 0.0},
    {"name": "cs256_tl20", "cs": 256, "tl": 20, "sm": 0.0},
    {"name": "cs256_tl25", "cs": 256, "tl": 25, "sm": 0.0},
    {"name": "cs256_tl30", "cs": 256, "tl": 30, "sm": 0.0},
    {"name": "cs192_tl20", "cs": 192, "tl": 20, "sm": 0.0},
    {"name": "cs192_tl26", "cs": 192, "tl": 26, "sm": 0.0},
    {"name": "cs128_tl30", "cs": 128, "tl": 30, "sm": 0.0},
    {"name": "cs128_tl35", "cs": 128, "tl": 35, "sm": 0.0},
    {"name": "cs128_tl40", "cs": 128, "tl": 40, "sm": 0.0},
    {"name": "cs96_tl35",  "cs": 96,  "tl": 35, "sm": 0.0},
    {"name": "cs96_tl40",  "cs": 96,  "tl": 40, "sm": 0.0},
    {"name": "cs96_tl50",  "cs": 96,  "tl": 50, "sm": 0.0},
    {"name": "cs64_tl40",  "cs": 64,  "tl": 40, "sm": 0.0},
    {"name": "cs64_tl50",  "cs": 64,  "tl": 50, "sm": 0.0},
]


def already_done(workload, algorithm, config_name, rate):
    """Check if this (workload, algorithm, config, rate) combo exists in DB."""
    r = cn.execute(
        "SELECT 1 FROM rate_sweep_perseg WHERE workload=? AND algorithm=? AND config_name=? AND arrival_rate=? LIMIT 1",
        (workload, algorithm, config_name, rate)
    ).fetchone()
    return r is not None


def run_sim(extra_args, nreq=NREQ, gate=True):
    tmpdir = tempfile.mkdtemp(prefix="vidur_psg_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on" if gate else "off"
    cmd = COMMON + [
        "--custom_request_generator_config_num_requests", str(nreq),
        "--metrics_config_output_dir", tmpdir,
    ] + extra_args
    result = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=1800, env=env, text=True)
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
    return s["request_e2e_time"].mean(), s["request_e2e_time"].quantile(0.99), len(s)


def make_prompt_types(wl_def, rate):
    return json.dumps([
        {"type": t["type"], "prefill": t["prefill"], "decode": t["decode"],
         "arrival_rate": round(rate * t["arrival_rate_frac"], 2)}
        for t in wl_def["types"]
    ])


# Select workload from argv (default: W3)
target_wl = sys.argv[1] if len(sys.argv) > 1 else "W3"
if target_wl not in WORKLOADS:
    print(f"Unknown workload: {target_wl}. Options: {list(WORKLOADS.keys())}")
    sys.exit(1)

wl_def = WORKLOADS[target_wl]
print(f"=== {target_wl}: {[t['type']+' p'+str(t['prefill'])+'d'+str(t['decode']) for t in wl_def['types']]} ===", flush=True)

for rate in wl_def["rates"]:
    pt = make_prompt_types(wl_def, rate)

    # --- Sarathi baseline ---
    if already_done(target_wl, "sarathi", "Sarathi512", rate):
        row = cn.execute(
            "SELECT mean_latency FROM rate_sweep_perseg WHERE workload=? AND algorithm='sarathi' AND arrival_rate=?",
            (target_wl, rate)
        ).fetchone()
        sar_m = row[0]
        line = f"r={rate:2d} Sar={sar_m:.3f}s [cached]"
    else:
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", str(wl_def["max_tokens"]),
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ], gate=False)
        if res:
            m, p99, n = res
            cn.execute("INSERT INTO rate_sweep_perseg VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (datetime.now().isoformat(), target_wl, "sarathi", "Sarathi512",
                        rate, None, 512, 0, NREQ, m, p99, n))
            cn.commit()
            sar_m = m
            line = f"r={rate:2d} Sar={m:.3f}s"
        else:
            print(f"r={rate:2d} Sarathi FAIL", flush=True)
            continue

    # --- WCP per-seg gate configs ---
    best_gap = 999
    best_name = ""
    for cfg in WCP_CONFIGS:
        if already_done(target_wl, "wait_cp_perseg", cfg["name"], rate):
            row = cn.execute(
                "SELECT mean_latency FROM rate_sweep_perseg WHERE workload=? AND config_name=? AND arrival_rate=?",
                (target_wl, cfg["name"], rate)
            ).fetchone()
            m = row[0]
            g = (m - sar_m) / sar_m * 100
            if g < best_gap:
                best_gap = g
                best_name = cfg["name"]
            continue

        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", str(wl_def["max_tokens"]),
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", str(cfg["tl"]),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", str(cfg["cs"]),
            "--general_nested_chunked_scheduler_config_seg_margin", str(cfg["sm"]),
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate",
        ], gate=True)
        if res:
            m, p99, n = res
            g = (m - sar_m) / sar_m * 100
            cn.execute("INSERT INTO rate_sweep_perseg VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                       (datetime.now().isoformat(), target_wl, "wait_cp_perseg", cfg["name"],
                        rate, cfg["tl"], cfg["cs"], cfg["sm"], NREQ, m, p99, n))
            cn.commit()
            mk = " WIN" if g < -1 else ""
            if g < best_gap:
                best_gap = g
                best_name = cfg["name"]
        else:
            pass  # skip fails silently

    if best_gap < 999:
        mk = "WIN" if best_gap < -1 else "LOSE"
        line += f"  best={best_name} {best_gap:+.1f}% {mk}"
    print(line, flush=True)

cn.close()
print(f"\n{target_wl} Done!")
