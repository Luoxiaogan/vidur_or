"""
Long decode experiment: R2-4.6 (output > 1000 tokens).
Two workloads: p128d1000, p64d2000.
Phase 1: Grid search (cs, tl) at a mid-rate
Phase 2: Rate sweep with best config + baselines
"""
import subprocess, json, pandas as pd, os, shutil, glob, sqlite3, tempfile, sys
from datetime import datetime

PROJECT = "/persistent/vidur_or"
DB = f"{PROJECT}/experiments.db"
OUTDIR = f"{PROJECT}/outputs/timeseries"

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
cn.execute("""CREATE TABLE IF NOT EXISTS long_decode (
    timestamp TEXT, workload TEXT, algorithm TEXT, config_name TEXT,
    arrival_rate REAL, total_limit INT, chunk_size INT,
    nreq INT, mean_latency REAL, p99_latency REAL, n_steady INT
)""")
cn.commit()

WORKLOADS = {
    "p128d1000": {"prefill": 128, "decode": 1000, "max_tokens": 1128},
    "p64d2000":  {"prefill": 64,  "decode": 2000, "max_tokens": 2064},
}


def run_sim(extra_args, nreq, gate=True):
    tmpdir = tempfile.mkdtemp(prefix="vidur_ld_")
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


def already_done(workload, algorithm, config_name, rate):
    r = cn.execute(
        "SELECT 1 FROM long_decode WHERE workload=? AND algorithm=? AND config_name=? AND arrival_rate=? LIMIT 1",
        (workload, algorithm, config_name, rate)).fetchone()
    return r is not None


