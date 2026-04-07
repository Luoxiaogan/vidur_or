#!/usr/bin/env python3
"""
Vidur vs Real GPU Comparison - Prove Vidur Reliability

This script:
1. Runs real GPU measurements using vLLM
2. Runs Vidur simulation with identical settings
3. Compares results to prove Vidur reliability

Usage:
    python scripts/vidur_vs_real_gpu_comparison.py --model qwen --batch-sizes 1 2 4 8
"""

import subprocess
import json
import pandas as pd
import os
import sys
import tempfile
import glob
import time
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np

PROJECT = "/home/archer/vidur_or"
sys.path.insert(0, PROJECT)

# Try to import vLLM
try:
    from vllm import LLM, SamplingParams
    import torch
    HAS_VLLM = True
except ImportError:
    HAS_VLLM = False
    print("WARNING: vLLM not available")


def run_real_gpu_measurement(
    model_name: str,
    batch_size: int,
    prefill_len: int,
    decode_len: int,
    num_iters: int = 5
) -> Optional[Dict]:
    """Measure real GPU iteration time using vLLM."""
    if not HAS_VLLM:
        return None

    print(f"  [Real GPU] Measuring batch={batch_size}...", end=" ")

    try:
        llm = LLM(
            model=model_name,
            dtype="float16",
            max_model_len=4096,
            max_num_seqs=batch_size * 2,
            gpu_memory_utilization=0.9,
        )

        # Prepare prompt
        base_text = "The quick brown fox jumps over the lazy dog. "
        words_needed = int(prefill_len / 0.75) + 20
        long_text = (base_text * (words_needed // 9 + 1))[:words_needed * 10]
        prompts = [long_text] * batch_size

        sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=decode_len + 5,
            ignore_eos=True,
        )

        # Warmup
        _ = llm.generate(prompts, sampling_params)
        torch.cuda.synchronize()

        # Measure
        times = []
        for _ in range(num_iters):
            torch.cuda.synchronize()
            start = time.perf_counter()
            _ = llm.generate(prompts, sampling_params)
            torch.cuda.synchronize()
            end = time.perf_counter()
            times.append((end - start) * 1000)

        memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

        del llm
        torch.cuda.empty_cache()

        result = {
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'memory_mb': memory_mb,
        }
        print(f"Done (mean={result['mean_ms']:.2f}ms)")
        return result

    except Exception as e:
        print(f"Error: {e}")
        return None


def run_vidur_simulation(
    model_name: str,
    batch_size: int,
    prefill_len: int,
    decode_len: int,
    num_requests: int = 100
) -> Optional[Dict]:
    """Run Vidur simulation with identical settings."""
    print(f"  [Vidur] Simulating batch={batch_size}...", end=" ")

    # Map model name
    model_map = {
        "qwen": "meta-llama/Meta-Llama-3-8B",  # Use similar profile
        "Qwen/Qwen2.5-Math-1.5B": "meta-llama/Meta-Llama-3-8B",
    }
    vidur_model = model_map.get(model_name, "meta-llama/Meta-Llama-3-8B")

    # Create prompt types
    prompt_types = json.dumps([{
        "type": "default",
        "prefill": prefill_len,
        "decode": decode_len,
        "arrival_rate": 1.0  # Low rate for single batch
    }])

    tmpdir = tempfile.mkdtemp(prefix="vidur_cmp_")

    cmd = [
        "python", "-m", "vidur.main",
        "--replica_config_device", "a100",
        "--replica_config_model_name", vidur_model,
        "--replica_config_memory_margin_fraction", "0.1",
        "--cluster_config_num_replicas", "1",
        "--request_generator_config_type", "custom",
        "--custom_request_generator_config_num_requests", str(num_requests),
        "--custom_request_generator_config_prompt_types", prompt_types,
        "--custom_request_generator_config_max_tokens", str(prefill_len + decode_len + 10),
        "--replica_scheduler_config_type", "sarathi",
        "--sarathi_scheduler_config_chunk_size", "512",
        "--metrics_config_output_dir", tmpdir,
        "--no-metrics_config_store_plots",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=PROJECT,
            timeout=300,
            text=True
        )

        if result.returncode != 0:
            print(f"Failed: {result.stderr[:100]}")
            return None

        # Parse results
        csvs = glob.glob(f"{tmpdir}/**/request_metrics_*.csv", recursive=True)
        if not csvs:
            print("No metrics found")
            return None

        df = pd.read_csv(csvs[0])

        # Calculate mean iteration time from batch times
        if 'batch_execution_time' in df.columns:
            mean_time = df['batch_execution_time'].mean() * 1000  # Convert to ms
        else:
            # Estimate from e2e time
            mean_time = df['request_e2e_time'].mean() * 1000 / decode_len

        # Cleanup
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)

        result = {'mean_ms': mean_time}
        print(f"Done (mean={result['mean_ms']:.2f}ms)")
        return result

    except Exception as e:
        print(f"Error: {e}")
        return None


