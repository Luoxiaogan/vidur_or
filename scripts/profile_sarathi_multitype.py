"""
Profile Sarathi for B2 2-type workload across all rates.
Records per-type e2e, scheduling delay, execution time to SQL.
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
cn.execute("""CREATE TABLE IF NOT EXISTS profile_multitype (
    timestamp TEXT, algorithm TEXT, arrival_rate REAL, total_limit INT,
    chunk_size INT, seg_margin REAL, workload TEXT, nreq INT,
    type_name TEXT, prefill INT, decode INT,
    n INT, e2e_mean REAL, exec_mean REAL, sched_delay_mean REAL,
    preemption_mean REAL, e2e_p99 REAL
)""")
cn.commit()

NREQ = 5000
MAX_TOKENS = 562
RATES = [26, 28, 30, 32, 34, 36, 38, 40]

for total_rate in RATES:
    r1 = round(total_rate * 0.7, 1)
    r2 = round(total_rate * 0.3, 1)
    pt = json.dumps([
        {"type": "short", "prefill": 256, "decode": 10, "arrival_rate": r1},
        {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": r2},
    ])

    print(f"r={total_rate} Sarathi...", end=" ", flush=True)
    tmpdir = tempfile.mkdtemp(prefix="vidur_prof_")
    env = os.environ.copy()
    cmd = COMMON + [
        "--custom_request_generator_config_max_tokens", str(MAX_TOKENS),
        "--custom_request_generator_config_num_requests", str(NREQ),
        "--metrics_config_output_dir", tmpdir,
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--sarathi_scheduler_config_batch_size_cap", "512",
    ]
    result = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=1800, env=env, text=True)
    if result.returncode != 0:
        print(f"FAIL (exit={result.returncode})", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        continue

    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if not csvs:
        print("FAIL (no CSV)", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        continue

    df = pd.read_csv(csvs[0])
    shutil.rmtree(tmpdir, ignore_errors=True)
    s = df.iloc[len(df) // 4:max(len(df) // 4 + 1, len(df) - 500)]

    ts = datetime.now().isoformat()
    # 按 type 记录
    for pt_val in sorted(s.request_num_prefill_tokens.unique()):
        sub = s[s.request_num_prefill_tokens == pt_val]
        dec_val = sub.request_num_decode_tokens.median()
        type_name = f"p{int(pt_val)}_d{int(dec_val)}"
        cn.execute(
            "INSERT INTO profile_multitype VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ts, "sarathi", total_rate, None, 512, 0, "b2_profile", NREQ,
             type_name, int(pt_val), int(dec_val), len(sub),
             sub.request_e2e_time.mean(), sub.request_execution_time.mean(),
             sub.request_scheduling_delay.mean(), sub.request_preemption_time.mean(),
             sub.request_e2e_time.quantile(0.99)))
    # 总体
    cn.execute(
        "INSERT INTO profile_multitype VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ts, "sarathi", total_rate, None, 512, 0, "b2_profile", NREQ,
         "ALL", 0, 0, len(s),
         s.request_e2e_time.mean(), s.request_execution_time.mean(),
         s.request_scheduling_delay.mean(), s.request_preemption_time.mean(),
         s.request_e2e_time.quantile(0.99)))
    cn.commit()

    sar_short = s[s.request_num_prefill_tokens == 256]
    sar_long = s[s.request_num_prefill_tokens == 512]
    print(f"ALL={s.request_e2e_time.mean():.3f}s  "
          f"short(p256d10)={sar_short.request_e2e_time.mean():.3f}s(sched={sar_short.request_scheduling_delay.mean():.4f}s)  "
          f"long(p512d50)={sar_long.request_e2e_time.mean():.3f}s(sched={sar_long.request_scheduling_delay.mean():.4f}s)", flush=True)

cn.close()
print(f"\nAll saved to {DB} table profile_multitype")