for wl_name, wl in WORKLOADS.items():
    l0, l1, max_tok = wl["prefill"], wl["decode"], wl["max_tokens"]
    pt = json.dumps([{"type": "only", "prefill": l0, "decode": l1, "arrival_rate": 1}])  # rate placeholder

    print(f"\n{'='*60}")
    print(f"Workload: {wl_name} (l0={l0}, l1={l1})")
    print(f"{'='*60}")

    # ---- Phase 1: Grid search at probe rate ----
    # Estimate reasonable rate: with long decode, throughput is low
    # pipeline = K + l1, P = tl/pipeline < 1
    # Try a few probe rates to find the stable region first
    print("\n--- Phase 1: Probe rates with Sarathi ---", flush=True)
    probe_nreq = 2000
    for rate in [1, 2, 3, 4, 5, 6, 8, 10]:
        pt_r = json.dumps([{"type": "only", "prefill": l0, "decode": l1, "arrival_rate": rate}])
        if already_done(wl_name, "sarathi", "Sarathi512", rate):
            row = cn.execute("SELECT mean_latency FROM long_decode WHERE workload=? AND algorithm='sarathi' AND arrival_rate=?",
                             (wl_name, rate)).fetchone()
            print(f"  Sar r={rate}: {row[0]:.3f}s [cached]", flush=True)
            continue
        res = run_sim([
            "--custom_request_generator_config_prompt_types", pt_r,
            "--custom_request_generator_config_max_tokens", str(max_tok),
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ], probe_nreq, gate=False)
        if res:
            cn.execute("INSERT INTO long_decode VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                       (datetime.now().isoformat(), wl_name, "sarathi", "Sarathi512",
                        rate, None, 512, probe_nreq, res[0], res[1], res[2]))
            cn.commit()
            print(f"  Sar r={rate}: {res[0]:.3f}s", flush=True)
        else:
            print(f"  Sar r={rate}: FAIL", flush=True)

    # Find a mid-rate where Sarathi is stable but not trivial
    sar_data = cn.execute(
        "SELECT arrival_rate, mean_latency FROM long_decode WHERE workload=? AND algorithm='sarathi' ORDER BY arrival_rate",
        (wl_name,)).fetchall()
    # Pick rate where Sarathi latency is moderate (2-10s range)
    mid_rate = None
    for r, lat in sar_data:
        if 1.0 < lat < 10.0:
            mid_rate = r
    if mid_rate is None and sar_data:
        mid_rate = sar_data[len(sar_data)//2][0]  # fallback: median rate
    if mid_rate is None:
        mid_rate = 3
    print(f"\nGrid search rate: {mid_rate}", flush=True)

    # ---- Phase 1b: Grid search WCP configs ----
    print(f"\n--- Phase 1b: WCP grid search at r={mid_rate} ---", flush=True)
    pt_mid = json.dumps([{"type": "only", "prefill": l0, "decode": l1, "arrival_rate": mid_rate}])

    # cs options: must be <= l0 for chunking benefit, or = l0 for no chunking
    cs_options = [c for c in [32, 64, 128] if c <= l0] + [l0]
    cs_options = sorted(set(cs_options))

    # tl: pipeline = ceil(l0/cs) + l1, need P = tl/pipeline in [0.8, 0.99]
    best_gap = 999
    best_cfg = None

    for cs in cs_options:
        K = max(1, -(-l0 // cs))  # ceil division
        pipeline = K + l1
        for P_target in [0.85, 0.90, 0.95, 0.98]:
            tl = max(2, int(P_target * pipeline))
            cfg_name = f"cs{cs}_tl{tl}"
            if already_done(wl_name, "wcp_grid", cfg_name, mid_rate):
                row = cn.execute("SELECT mean_latency FROM long_decode WHERE workload=? AND config_name=? AND arrival_rate=?",
                                 (wl_name, cfg_name, mid_rate)).fetchone()
                lat = row[0]
            else:
                res = run_sim([
                    "--custom_request_generator_config_prompt_types", pt_mid,
                    "--custom_request_generator_config_max_tokens", str(max_tok),
                    "--replica_scheduler_config_type", "general_nested_chunked",
                    "--general_nested_chunked_scheduler_config_prompt_types", pt_mid,
                    "--general_nested_chunked_scheduler_config_total_limit", str(tl),
                    "--general_nested_chunked_scheduler_config_total_num_requests", str(probe_nreq),
                    "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
                    "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
                    "--general_nested_chunked_scheduler_config_force_clear",
                    "--no-general_nested_chunked_scheduler_config_wait_gate",
                ], probe_nreq, gate=True)
                if not res:
                    print(f"  {cfg_name}: FAIL", flush=True)
                    continue
                lat = res[0]
                cn.execute("INSERT INTO long_decode VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (datetime.now().isoformat(), wl_name, "wcp_grid", cfg_name,
                            mid_rate, tl, cs, probe_nreq, res[0], res[1], res[2]))
                cn.commit()

            sar_lat = cn.execute("SELECT mean_latency FROM long_decode WHERE workload=? AND algorithm='sarathi' AND arrival_rate=?",
                                 (wl_name, mid_rate)).fetchone()[0]
            gap = (lat - sar_lat) / sar_lat * 100
            mk = "WIN" if gap < -1 else ""
            print(f"  {cfg_name} (K={K} P={tl/pipeline:.2f}): {lat:.3f}s ({gap:+.1f}%) {mk}", flush=True)
            if gap < best_gap:
                best_gap = gap
                best_cfg = {"cs": cs, "tl": tl, "name": cfg_name}

    if best_cfg:
        print(f"\nBest config: {best_cfg['name']} ({best_gap:+.1f}%)")
    else:
        print("\nNo WCP config found!")
        continue

    # ---- Phase 2: Rate sweep with best config ----
    print(f"\n--- Phase 2: Rate sweep ({wl_name}) ---", flush=True)
    rates = sorted(set([r for r, _ in sar_data]))
    nreq_sweep = 5000

    for rate in rates:
        pt_r = json.dumps([{"type": "only", "prefill": l0, "decode": l1, "arrival_rate": rate}])
        sar = cn.execute("SELECT mean_latency FROM long_decode WHERE workload=? AND algorithm='sarathi' AND arrival_rate=?",
                         (wl_name, rate)).fetchone()
        sar_lat = sar[0] if sar else None

        # vLLM
        if not already_done(wl_name, "vllm", "vLLM", rate):
            res = run_sim([
                "--custom_request_generator_config_prompt_types", pt_r,
                "--custom_request_generator_config_max_tokens", str(max_tok),
                "--replica_scheduler_config_type", "vllm",
            ], probe_nreq, gate=False)
            if res:
                cn.execute("INSERT INTO long_decode VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (datetime.now().isoformat(), wl_name, "vllm", "vLLM",
                            rate, None, 0, probe_nreq, res[0], res[1], res[2]))
                cn.commit()

        # WCP best
        cfg = best_cfg
        if not already_done(wl_name, "wcp_best", cfg["name"], rate):
            res = run_sim([
                "--custom_request_generator_config_prompt_types", pt_r,
                "--custom_request_generator_config_max_tokens", str(max_tok),
                "--replica_scheduler_config_type", "general_nested_chunked",
                "--general_nested_chunked_scheduler_config_prompt_types", pt_r,
                "--general_nested_chunked_scheduler_config_total_limit", str(cfg["tl"]),
                "--general_nested_chunked_scheduler_config_total_num_requests", str(nreq_sweep),
                "--general_nested_chunked_scheduler_config_chunk_size", str(cfg["cs"]),
                "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
                "--general_nested_chunked_scheduler_config_force_clear",
                "--no-general_nested_chunked_scheduler_config_wait_gate",
            ], probe_nreq, gate=True)
            if res:
                cn.execute("INSERT INTO long_decode VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (datetime.now().isoformat(), wl_name, "wcp_best", cfg["name"],
                            rate, cfg["tl"], cfg["cs"], probe_nreq, res[0], res[1], res[2]))
                cn.commit()

        # Print summary for this rate
        row_v = cn.execute("SELECT mean_latency FROM long_decode WHERE workload=? AND algorithm='vllm' AND arrival_rate=?",
                           (wl_name, rate)).fetchone()
        row_w = cn.execute("SELECT mean_latency FROM long_decode WHERE workload=? AND algorithm='wcp_best' AND arrival_rate=?",
                           (wl_name, rate)).fetchone()
        line = f"  r={rate}"
        if sar_lat:
            line += f" Sar={sar_lat:.3f}s"
        if row_v:
            line += f" vLLM={row_v[0]:.3f}s"
        if row_w and sar_lat:
            gap = (row_w[0] - sar_lat) / sar_lat * 100
            mk = "WIN" if gap < -1 else "LOSE"
            line += f" WCP={row_w[0]:.3f}s ({gap:+.1f}% {mk})"
        print(line, flush=True)

cn.close()
print("\nDone!")
