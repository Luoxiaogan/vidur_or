"""
C1/C2: Memory usage + throughput time series at near-capacity rates.
Saves full sim output (request_metrics + throughput + batch_metrics CSVs).
"""
import subprocess, json, os, shutil, glob
from pathlib import Path

PROJECT = "/persistent/vidur_or"
OUTDIR = Path(PROJECT) / "outputs" / "memory_throughput"
OUTDIR.mkdir(parents=True, exist_ok=True)

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
L0, L1, MAX_TOK = 512, 20, 532

# Near-capacity rates for each algorithm:
# vLLM saturates ~r=16, Sarathi ~r=22, WCP ~r=23
# Test at r=20 (all stable), r=22 (Sarathi boundary), r=24 (all unstable)
RATES = [20, 22, 24]

EXPERIMENTS = []
for rate in RATES:
    pt = json.dumps([{"type": "only", "prefill": L0, "decode": L1, "arrival_rate": rate}])

    # Sarathi
    EXPERIMENTS.append({
        "label": f"Sarathi_r{rate}",
        "args": [
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", str(MAX_TOK),
            "--custom_request_generator_config_num_requests", str(NREQ),
            "--replica_scheduler_config_type", "sarathi",
            "--sarathi_scheduler_config_chunk_size", "512",
            "--sarathi_scheduler_config_batch_size_cap", "512",
        ],
        "gate": False,
    })
    # vLLM
    EXPERIMENTS.append({
        "label": f"vLLM_r{rate}",
        "args": [
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", str(MAX_TOK),
            "--custom_request_generator_config_num_requests", str(NREQ),
            "--replica_scheduler_config_type", "vllm",
        ],
        "gate": False,
    })
    # WCP
    EXPERIMENTS.append({
        "label": f"WCP_r{rate}",
        "args": [
            "--custom_request_generator_config_prompt_types", pt,
            "--custom_request_generator_config_max_tokens", str(MAX_TOK),
            "--custom_request_generator_config_num_requests", str(NREQ),
            "--replica_scheduler_config_type", "general_nested_chunked",
            "--general_nested_chunked_scheduler_config_prompt_types", pt,
            "--general_nested_chunked_scheduler_config_total_limit", "21",
            "--general_nested_chunked_scheduler_config_total_num_requests", str(NREQ),
            "--general_nested_chunked_scheduler_config_chunk_size", "256",
            "--general_nested_chunked_scheduler_config_seg_margin", "0.0",
            "--general_nested_chunked_scheduler_config_force_clear",
            "--no-general_nested_chunked_scheduler_config_wait_gate",
        ],
        "gate": True,
    })


for exp in EXPERIMENTS:
    exp_dir = OUTDIR / exp["label"]
    if exp_dir.exists() and list(exp_dir.glob("*.csv")):
        print(f"  {exp['label']}: cached", flush=True)
        continue

    env = os.environ.copy()
    env["WAIT_CP_GATE"] = "on" if exp["gate"] else "off"

    # Save full output to exp_dir
    exp_dir.mkdir(parents=True, exist_ok=True)
    cmd = COMMON + [
        "--metrics_config_output_dir", str(exp_dir),
    ] + exp["args"]

    print(f"  {exp['label']}: running...", end="", flush=True)
    result = subprocess.run(cmd, capture_output=True, cwd=PROJECT, timeout=3600, env=env, text=True)

    if result.returncode != 0:
        print(f" FAIL", flush=True)
        continue

    csvs = list(exp_dir.rglob("*.csv"))
    print(f" done ({len(csvs)} CSVs)", flush=True)
    for c in csvs:
        print(f"    {c.name}", flush=True)

print("\nDone!")
