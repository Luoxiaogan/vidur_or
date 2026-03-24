"""
Overnight grid search: cs × tl × sm × rate × workload type
Tests multiple B2 workload variants + parameter combinations.
Results stored in experiments.db table: grid_multitype

Workloads:
  W1: p256d10(70%) + p512d50(30%)    — current B2
  W2: p256d20(70%) + p512d40(30%)    — closer decode lengths
  W3: p512d20(70%) + p512d50(30%)    — same prefill, different decode
  W4: p256d10(50%) + p512d50(50%)    — equal traffic split
  W5: p256d20(60%) + p512d30(40%)    — moderate heterogeneity
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
cn.execute("""CREATE TABLE IF NOT EXISTS grid_multitype (
    timestamp TEXT, workload TEXT, algorithm TEXT,
    arrival_rate REAL, total_limit INT, chunk_size INT, seg_margin REAL,
    wait_gate INT, nreq INT,
    mean_latency REAL, p99_latency REAL, n_steady INT
)""")
cn.commit()

NREQ = 2000  # fast mode


def run_sim(extra_args, gate="on", nreq=NREQ, max_tokens=562):
    tmpdir = tempfile.mkdtemp(prefix="vidur_grid_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = gate
    cmd = COMMON + [
        "--custom_request_generator_config_max_tokens", str(max_tokens),
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


def record(workload, alg, rate, tl, cs, sm, wg, m, p99, n):
    cn.execute(
        "INSERT INTO grid_multitype VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (datetime.now().isoformat(), workload, alg,
         rate, tl, cs, sm, wg, NREQ, m, p99, n))
    cn.commit()


# ========================================================
# Workload definitions
# ========================================================
WORKLOADS = {
    "W1_p256d10_p512d50_7030": {
        "types": [
            {"type": "short", "prefill": 256, "decode": 10},
            {"type": "long", "prefill": 512, "decode": 50},
        ],
        "split": [0.7, 0.3],
        "max_tokens": 562,
    },
    "W2_p256d20_p512d40_7030": {
        "types": [
            {"type": "short", "prefill": 256, "decode": 20},
            {"type": "long", "prefill": 512, "decode": 40},
        ],
        "split": [0.7, 0.3],
        "max_tokens": 552,
    },
    "W3_p512d20_p512d50_7030": {
        "types": [
            {"type": "short", "prefill": 512, "decode": 20},
            {"type": "long", "prefill": 512, "decode": 50},
        ],
        "split": [0.7, 0.3],
        "max_tokens": 562,
    },
    "W4_p256d10_p512d50_5050": {
        "types": [
            {"type": "short", "prefill": 256, "decode": 10},
            {"type": "long", "prefill": 512, "decode": 50},
        ],
        "split": [0.5, 0.5],
        "max_tokens": 562,
    },
    "W5_p256d20_p512d30_6040": {
        "types": [
            {"type": "short", "prefill": 256, "decode": 20},
            {"type": "long", "prefill": 512, "decode": 30},
        ],
        "split": [0.6, 0.4],
        "max_tokens": 542,
    },
}

# ========================================================
# Parameter grid
# ========================================================
RATES = [16, 20, 24, 30]
CS_LIST = [128, 256, 512]
TL_LIST = [15, 20, 25, 30, 40, 50]
SM_LIST = [-0.1, 0.0, 0.1, 0.2]

total_configs = len(WORKLOADS) * len(RATES) * (1 + len(CS_LIST) * len(TL_LIST) * len(SM_LIST))
print(f"Total configs: {total_configs} ({len(WORKLOADS)} workloads × {len(RATES)} rates × (1 Sarathi + {len(CS_LIST)*len(TL_LIST)*len(SM_LIST)} WCP))")
print(f"nreq={NREQ} (fast mode)")
print()

config_num = 0
for wname, wdef in WORKLOADS.items():
    print(f"\n{'='*60}")
    print(f"Workload: {wname}")
    print(f"{'='*60}")

    for total_rate in RATES:
        types_with_rates = []
        for i, t in enumerate(wdef["types"]):
            r = round(total_rate * wdef["split"][i], 1)
            types_with_rates.append({**t, "arrival_rate": r})
        pt = json.dumps(types_with_rates)
        max_tokens = wdef["max_tokens"]

        # --- Sarathi baseline ---
        config_num += 1
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt,
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ], nreq=NREQ, max_tokens=max_tokens)
        if res:
            m, p99, n = res
            record(wname, "sarathi", total_rate, None, 512, 0, 0, m, p99, n)
            sar_m = m
            print(f"[{config_num}] {wname} r={total_rate} Sarathi: {m:.3f}s", flush=True)
        else:
            print(f"[{config_num}] {wname} r={total_rate} Sarathi: FAIL", flush=True)
            continue

        # --- WCP grid ---
        for cs in CS_LIST:
            for tl in TL_LIST:
                for sm in SM_LIST:
                    config_num += 1
                    res = run_sim([
                        "--custom_request_generator_config_prompt_types", pt,
                        "--replica_scheduler_config_type", "general_nested_chunked",
                        "--general_nested_chunked_scheduler_config_prompt_types", pt,
                        "--general_nested_chunked_scheduler_config_total_limit", str(tl),
                        "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
                        "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
                        "--general_nested_chunked_scheduler_config_seg_margin", str(sm),
                        "--general_nested_chunked_scheduler_config_force_clear",
                        "--no-general_nested_chunked_scheduler_config_wait_gate",
                    ], nreq=NREQ, max_tokens=max_tokens)
                    if res:
                        m, p99, n_s = res
                        g = (m - sar_m) / sar_m * 100
                        mk = " WIN" if g < -1 else ""
                        record(wname, "wait_cp", total_rate, tl, cs, sm, 0, m, p99, n_s)
                        if g < 5 or mk:  # only print promising results
                            print(f"[{config_num}] r={total_rate} cs={cs:3d} tl={tl:2d} sm={sm:+.1f}: {m:.3f}s ({g:+.1f}%){mk}", flush=True)
                    else:
                        pass  # silent fail for grid search

print(f"\n{'='*60}")
print(f"All {config_num} configs done. Results in {DB} table grid_multitype")

# ========================================================
# Summary: best per workload × rate
# ========================================================
print(f"\n{'='*60}")
print("SUMMARY: Best WCP config per workload × rate")
print(f"{'='*60}")

df = pd.read_sql("SELECT * FROM grid_multitype WHERE algorithm='wait_cp' ORDER BY mean_latency", cn)
sar = pd.read_sql("SELECT * FROM grid_multitype WHERE algorithm='sarathi'", cn)

for wname in WORKLOADS:
    print(f"\n{wname}:")
    for rate in RATES:
        s_row = sar[(sar.workload == wname) & (sar.arrival_rate == rate)]
        if s_row.empty:
            continue
        s_m = s_row.iloc[0].mean_latency
        w_rows = df[(df.workload == wname) & (df.arrival_rate == rate)]
        if w_rows.empty:
            continue
        best = w_rows.iloc[0]
        g = (best.mean_latency - s_m) / s_m * 100
        mk = "WIN" if g < -1 else ""
        print(f"  r={rate}: Sar={s_m:.3f}s  WCP={best.mean_latency:.3f}s ({g:+.1f}%) "
              f"cs={int(best.chunk_size)} tl={int(best.total_limit)} sm={best.seg_margin:+.1f} {mk}")

cn.close()
print("\nDone!")
