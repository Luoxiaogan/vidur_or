#!/usr/bin/env python3
"""
Llama-2-7B Real GPU vs Vidur Profiling Comparison

Uses Llama-2-7B which is compatible with Vidur profiling data.
"""

import os
import sys
import time
import json
import warnings
from pathlib import Path
from typing import List, Dict, Optional
import numpy as np
import pandas as pd

warnings.filterwarnings('ignore')

# Check GPU and vLLM
try:
    import torch
    from vllm import LLM, SamplingParams
    HAS_GPU = torch.cuda.is_available()
    HAS_VLLM = True
except ImportError:
    HAS_GPU = False
    HAS_VLLM = False
    print("ERROR: vLLM or GPU not available")
    sys.exit(1)


def measure_llama2(
    batch_size: int,
    prefill_len: int,
    decode_len: int,
    num_iters: int = 5
) -> Optional[Dict]:
    """Measure Llama-2-7B on real GPU."""

    model_path = "models/modelscope/Llama-2-7b-ms"

    print(f"  [Real GPU] batch={batch_size}, prefill={prefill_len}, decode={decode_len}...", end=" ")

    try:
        llm = LLM(
            model=model_path,
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
        print(f"Done ({result['mean_ms']:.2f}ms)")
        return result

    except Exception as e:
        print(f"Error: {e}")
        return None


def get_vidur_prediction(batch_size: int) -> Optional[float]:
    """Get Vidur prediction from profiling data."""
    attn_file = Path("data/profiling/compute/a100/meta-llama/Llama-2-7b-hf/attention.csv")

    if not attn_file.exists():
        return None

    try:
        df = pd.read_csv(attn_file)
        # Filter decode
        if 'is_decode' in df.columns:
            decode_df = df[df['is_decode'] == True]
        elif 'prefill_chunk_size' in df.columns:
            decode_df = df[df['prefill_chunk_size'] == 0]
        else:
            return None

        # Find closest batch size
        if 'batch_size' in decode_df.columns and 'time_stats.attn_decode.median' in decode_df.columns:
            closest = decode_df.iloc[(decode_df['batch_size'] - batch_size).abs().argsort()[:1]]
            if len(closest) > 0:
                # Note: this is just attention time, not full iteration
                return closest['time_stats.attn_decode.median'].values[0]
    except Exception as e:
        print(f"Warning: {e}")

    return None


def main():
    print("="*80)
    print("Llama-2-7B Real GPU vs Vidur Profiling Comparison")
    print("="*80)

    configs = [
        (1, 256, 20),
        (2, 256, 20),
        (4, 256, 20),
        (8, 256, 20),
    ]

    results = []

    for batch_size, prefill_len, decode_len in configs:
        print(f"\nConfig: batch={batch_size}, prefill={prefill_len}, decode={decode_len}")

        # Real GPU measurement
        real_result = measure_llama2(batch_size, prefill_len, decode_len)

        # Vidur prediction (attention only)
        vidur_pred = get_vidur_prediction(batch_size)

        if real_result:
            result = {
                'batch_size': batch_size,
                'prefill_len': prefill_len,
                'decode_len': decode_len,
                'real_mean_ms': real_result['mean_ms'],
                'real_std_ms': real_result['std_ms'],
                'real_memory_mb': real_result['memory_mb'],
                'vidur_attn_ms': vidur_pred,
            }

            if vidur_pred:
                print(f"  Real (full iter): {real_result['mean_ms']:.2f}ms")
                print(f"  Vidur (attn only): {vidur_pred:.2f}ms")
                print(f"  Note: Vidur profiling is attention-only component")
            else:
                print(f"  Real: {real_result['mean_ms']:.2f}ms")
                print(f"  Vidur: N/A")

            results.append(result)

    # Save results
    if results:
        df = pd.DataFrame(results)
        output_dir = Path("outputs/llama2_validation")
        output_dir.mkdir(parents=True, exist_ok=True)

        csv_path = output_dir / 'llama2_real_gpu_results.csv'
        df.to_csv(csv_path, index=False)

        print(f"\n{'='*80}")
        print("Summary")
        print(f"{'='*80}")
        print(f"Configurations tested: {len(results)}")
        print(f"\nResults saved to: {csv_path}")
        print(f"\nNote: Vidur profiling data is component-level (attention only).")
        print(f"Real GPU measurement includes: attention + MLP + layernorm + communication")
        print(f"{'='*80}")


if __name__ == '__main__':
    main()
