"""
Long decode exploration: p128d1000, single-type.
Compare: Sarathi, vLLM, GeneralNestedChunked (1-seg), UniformSegment (5-seg, 10-seg).
"""
import subprocess, json, pandas as pd, os, shutil, glob, sqlite3, tempfile
from datetime import datetime
from math import ceil

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
cn.execute("""CREATE TABLE IF NOT EXISTS long_decode_v2 (
    timestamp TEXT, workload TEXT, algorithm TEXT, config_name TEXT,
    arrival_rate REAL, total_limit INT, chunk_size INT, segment_size INT,
    nreq INT, mean_latency REAL, p99_latency REAL, n_steady INT
)""")
cn.commit()

L0, L1 = 128, 1000
MAX_TOK = L0 + L1
NREQ = 2000


def run_sim(extra_args, nreq=NREQ, gate=True):
    tmpdir = tempfile.mkdtemp(prefix="vidur_ld2_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on" if gate else "off"
    cmd = COMMON + [
        "--custom_request_generator_config_num_requests", str(nreq),
        "--metrics_config_output_dir", tmpdir,
    ] + extra_args
    result = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=3600, env=env, text=True)
    if result.returncode != 0:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if not csvs:
        shutil.rmtree(tmpdir, ignore_errors=True)
        return None
    df = pd.read_csv(csvs[0])
    shutil.rmtree(tmpdir, ignore_errors=True)
    start = len(df) // 4
    end = max(start + 1, len(df) - len(df) // 4)
    s = df.iloc[start:end]
    return s["request_e2e_time"].mean(), s["request_e2e_time"].quantile(0.99), len(s)


def done(wl, algo, cfg, rate):
    r = cn.execute("SELECT mean_latency FROM long_decode_v2 WHERE workload=? AND algorithm=? AND config_name=? AND arrival_rate=?",
                   (wl, algo, cfg, rate)).fetchone()
    return r[0] if r else None


def store(wl, algo, cfg, rate, tl, cs, seg_size, nreq, res):
    cn.execute("INSERT INTO long_decode_v2 VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
               (datetime.now().isoformat(), wl, algo, cfg, rate, tl, cs, seg_size, nreq, res[0], res[1], res[2]))
    cn.commit()


WL = "p128d1000"
RATES = [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]

# ============================================================
# Baselines: Sarathi + vLLM
# ============================================================
print("=== Baselines ===", flush=True)
for rate in RATES:
    pt = json.dumps([{"type": "only", "prefill": L0, "decode": L1, "arrival_rate": rate}])

    for algo, cfg_name, args in [
        ("sarathi", "Sarathi512", [
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ]),
        ("vllm", "vLLM", [
            "--replica_scheduler_config_type", "vllm",
        ]),
    ]:
        cached = done(WL, algo, cfg_name, rate)
        if cached:
            print(f"  {algo} r={rate:.1f}: {cached:.3f}s [cached]", flush=True)
            continue
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", str(MAX_TOK),
        ] + args, gate=False)
        if res:
            store(WL, algo, cfg_name, rate, None, None, None, NREQ, res)
            print(f"  {algo} r={rate:.1f}: {res[0]:.3f}s", flush=True)
        else:
            print(f"  {algo} r={rate:.1f}: FAIL", flush=True)

# Find mid_rate for grid search
sar_data = [(r, done(WL, "sarathi", "Sarathi512", r)) for r in RATES]
sar_data = [(r, l) for r, l in sar_data if l is not None]
mid_rate = 2.0
for r, lat in sar_data:
    if 2.0 < lat < 20.0:
        mid_rate = r
        break
print(f"\nGrid search rate: {mid_rate}", flush=True)

# ============================================================
# WCP-A: GeneralNestedChunked (1 segment, original)
# ============================================================
print("\n=== WCP-A: 1-segment (general_nested_chunked) ===", flush=True)
pt_mid = json.dumps([{"type": "only", "prefill": L0, "decode": L1, "arrival_rate": mid_rate}])

