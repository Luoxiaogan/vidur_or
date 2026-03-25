"""
Rate sweep for W3 (p512d20 + p512d50, 70/30) with best WCP configs.
r=12 to 36, step=1. Sarathi + 3 WCP configs.
Results to SQL table: rate_sweep_w3
"""
import subprocess, json, pandas as pd, os, shutil, glob, sqlite3, tempfile
from datetime import datetime

PROJECT = "/home/CPU/vidur_or"
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
cn.execute("""CREATE TABLE IF NOT EXISTS rate_sweep_w3 (
    timestamp TEXT, algorithm TEXT, config_name TEXT,
    arrival_rate REAL, total_limit INT, chunk_size INT, seg_margin REAL,
    nreq INT, mean_latency REAL, p99_latency REAL, n_steady INT
)""")
cn.commit()

NREQ = 5000
MAX_TOKENS = 562
RATES = list(range(12, 37))  # 12 to 36

# Best WCP configs from grid search
WCP_CONFIGS = [
    {"name": "WCP_cs256_tl25_sm0",   "cs": 256, "tl": 25, "sm": 0.0},
    {"name": "WCP_cs256_tl22_sm0",   "cs": 256, "tl": 22, "sm": 0.0},
    {"name": "WCP_cs256_tl25_sm-005", "cs": 256, "tl": 25, "sm": -0.05},
]


def run_sim(extra_args, nreq=NREQ):
    tmpdir = tempfile.mkdtemp(prefix="vidur_rs_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on"
    cmd = COMMON + [
        "--custom_request_generator_config_max_tokens", str(MAX_TOKENS),
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
    s = df.iloc[len(df) // 4:max(len(df) // 4 + 1, len(df) - 500)]
    return s["request_e2e_time"].mean(), s["request_e2e_time"].quantile(0.99), len(s)


for rate in RATES:
    r1 = round(rate * 0.7, 2)
    r2 = round(rate * 0.3, 2)
    pt = json.dumps([
        {"type": "short", "prefill": 512, "decode": 20, "arrival_rate": r1},
        {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": r2},
    ])

    # Sarathi
    res = run_sim([
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--sarathi_scheduler_config_batch_size_cap", "512",
    ])
    if res:
        m, p99, n = res
        cn.execute("INSERT INTO rate_sweep_w3 VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                   (datetime.now().isoformat(), "sarathi", "Sarathi512",
                    rate, None, 512, 0, NREQ, m, p99, n))
        cn.commit()
        sar_m = m
        line = f"r={rate:2d} Sar={m:.3f}s"
    else:
        print(f"r={rate:2d} Sarathi FAIL", flush=True)
        continue

    # WCP configs
    for cfg in WCP_CONFIGS:
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt,
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", str(cfg["tl"]),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", str(cfg["cs"]),
            "--general_nested_chunked_scheduler_config_seg_margin", str(cfg["sm"]),
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate",
        ])
        if res:
            m, p99, n = res
            g = (m - sar_m) / sar_m * 100
            cn.execute("INSERT INTO rate_sweep_w3 VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       (datetime.now().isoformat(), "wait_cp", cfg["name"],
                        rate, cfg["tl"], cfg["cs"], cfg["sm"], NREQ, m, p99, n))
            cn.commit()
            mk = "WIN" if g < -1 else ""
            line += f"  {cfg['name']}={m:.3f}s({g:+.1f}%){mk}"
        else:
            line += f"  {cfg['name']}=FAIL"

    print(line, flush=True)

cn.close()
print("\nDone!")
