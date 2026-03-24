"""
Profile Sarathi + WCP (no-WAIT) for B2 2-type workload.
Records per-type e2e, scheduling delay, execution time to SQL.
"""
import subprocess, json, pandas as pd, os, shutil, glob, sqlite3, tempfile
from math import ceil
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


def run_and_profile(extra_args, gate="on"):
    tmpdir = tempfile.mkdtemp(prefix="vidur_prof_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = gate
    cmd = COMMON + [
        "--custom_request_generator_config_max_tokens", str(MAX_TOKENS),
        "--custom_request_generator_config_num_requests", str(NREQ),
        "--metrics_config_output_dir", tmpdir,
    ] + extra_args
    result = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=1800, env=env, text=True)
    if result.returncode != 0:
        err = (result.stderr or "").strip().split("\n")[-1]
        print(f"    [ERR] {err}", flush=True)
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if not csvs:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    df = pd.read_csv(csvs[0])
    shutil.rmtree(tmpdir, ignore_errors=True)
    # 掐头 25%, 去尾 500
    s = df.iloc[len(df) // 4:max(len(df) // 4 + 1, len(df) - 500)]
    return s


def record_profile(alg, rate, tl, cs, sm, workload, df_steady):
    ts = datetime.now().isoformat()
    # 按 prefill token 分 type
    for pt_val in sorted(df_steady.request_num_prefill_tokens.unique()):
        sub = df_steady[df_steady.request_num_prefill_tokens == pt_val]
        dec_val = sub.request_num_decode_tokens.median()
        type_name = f"p{int(pt_val)}_d{int(dec_val)}"
        cn.execute(
            "INSERT INTO profile_multitype VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ts, alg, rate, tl, cs, sm, workload, NREQ,
             type_name, int(pt_val), int(dec_val),
             len(sub),
             sub.request_e2e_time.mean(),
             sub.request_execution_time.mean(),
             sub.request_scheduling_delay.mean(),
             sub.request_preemption_time.mean(),
             sub.request_e2e_time.quantile(0.99)))
    # 也记录总体
    cn.execute(
        "INSERT INTO profile_multitype VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (ts, alg, rate, tl, cs, sm, workload, NREQ,
         "ALL", 0, 0, len(df_steady),
         df_steady.request_e2e_time.mean(),
         df_steady.request_execution_time.mean(),
         df_steady.request_scheduling_delay.mean(),
         df_steady.request_preemption_time.mean(),
         df_steady.request_e2e_time.quantile(0.99)))
    cn.commit()


# ========================================================
# B2: 2-type workload
# ========================================================
RATES = [12, 14, 16, 18, 20, 22, 24]

for total_rate in RATES:
    r1 = round(total_rate * 0.7, 1)
    r2 = round(total_rate * 0.3, 1)
    pt = json.dumps([
        {"type": "short", "prefill": 256, "decode": 10, "arrival_rate": r1},
        {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": r2},
    ])

    # --- Sarathi(512) ---
    print(f"r={total_rate} Sarathi...", end=" ", flush=True)
    df = run_and_profile([
        "--custom_request_generator_config_prompt_types", pt,
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--sarathi_scheduler_config_batch_size_cap", "512",
    ])
    if df is not None:
        record_profile("sarathi", total_rate, None, 512, 0, "b2_profile", df)
        sar_all = df.request_e2e_time.mean()
        sar_short = df[df.request_num_prefill_tokens == 256].request_e2e_time.mean()
        sar_long = df[df.request_num_prefill_tokens == 512].request_e2e_time.mean()
        print(f"ALL={sar_all:.3f}s  short={sar_short:.3f}s  long={sar_long:.3f}s", flush=True)
    else:
        print("FAIL", flush=True)
        continue

    # --- WCP (no-WAIT, free flow) sweep ---
    wcp_configs = [
        (20, 256, 0.0), (30, 256, 0.0), (40, 256, 0.0), (50, 256, 0.0), (60, 256, 0.0),
        (30, 256, 0.2), (40, 256, 0.2), (50, 256, 0.2),
        (30, 256, 0.3), (40, 256, 0.3), (50, 256, 0.3),
    ]
    for tl, cs, sm in wcp_configs:
        print(f"r={total_rate} WCP(tl={tl},cs={cs},sm={sm})...", end=" ", flush=True)
        df = run_and_profile([
            "--custom_request_generator_config_prompt_types", pt,
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", str(tl),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
            "--general_nested_chunked_scheduler_config_seg_margin", str(sm),
            "--general_nested_chunked_scheduler_config_force_clear",
        ])
        if df is not None:
            record_profile("wait_cp_nowait", total_rate, tl, cs, sm, "b2_profile", df)
            w_all = df.request_e2e_time.mean()
            w_short = df[df.request_num_prefill_tokens == 256].request_e2e_time.mean()
            w_long = df[df.request_num_prefill_tokens == 512].request_e2e_time.mean()
            g = (w_all - sar_all) / sar_all * 100
            mk = "WIN" if g < -1 else ""
            print(f"ALL={w_all:.3f}s({g:+.1f}%)  short={w_short:.3f}s  long={w_long:.3f}s {mk}", flush=True)
        else:
            print("FAIL", flush=True)

cn.close()
print(f"\nAll results saved to {DB}")
print("Done!")
