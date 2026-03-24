"""
3D grid search: cs × tl × sm for r=20 B2 2-type.
Fast mode: nreq=2000, find top configs, then verify with 5000.
"""
import subprocess, json, pandas as pd, os, shutil, glob, tempfile
from datetime import datetime

PROJECT = "/home/CPU/vidur_or"

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

RATE = 20
r1, r2 = 14.0, 6.0
PT = json.dumps([
    {"type": "short", "prefill": 256, "decode": 10, "arrival_rate": r1},
    {"type": "long", "prefill": 512, "decode": 50, "arrival_rate": r2},
])
MAX_TOKENS = 562
SAR_BASELINE = 0.515  # from profiling


def run(tl, cs, sm, nreq):
    tmpdir = tempfile.mkdtemp(prefix="vidur_grid_")
    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on"
    cmd = COMMON + [
        "--custom_request_generator_config_max_tokens", str(MAX_TOKENS),
        "--custom_request_generator_config_num_requests", str(nreq),
        "--metrics_config_output_dir", tmpdir,
        "--custom_request_generator_config_prompt_types", PT,
        "--replica_scheduler_config_type", "general_nested_chunked",
        "--general_nested_chunked_scheduler_config_prompt_types", PT,
        "--general_nested_chunked_scheduler_config_total_limit", str(tl),
        "--general_nested_chunked_scheduler_config_total_num_requests", str(nreq),
        "--general_nested_chunked_scheduler_config_chunk_size", str(cs),
        "--general_nested_chunked_scheduler_config_seg_margin", str(sm),
        "--general_nested_chunked_scheduler_config_force_clear",
        "--no-general_nested_chunked_scheduler_config_wait_gate",
    ]
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
    return s["request_e2e_time"].mean()


# ========= Phase 1: Coarse grid with nreq=2000 =========
CS_LIST = [64, 128, 192, 256, 384, 512]
TL_LIST = [15, 20, 25, 30, 35, 40, 50]
SM_LIST = [-0.1, 0.0, 0.1, 0.2, 0.3]

total = len(CS_LIST) * len(TL_LIST) * len(SM_LIST)
print(f"Phase 1: {total} configs (nreq=2000)")
print(f"Sarathi baseline: {SAR_BASELINE:.3f}s")
print()

results = []
done = 0
for cs in CS_LIST:
    for tl in TL_LIST:
        for sm in SM_LIST:
            done += 1
            m = run(tl, cs, sm, nreq=2000)
            if m is not None:
                g = (m - SAR_BASELINE) / SAR_BASELINE * 100
                mk = "WIN" if g < -1 else ""
                results.append((cs, tl, sm, m, g))
                print(f"[{done}/{total}] cs={cs:3d} tl={tl:2d} sm={sm:+.1f}: {m:.3f}s ({g:+.1f}%) {mk}", flush=True)
            else:
                print(f"[{done}/{total}] cs={cs:3d} tl={tl:2d} sm={sm:+.1f}: FAIL", flush=True)

# Sort by gap
results.sort(key=lambda x: x[4])
print("\n===== Top 10 configs =====")
for cs, tl, sm, m, g in results[:10]:
    print(f"  cs={cs:3d} tl={tl:2d} sm={sm:+.1f}: {m:.3f}s ({g:+.1f}%)")

# ========= Phase 2: Verify top 5 with nreq=5000 =========
print("\n===== Phase 2: Verify top 5 (nreq=5000) =====")
for cs, tl, sm, _, _ in results[:5]:
    m = run(tl, cs, sm, nreq=5000)
    if m is not None:
        g = (m - SAR_BASELINE) / SAR_BASELINE * 100
        mk = "WIN" if g < -1 else ""
        print(f"  cs={cs:3d} tl={tl:2d} sm={sm:+.1f}: {m:.3f}s ({g:+.1f}%) {mk}", flush=True)
    else:
        print(f"  cs={cs:3d} tl={tl:2d} sm={sm:+.1f}: FAIL", flush=True)

print("\nDone!")
