"""High QPS real data: 50 bins workload, vary segment_size + tl."""
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

def make_50bins(qps):
    types = []
    for i in range(50):
        lo, hi = i*10+1, (i+1)*10
        mask = (df.num_decode_tokens >= lo) & (df.num_decode_tokens <= hi)
        sub = df[mask]
        if len(sub) == 0:
            continue
        types.append({"type": f"d{hi}", "prefill": max(1, int(sub.num_prefill_tokens.mean())),
                       "decode": hi, "arrival_rate": round(qps * len(sub) / len(df), 2)})
    return types

def run_sim(qps, sched_args, gate=True):
    pt = json.dumps(make_50bins(qps))
    tmpdir = tempfile.mkdtemp(prefix="vidur_hq2_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on" if gate else "off"
    cmd = COMMON + [
        "--custom_request_generator_config_prompt_types", pt,
        "--custom_request_generator_config_max_tokens", "539",
        "--custom_request_generator_config_num_requests", str(NREQ),
        "--metrics_config_output_dir", tmpdir,
    ] + sched_args
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

for qps in [80, 100]:
    pt = json.dumps(make_50bins(qps))

    # Sarathi baseline
    sar = run_sim(qps, [
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--sarathi_scheduler_config_batch_size_cap", "512"], gate=False)
    if not sar:
        print(f"QPS={qps}: Sarathi FAIL", flush=True)
        continue
    print(f"\nQPS={qps} Sar={sar:.1f}s (50 bins)", flush=True)

    # uniform_segment_chunked: vary segment_size (controls num segments)
    # segment_size=10 → 50 segs (same as bins), 50 → 10 segs, 100 → 5 segs, 250 → 2, 500 → 1
    for seg_size in [10, 25, 50, 100, 250, 500]:
        n_seg = 500 // seg_size
        for tl in [300, 400, 500, 600, 800]:
            lat = run_sim(qps, [
                "--replica_scheduler_config_type", "uniform_segment_chunked",
                "--uniform_segment_chunked_scheduler_config_prompt_types", pt,
                "--uniform_segment_chunked_scheduler_config_total_limit", str(tl),
                "--uniform_segment_chunked_scheduler_config_total_num_requests", str(NREQ),
                "--uniform_segment_chunked_scheduler_config_chunk_size", "32",
                "--uniform_segment_chunked_scheduler_config_segment_size", str(seg_size),
                "--uniform_segment_chunked_scheduler_config_seg_margin", "0.0",
                "--uniform_segment_chunked_scheduler_config_force_clear",
                "--no-uniform_segment_chunked_scheduler_config_wait_gate"])
            if lat:
                gap = (lat - sar) / sar * 100
                if gap < 3:
                    print(f"  {n_seg:2d}seg tl={tl:4d}: {lat:.1f}s ({gap:+.1f}%){'  WIN' if gap < -1 else ''}", flush=True)

    # Also general_nested_chunked (auto segments from 50 bins = 50 seg)
    print("  --- auto segments (general_nested_chunked) ---", flush=True)
    for tl in [400, 500, 600, 800]:
        lat = run_sim(qps, [
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", str(tl),
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", "32",
            "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate"])
        if lat:
            gap = (lat - sar) / sar * 100
            if gap < 3:
                print(f"  auto50seg tl={tl:4d}: {lat:.1f}s ({gap:+.1f}%){'  WIN' if gap < -1 else ''}", flush=True)

print("\nDone!", flush=True)
