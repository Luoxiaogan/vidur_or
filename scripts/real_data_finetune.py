"""Real data binned: high QPS + large tl + bins sweep."""
import subprocess, json, pandas as pd, os, shutil, glob, tempfile

PROJECT = "/persistent/vidur_or"
COMMON = [
    "python", "-m", "vidur.main",
    "--replica_config_device", "a100", "--replica_config_model_name", "meta-llama/Meta-Llama-3-8B",
    "--replica_config_memory_margin_fraction", "0.1", "--cluster_config_num_replicas", "1",
    "--replica_config_tensor_parallel_size", "1", "--replica_config_num_pipeline_stages", "1",
    "--request_generator_config_type", "custom",
    "--no-metrics_config_store_plots",
    "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size", "16384",
    "--random_forrest_execution_time_predictor_config_prediction_max_batch_size", "2048",
    "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request", "65536",
]
df = pd.read_csv('data/processed_traces/sample_2e5_input<200_output<500.csv')
NREQ = 5000

def make_bins(qps, nbins):
    seg_size = 500 // nbins
    types = []
    for i in range(nbins):
        lo, hi = i*seg_size+1, (i+1)*seg_size
        mask = (df.num_decode_tokens >= lo) & (df.num_decode_tokens <= hi)
        sub = df[mask]
        if len(sub) == 0:
            continue
        types.append({"type": f"d{hi}", "prefill": max(1, int(sub.num_prefill_tokens.mean())),
                       "decode": hi, "arrival_rate": round(qps * len(sub) / len(df), 2)})
    return types

def run_wcp(qps, tl, nbins):
    pt = json.dumps(make_bins(qps, nbins))
    tmpdir = tempfile.mkdtemp(prefix="vidur_rdf_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on"
    cmd = COMMON + [
        "--custom_request_generator_config_prompt_types", pt,
        "--custom_request_generator_config_max_tokens", "539",
        "--custom_request_generator_config_num_requests", str(NREQ),
        "--metrics_config_output_dir", tmpdir,
        "--replica_scheduler_config_type", "general_nested_chunked",
        "--general_nested_chunked_scheduler_config_prompt_types", pt,
        "--general_nested_chunked_scheduler_config_total_limit", str(tl),
        "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
        "--general_nested_chunked_scheduler_config_chunk_size", "32",
        "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
        "--general_nested_chunked_scheduler_config_force_clear",
        "--no-general_nested_chunked_scheduler_config_wait_gate",
    ]
    r = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=1800, env=env, text=True)
    csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
    if csvs:
        rdf = pd.read_csv(csvs[0])
        s = rdf.iloc[len(rdf)//4:]
        lat = s["request_e2e_time"].mean()
        shutil.rmtree(tmpdir, ignore_errors=True)
        return lat
    shutil.rmtree(tmpdir, ignore_errors=True)
    return None

SAR = {55: 5.6, 80: 18.0, 100: 25.3}

for qps in [55, 80, 100]:
    sar = SAR[qps]
    print(f"\nQPS={qps} Sar={sar}s:", flush=True)
    for nbins in [10, 20, 50]:
        for tl in [400, 500, 600, 800, 1000]:
            lat = run_wcp(qps, tl, nbins)
            if lat:
                gap = (lat - sar) / sar * 100
                if gap < 5:
                    print(f"  {nbins:2d}bins tl={tl:4d}: {lat:.1f}s ({gap:+.1f}%){'  WIN' if gap < -1 else ''}", flush=True)

print("\nDone!", flush=True)
