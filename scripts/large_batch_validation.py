#!/usr/bin/env python3
"""
Large Batch Size Validation - Including Reviewer's B=600 Case

Tests:
1. Intermediate batch sizes (70-128) to fill gaps
2. Very large batches (B=600) with small prompts as reviewer suggested
"""

import time
import torch
import csv
import os
from pathlib import Path
from vllm import LLM, SamplingParams

# Test configurations
# Region 1: Intermediate batches (fill gap between 64 and 128)
INTERMEDIATE_BATCHES = [70, 80, 96, 112, 128]

# Region 2: Large batches (approaching memory limit with normal prompt)
LARGE_BATCHES_NORMAL = [150, 200, 256]

# Region 3: Extreme batches (reviewer's B=600 case with small prompt)
# Using small prompt: prefill=20, decode=10 (as in test_large_batch_small_prompt.py)
EXTREME_BATCHES_SMALL_PROMPT = [300, 400, 600]

def test_batch_size(batch_size: int, prefill_len: int, decode_len: int, model_path: str):
    """Test a specific batch size on real GPU."""

    print(f"\n{'='*60}")
    print(f"Testing Batch Size: {batch_size}")
    print(f"Config: prefill={prefill_len}, decode={decode_len}")
    print(f"KV Cache: {batch_size * (prefill_len + decode_len)} tokens")
    print(f"{'='*60}")

    try:
        max_model_len = max(4096, prefill_len + decode_len + 100)
        llm = LLM(
            model=model_path,
            dtype="float16",
            max_model_len=max_model_len,
            max_num_seqs=batch_size * 2,
            gpu_memory_utilization=0.90,
        )

        # Create prompt of exact prefill length
        if prefill_len <= 50:
            # Small prompt for extreme batches
            base_text = "Hi, how are you? "
            words_needed = int(prefill_len / 0.75) + 5
        else:
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
        print("  Warmup...")
        warmup_batch = min(10, batch_size)
        _ = llm.generate(prompts[:warmup_batch], sampling_params)
        torch.cuda.synchronize()

        # Measure iterations
        num_iterations = 5 if batch_size <= 128 else 3
        print(f"  Measuring {num_iterations} iterations...")
        times = []
        for i in range(num_iterations):
            torch.cuda.synchronize()
            start = time.perf_counter()
            _ = llm.generate(prompts, sampling_params)
            torch.cuda.synchronize()
            end = time.perf_counter()
            iter_time = (end - start) * 1000
            times.append(iter_time)
            print(f"    Iter {i+1}: {iter_time:.2f} ms")

        memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

        # Statistics
        import numpy as np
        mean_time = np.mean(times)
        std_time = np.std(times)

        print(f"\n  Results for B={batch_size} (P={prefill_len}, D={decode_len}):")
        print(f"    Mean: {mean_time:.2f} ± {std_time:.2f} ms")
        print(f"    Memory: {memory_mb:.1f} MB ({memory_mb/1024:.2f} GB)")

        del llm
        torch.cuda.empty_cache()

        return {
            'batch_size': batch_size,
            'prefill_len': prefill_len,
            'decode_len': decode_len,
            'kv_cache_size': batch_size * (prefill_len + decode_len),
            'mean_ms': mean_time,
            'std_ms': std_time,
            'memory_mb': memory_mb,
            'all_times': times
        }

    except torch.cuda.OutOfMemoryError:
        print(f"  ❌ OOM at batch size {batch_size}")
        return {'batch_size': batch_size, 'prefill_len': prefill_len, 'decode_len': decode_len, 'oom': True}
    except Exception as e:
        print(f"  ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def update_database(results):
    """Add new results to SQLite database."""
    import sqlite3
    from datetime import datetime

    DB_PATH = "outputs/validation_database/vidur_validation.db"
    conn = sqlite3.connect(DB_PATH)
    timestamp = datetime.now().isoformat()

    oom_count = 0
    success_count = 0

    for result in results:
        if result is None:
            continue

        if 'oom' in result and result['oom']:
            oom_count += 1
            continue

        if 'mean_ms' not in result:
            continue

        # Determine region
        batch = result['batch_size']
        if batch <= 64:
            region = 'ACCURATE'
        elif batch <= 128:
            region = 'ACCURATE_PLUS'  # Extended accurate region
        else:
            region = 'EXTRAPOLATION'

        conn.execute("""
        INSERT INTO real_gpu_measurements
        (timestamp, model, batch_size, prefill_len, decode_len, kv_cache_size,
         mean_ms, std_ms, min_ms, max_ms, region, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, 'Llama-2-7B', result['batch_size'], result['prefill_len'],
              result['decode_len'], result['kv_cache_size'], result['mean_ms'],
              result['std_ms'], min(result['all_times']), max(result['all_times']),
              region, 'Large batch validation including reviewer case'))

        success_count += 1

    conn.commit()
    conn.close()
    print(f"\n✅ Database updated: {success_count} new entries, {oom_count} OOM")


def main():
    model_path = "models/modelscope/Llama-2-7b-ms"

    print("="*80)
    print("Large Batch Size Validation - Including Reviewer's B=600 Case")
    print("="*80)

    results = []

    # Phase 1: Intermediate batches (70-128) with normal prompt
    print("\n" + "="*80)
    print("PHASE 1: Intermediate Batches (70-128) with Normal Prompt")
    print("="*80)
    for bs in INTERMEDIATE_BATCHES:
        result = test_batch_size(bs, 256, 20, model_path)
        results.append(result)
        if result and 'oom' in result:
            print(f"Stopping intermediate batch tests due to OOM")
            break

    # Phase 2: Large batches (150-256) with normal prompt
    print("\n" + "="*80)
    print("PHASE 2: Large Batches (150-256) with Normal Prompt")
    print("="*80)
    for bs in LARGE_BATCHES_NORMAL:
        result = test_batch_size(bs, 256, 20, model_path)
        results.append(result)
        if result and 'oom' in result:
            print(f"Stopping large batch tests due to OOM")
            break

    # Phase 3: Extreme batches (300-600) with small prompt
    print("\n" + "="*80)
    print("PHASE 3: Extreme Batches (300-600) with Small Prompt")
    print("(Reviewer 2's case: small prompt, large batch)")
    print("="*80)
    for bs in EXTREME_BATCHES_SMALL_PROMPT:
        result = test_batch_size(bs, 20, 10, model_path)
        results.append(result)
        # Continue even if OOM to try smaller extreme batches

    # Update database
    update_database(results)

    print("\n" + "="*80)
    print("Large batch validation complete!")
    print("Run 'python scripts/regenerate_predictions.py' to update predictions")
    print("="*80)


if __name__ == '__main__':
    main()