for cs in [64, 128]:
    for tl in [10, 15, 20, 25, 30, 40, 50]:
        cfg = f"A_cs{cs}_tl{tl}"
        cached = done(WL, "wcp_1seg", cfg, mid_rate)
        if cached is not None:
            sar = done(WL, "sarathi", "Sarathi512", mid_rate)
            gap = (cached - sar) / sar * 100 if sar else 0
            if gap < 5:
                print(f"  {cfg}: {cached:.3f}s ({gap:+.1f}%) [cached]", flush=True)
            continue
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt_mid,
            "--custom_request_generator_config_max_tokens", str(MAX_TOK),
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt_mid,
            "--general_nested_chunked_scheduler_config_total_limit", str(tl),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
            "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate",
        ])
        if res:
            store(WL, "wcp_1seg", cfg, mid_rate, tl, cs, None, NREQ, res)
            sar = done(WL, "sarathi", "Sarathi512", mid_rate)
            gap = (res[0] - sar) / sar * 100 if sar else 0
            mk = "WIN" if gap < -1 else ""
            print(f"  {cfg}: {res[0]:.3f}s ({gap:+.1f}%) {mk}", flush=True)
        else:
            print(f"  {cfg}: FAIL", flush=True)

# ============================================================
# WCP-B: UniformSegmentChunked (5-seg, 10-seg)
# ============================================================
for seg_size, seg_label in [(200, "5seg"), (100, "10seg"), (50, "20seg")]:
    num_seg = ceil(L1 / seg_size)
    print(f"\n=== WCP-B: {num_seg}-segment (uniform, seg_size={seg_size}) ===", flush=True)

    for cs in [64, 128]:
        for tl in [10, 15, 20, 25, 30, 40, 50]:
            cfg = f"B_{seg_label}_cs{cs}_tl{tl}"
            cached = done(WL, f"wcp_{seg_label}", cfg, mid_rate)
            if cached is not None:
                sar = done(WL, "sarathi", "Sarathi512", mid_rate)
                gap = (cached - sar) / sar * 100 if sar else 0
                if gap < 5:
                    print(f"  {cfg}: {cached:.3f}s ({gap:+.1f}%) [cached]", flush=True)
                continue
            res = run_sim([
                "--custom_request_generator_config_prompt_types", pt_mid,
                "--custom_request_generator_config_max_tokens", str(MAX_TOK),
                "--replica_scheduler_config_type", "uniform_segment_chunked",
                "--uniform_segment_chunked_scheduler_config_prompt_types", pt_mid,
                "--uniform_segment_chunked_scheduler_config_total_limit", str(tl),
                "--uniform_segment_chunked_scheduler_config_total_num_requests", str(NREQ),
                "--uniform_segment_chunked_scheduler_config_chunk_size", str(cs),
                "--uniform_segment_chunked_scheduler_config_segment_size", str(seg_size),
                "--uniform_segment_chunked_scheduler_config_seg_margin", "0.0",
                "--uniform_segment_chunked_scheduler_config_force_clear",
                "--no-uniform_segment_chunked_scheduler_config_wait_gate",
            ])
            if res:
                store(WL, f"wcp_{seg_label}", cfg, mid_rate, tl, cs, seg_size, NREQ, res)
                sar = done(WL, "sarathi", "Sarathi512", mid_rate)
                gap = (res[0] - sar) / sar * 100 if sar else 0
                mk = "WIN" if gap < -1 else ""
                print(f"  {cfg}: {res[0]:.3f}s ({gap:+.1f}%) {mk}", flush=True)
            else:
                print(f"  {cfg}: FAIL", flush=True)

# ============================================================
# Summary
# ============================================================
print("\n" + "=" * 60)
print("Summary at r=" + str(mid_rate))
print("=" * 60)

sar = done(WL, "sarathi", "Sarathi512", mid_rate)
vlm = done(WL, "vllm", "vLLM", mid_rate)
print(f"  Sarathi: {sar:.3f}s" if sar else "  Sarathi: N/A")
print(f"  vLLM:    {vlm:.3f}s" if vlm else "  vLLM: N/A")

for algo_prefix in ["wcp_1seg", "wcp_5seg", "wcp_10seg", "wcp_20seg"]:
    rows = cn.execute(
        "SELECT config_name, mean_latency FROM long_decode_v2 WHERE workload=? AND algorithm=? AND arrival_rate=? ORDER BY mean_latency LIMIT 3",
        (WL, algo_prefix, mid_rate)).fetchall()
    if rows:
        print(f"\n  {algo_prefix} top 3:")
        for name, lat in rows:
            gap = (lat - sar) / sar * 100 if sar else 0
            mk = "WIN" if gap < -1 else ""
            print(f"    {name}: {lat:.3f}s ({gap:+.1f}%) {mk}")

cn.close()
print("\nDone!")