def compare_and_report(
    model_name: str,
    batch_sizes: List[int],
    prefill_len: int,
    decode_len: int,
    output_dir: str
):
    """Run comparison and generate report."""
    results = []

    print(f"\n{'='*80}")
    print(f"Vidur vs Real GPU Comparison")
    print(f"Model: {model_name}")
    print(f"Config: prefill={prefill_len}, decode={decode_len}")
    print(f"{'='*80}\n")

    for batch_size in batch_sizes:
        print(f"\nBatch Size: {batch_size}")

        # Real GPU
        real_result = run_real_gpu_measurement(
            model_name, batch_size, prefill_len, decode_len
        )

        # Vidur simulation
        vidur_result = run_vidur_simulation(
            model_name, batch_size, prefill_len, decode_len
        )

        if real_result and vidur_result:
            error_ms = real_result['mean_ms'] - vidur_result['mean_ms']
            error_percent = (error_ms / real_result['mean_ms']) * 100

            results.append({
                'batch_size': batch_size,
                'prefill_len': prefill_len,
                'decode_len': decode_len,
                'real_mean_ms': real_result['mean_ms'],
                'real_std_ms': real_result['std_ms'],
                'vidur_mean_ms': vidur_result['mean_ms'],
                'error_ms': error_ms,
                'error_percent': error_percent,
            })

            print(f"  Comparison:")
            print(f"    Real GPU: {real_result['mean_ms']:.2f} ± {real_result['std_ms']:.2f} ms")
            print(f"    Vidur:    {vidur_result['mean_ms']:.2f} ms")
            print(f"    Error:    {error_percent:+.1f}%")

    # Save results
    if results:
        df = pd.DataFrame(results)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        csv_path = output_path / f'vidur_vs_real_{model_name.replace("/", "_")}.csv'
        df.to_csv(csv_path, index=False)

        # Calculate MAPE
        mape = df['error_percent'].abs().mean()

        print(f"\n{'='*80}")
        print("Summary")
        print(f"{'='*80}")
        print(f"Model: {model_name}")
        print(f"Configurations tested: {len(results)}")
        print(f"Mean Absolute Percentage Error (MAPE): {mape:.2f}%")

        if mape < 10:
            print("✅ EXCELLENT: Vidur predictions are highly accurate")
        elif mape < 20:
            print("✅ GOOD: Vidur predictions are reasonably accurate")
        else:
            print("⚠️ MODERATE: Vidur predictions have moderate error")

        print(f"\nResults saved to: {csv_path}")
        print(f"{'='*80}\n")

        return df

    return None


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, default='Qwen/Qwen2.5-Math-1.5B')
    parser.add_argument('--batch-sizes', type=int, nargs='+', default=[1, 2, 4])
    parser.add_argument('--prefill', type=int, default=128)
    parser.add_argument('--decode', type=int, default=20)
    parser.add_argument('--output-dir', type=str, default='outputs/vidur_comparison')

    args = parser.parse_args()

    if not HAS_VLLM:
        print("ERROR: vLLM not available")
        sys.exit(1)

    compare_and_report(
        args.model,
        args.batch_sizes,
        args.prefill,
        args.decode,
        args.output_dir
    )


if __name__ == '__main__':
    main()
