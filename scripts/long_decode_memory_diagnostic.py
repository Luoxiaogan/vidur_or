"""
Run a small Vidur memory-pressure diagnostic for the long-decode workload.

The goal is not to estimate the fluid memory requirement M*.  Instead, this
script records Vidur's realized GPU-resident KV-block usage and eviction/restart
metrics under the same A100/Llama-2-7B setting used in the paper.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
OUT_ROOT = PROJECT / "outputs" / "memory_pressure"


def build_prompt_type(rate: float) -> str:
    return json.dumps(
        [{"type": "only", "prefill": 512, "decode": 1000, "arrival_rate": rate}]
    )


def common_args(output_dir: Path, nreq: int, rate: float) -> list[str]:
    prompt_type = build_prompt_type(rate)
    return [
        "python",
        "-m",
        "vidur.main",
        "--replica_config_device",
        "a100",
        "--replica_config_model_name",
        "meta-llama/Llama-2-7b-hf",
        "--replica_config_memory_margin_fraction",
        "0.1",
        "--cluster_config_num_replicas",
        "1",
        "--replica_config_tensor_parallel_size",
        "1",
        "--replica_config_num_pipeline_stages",
        "1",
        "--request_generator_config_type",
        "custom",
        "--custom_request_generator_config_prompt_types",
        prompt_type,
        "--custom_request_generator_config_max_tokens",
        "1512",
        "--custom_request_generator_config_num_requests",
        str(nreq),
        "--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size",
        "512",
        "--random_forrest_execution_time_predictor_config_prediction_max_batch_size",
        "512",
        "--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request",
        "2048",
        "--random_forrest_execution_time_predictor_config_k_fold_cv_splits",
        "2",
        "--metrics_config_keep_individual_batch_metrics",
        "--metrics_config_output_dir",
        str(output_dir),
    ]


def policy_args(policy: str, nreq: int, rate: float) -> tuple[list[str], dict[str, str]]:
    prompt_type = build_prompt_type(rate)
    env = os.environ.copy()

    if policy == "sarathi":
        env["WAIT_CP_GATE"] = "off"
        return (
            [
                "--replica_scheduler_config_type",
                "sarathi",
                "--sarathi_scheduler_config_chunk_size",
                "512",
                "--sarathi_scheduler_config_batch_size_cap",
                "512",
            ],
            env,
        )

    if policy == "vllm":
        env["WAIT_CP_GATE"] = "off"
        return (["--replica_scheduler_config_type", "vllm"], env)

    if policy == "wait":
        env["WAIT_CP_GATE"] = "off"
        return (
            [
                "--replica_scheduler_config_type",
                "general_nested_chunked",
                "--general_nested_chunked_scheduler_config_prompt_types",
                prompt_type,
                "--general_nested_chunked_scheduler_config_total_limit",
                "120",
                "--general_nested_chunked_scheduler_config_total_num_requests",
                str(nreq),
                "--general_nested_chunked_scheduler_config_chunk_size",
                "128",
                "--general_nested_chunked_scheduler_config_seg_margin",
                "0.0",
                "--general_nested_chunked_scheduler_config_force_clear",
                "--no-general_nested_chunked_scheduler_config_wait_gate",
            ],
            env,
        )

    raise ValueError(f"Unknown policy: {policy}")


def find_one(run_dir: Path, pattern: str) -> Path:
    matches = sorted(glob.glob(str(run_dir / "**" / pattern), recursive=True))
    if not matches:
        raise FileNotFoundError(f"No {pattern} under {run_dir}")
    return Path(matches[0])


def central_window(df: pd.DataFrame, frac: float = 0.5) -> pd.DataFrame:
    if df.empty:
        return df
    drop = int(len(df) * (1 - frac) / 2)
    return df.iloc[drop : len(df) - drop] if drop > 0 else df


def summarize(run_dir: Path, policy: str, nreq: int, rate: float) -> dict[str, float | int | str]:
    req = pd.read_csv(find_one(run_dir, "request_metrics_*.csv"))
    batch = pd.read_csv(find_one(run_dir, "batch_metrics*.csv"))

    req_mid = central_window(req)
    batch_mid = central_window(batch)

    restart_col = "request_num_restarts"
    if restart_col not in req_mid and "num_restarts" in req_mid:
        restart_col = "num_restarts"

    restarts = int(req_mid[restart_col].fillna(0).sum()) if restart_col in req_mid else 0
    completed = int(len(req_mid))

    out = {
        "policy": policy,
        "arrival_rate": rate,
        "nreq": nreq,
        "completed_window": completed,
        "mean_latency_s": float(req_mid["request_e2e_time"].mean()),
        "p99_latency_s": float(req_mid["request_e2e_time"].quantile(0.99)),
        "restarts": restarts,
        "restart_rate_pct": float(100 * restarts / max(completed, 1)),
    }

    for col, prefix in [
        ("batch_memory_usage_percent", "resident_memory"),
        ("batch_kv_tokens_percent", "batch_kv_tokens"),
        ("batch_cpu_queue_length", "cpu_queue"),
    ]:
        if col in batch_mid:
            out[f"{prefix}_mean_pct" if "percent" in col else f"{prefix}_mean"] = float(
                batch_mid[col].mean()
            )
            out[f"{prefix}_p95_pct" if "percent" in col else f"{prefix}_p95"] = float(
                batch_mid[col].quantile(0.95)
            )
            out[f"{prefix}_max_pct" if "percent" in col else f"{prefix}_max"] = float(
                batch_mid[col].max()
            )

    return out


def run_policy(policy: str, nreq: int, rate: float, force: bool) -> dict[str, float | int | str]:
    run_dir = OUT_ROOT / f"p512d1000_r{rate:g}_{policy}_n{nreq}"
    if force and run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    if not list(run_dir.rglob("request_metrics_*.csv")):
        args, env = policy_args(policy, nreq, rate)
        cmd = common_args(run_dir, nreq, rate) + args
        print(f"[run] {policy} rate={rate:g} nreq={nreq}", flush=True)
        result = subprocess.run(
            cmd,
            cwd=PROJECT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=7200,
        )
        if result.returncode != 0:
            (run_dir / "stdout.log").write_text(result.stdout)
            (run_dir / "stderr.log").write_text(result.stderr)
            raise RuntimeError(f"{policy} failed; see {run_dir}/stderr.log")
        (run_dir / "stdout.log").write_text(result.stdout)
        (run_dir / "stderr.log").write_text(result.stderr)
    else:
        print(f"[cache] {policy} rate={rate:g} nreq={nreq}", flush=True)

    return summarize(run_dir, policy, nreq, rate)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rate", type=float, default=4.0)
    parser.add_argument("--nreq", type=int, default=2000)
    parser.add_argument(
        "--policies", nargs="+", default=["sarathi", "wait"], choices=["sarathi", "wait", "vllm"]
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    rows = [run_policy(p, args.nreq, args.rate, args.force) for p in args.policies]
    summary = pd.DataFrame(rows)
    out = OUT_ROOT / f"p512d1000_r{args.rate:g}_n{args.nreq}_summary.csv"
    summary.to_csv(out, index=False)
    print(summary.to_string(index=False))
    print(f"[write] {out}")


if __name__ == "__main__":
    main()
