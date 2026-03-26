"""
Multi-seed verification at critical rates.
Runs 5 seeds for Sarathi/vLLM/WCP at r=22,23 (single+multi).
"""
import subprocess, json, pandas as pd, os, shutil, glob, tempfile, sqlite3
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

NREQ = 10000
SEEDS = [42, 123, 456, 789, 1024]

cn = sqlite3.connect(DB)
cn.execute("""CREATE TABLE IF NOT EXISTS multi_seed (
    timestamp TEXT, workload TEXT, algorithm TEXT, config_name TEXT,
    arrival_rate REAL, seed INT, nreq INT, mean_latency REAL, p99_latency REAL, n_steady INT
)""")
cn.commit()


def already_done(workload, algorithm, rate, seed):
    r = cn.execute(
        "SELECT 1 FROM multi_seed WHERE workload=? AND algorithm=? AND arrival_rate=? AND seed=? LIMIT 1",
        (workload, algorithm, rate, seed)).fetchone()
    return r is not None


def run_sim(extra_args, nreq, gate, seed):
    tmpdir = tempfile.mkdtemp(prefix="vidur_ms_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on" if gate else "off"
    cmd = COMMON + [
        "--custom_request_generator_config_num_requests", str(nreq),
        "--custom_request_generator_config_seed", str(seed),
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


for rate in [22, 23]:
    for wl_name, pt_func, max_tok, wcp_args in [
        ("single", lambda r: json.dumps([{"type": "only", "prefill": 512, "decode": 20, "arrival_rate": r}]),
         532, lambda pt: [
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", "21",
            "--general_nested_chunked_scheduler_config_chunk_size", "256",
         ]),
        ("multi_W3", lambda r: json.dumps([
            {"type": "short", "prefill": 512, "decode": 20, "arrival_rate": round(r * 0.7, 2)},
            {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": round(r * 0.3, 2)},
        ]), 562, lambda pt: [
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", "30",
            "--general_nested_chunked_scheduler_config_chunk_size", "128",
         ]),
    ]:
        pt = pt_func(rate)
        print(f"\n=== {wl_name} r={rate} ===", flush=True)

        for seed in SEEDS:
            # Sarathi
            if not already_done(wl_name, "sarathi", rate, seed):
                res = run_sim([
                    "--custom_request_generator_config_prompt_types", pt,
                    "--custom_request_generator_config_max_tokens", str(max_tok),
                    "--replica_scheduler_config_type", "sarathi",
                    "--sarathi_scheduler_config_chunk_size", "512",
                    "--sarathi_scheduler_config_batch_size_cap", "512",
                ], NREQ, False, seed)
                if res:
                    cn.execute("INSERT INTO multi_seed VALUES(?,?,?,?,?,?,?,?,?,?)",
                               (datetime.now().isoformat(), wl_name, "sarathi", "Sarathi512",
                                rate, seed, NREQ, res[0], res[1], res[2]))
                    cn.commit()

            # vLLM
            if not already_done(wl_name, "vllm", rate, seed):
                res = run_sim([
                    "--custom_request_generator_config_prompt_types", pt,
                    "--custom_request_generator_config_max_tokens", str(max_tok),
                    "--replica_scheduler_config_type", "vllm",
                ], NREQ, False, seed)
                if res:
                    cn.execute("INSERT INTO multi_seed VALUES(?,?,?,?,?,?,?,?,?,?)",
                               (datetime.now().isoformat(), wl_name, "vllm", "vLLM",
                                rate, seed, NREQ, res[0], res[1], res[2]))
                    cn.commit()

            # WCP
            if not already_done(wl_name, "wcp", rate, seed):
                res = run_sim([
                    "--custom_request_generator_config_prompt_types", pt,
                    "--custom_request_generator_config_max_tokens", str(max_tok),
                    "--replica_scheduler_config_type", "general_nested_chunked",
                    "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
                    "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
                    "--general_nested_chunked_scheduler_config_force_clear",
                    "--no-general_nested_chunked_scheduler_config_wait_gate",
                ] + wcp_args(pt), NREQ, True, seed)
                if res:
                    cn.execute("INSERT INTO multi_seed VALUES(?,?,?,?,?,?,?,?,?,?)",
                               (datetime.now().isoformat(), wl_name, "wcp", "WCP",
                                rate, seed, NREQ, res[0], res[1], res[2]))
                    cn.commit()

            print(f"  seed={seed} done", flush=True)

# Print summary
print("\n=== Multi-seed Summary ===")
for wl in ["single", "multi_W3"]:
    for rate in [22, 23]:
        print(f"\n{wl} r={rate}:")
        for algo in ["sarathi", "vllm", "wcp"]:
            rows = cn.execute(
                "SELECT mean_latency FROM multi_seed WHERE workload=? AND algorithm=? AND arrival_rate=? ORDER BY seed",
                (wl, algo, rate)).fetchall()
            if rows:
                lats = [r[0] for r in rows]
                import statistics
                m = statistics.mean(lats)
                s = statistics.stdev(lats) if len(lats) > 1 else 0
                print(f"  {algo:8s}: {m:.3f}s ± {s:.3f}s  ({len(lats)} seeds)  [{', '.join(f'{l:.2f}' for l in lats)}]")

cn.close()
print("\nDone!")
