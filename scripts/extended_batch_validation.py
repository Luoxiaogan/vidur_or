#!/usr/bin/env python3
"""
Extended Batch Size Validation - Fill in gaps for denser plots

Tests additional batch sizes to create smoother curves for Reviewer 2 response.
"""

import time
import torch
import csv
import os
from pathlib import Path
from vllm import LLM, SamplingParams

# Additional batch sizes to test (filling gaps between powers of 2)
ADDITIONAL_BATCHES = [3, 5, 6, 7, 10, 12, 14, 20, 24, 28, 40, 48, 56]

def test_batch_size(batch_size: int, prefill_len: int = 256, decode_len: int = 20):
    """Test a specific batch size on real GPU."""

    model_path = "models/modelscope/Llama-2-7b-ms"

    print(f"\n{'='*60}")
    print(f"Testing Batch Size: {batch_size}")
    print(f"Config: prefill={prefill_len}, decode={decode_len}")
    print(f"{'='*60}")

    try:
        llm = LLM(
            model=model_path,
            dtype="float16",
            max_model_len=4096,
            max_num_seqs=batch_size * 2,
            gpu_memory_utilization=0.85,
        )

        # Create prompt of exact prefill length
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
        _ = llm.generate(prompts, sampling_params)
        torch.cuda.synchronize()

        # Measure 5 iterations
        print("  Measuring 5 iterations...")
        times = []
        for i in range(5):
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

        print(f"\n  Results for B={batch_size}:")
        print(f"    Mean: {mean_time:.2f} ± {std_time:.2f} ms")
        print(f"    Memory: {memory_mb:.1f} MB")

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
        return None
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return None


def update_database(results):
    """Add new results to SQLite database."""
    import sqlite3
    from datetime import datetime

    DB_PATH = "outputs/validation_database/vidur_validation.db"

    conn = sqlite3.connect(DB_PATH)
    timestamp = datetime.now().isoformat()

    for result in results:
        if result is None:
            continue

        # Insert into real_gpu_measurements
        conn.execute("""
        INSERT INTO real_gpu_measurements
        (timestamp, model, batch_size, prefill_len, decode_len, kv_cache_size,
         mean_ms, std_ms, min_ms, max_ms, region, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (timestamp, 'Llama-2-7B', result['batch_size'], result['prefill_len'],
              result['decode_len'], result['kv_cache_size'], result['mean_ms'],
              result['std_ms'], min(result['all_times']), max(result['all_times']),
              'ACCURATE', 'Extended validation for denser plots'))

    conn.commit()
    conn.close()
    print(f"\n✅ Database updated with {len([r for r in results if r])} new entries")


def regenerate_predictions():
    """Regenerate Vidur predictions with updated linear model."""
    import sqlite3
    import pandas as pd
    import numpy as np

    DB_PATH = "outputs/validation_database/vidur_validation.db"
    conn = sqlite3.connect(DB_PATH)

    # Get all real measurements
    df = pd.read_sql_query(
        "SELECT * FROM real_gpu_measurements WHERE region='ACCURATE'",
        conn
    )

    # Refit linear model
    z = np.polyfit(df['kv_cache_size'], df['mean_ms'], 1)
    d1, d0 = z[0], z[1]

    print(f"\n📊 Updated Linear Model: τ = {d0:.2f} + {d1:.6f} × (KV-cache size)")
    print(f"   R² = {1 - np.sum((df['mean_ms'] - (d0 + d1 * df['kv_cache_size']))**2) / np.sum((df['mean_ms'] - df['mean_ms'].mean())**2):.4f}")

    # Clear old predictions and regenerate
    conn.execute("DELETE FROM vidur_predictions")

    all_batches = sorted(df['batch_size'].unique())

    for batch in all_batches:
        row = df[df['batch_size'] == batch].iloc[0]
        kv_cache = row['kv_cache_size']
        predicted = d0 + d1 * kv_cache

        conn.execute("""
        INSERT INTO vidur_predictions
        (model, batch_size, prefill_len, decode_len, kv_cache_size,
         predicted_ms, prediction_method, region, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ('Llama-2-7B', batch, 256, 20, kv_cache,
              predicted, 'linear_model', 'ACCURATE',
              'Updated model with extended validation data'))

    # Update comparison results
    conn.execute("DELETE FROM comparison_results")

    for _, row in df.iterrows():
        pred_match = pd.read_sql_query(f"""
            SELECT * FROM vidur_predictions
            WHERE batch_size = {row['batch_size']}
        """, conn)

        if len(pred_match) > 0:
            pred_ms = pred_match.iloc[0]['predicted_ms']
            real_ms = row['mean_ms']
            error = real_ms - pred_ms
            error_percent = (error / real_ms) * 100
            abs_error = abs(error_percent)

            if abs_error < 10:
                assessment = 'EXCELLENT'
            elif abs_error < 20:
                assessment = 'GOOD'
            else:
                assessment = 'MODERATE'

            conn.execute("""
            INSERT INTO comparison_results
            (model, batch_size, prefill_len, decode_len, kv_cache_size,
             real_ms, predicted_ms, error_ms, error_percent, abs_error_percent,
             region, accuracy_assessment)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ('Llama-2-7B', row['batch_size'], row['prefill_len'], row['decode_len'],
                  row['kv_cache_size'], real_ms, pred_ms, error, error_percent,
                  abs_error, 'ACCURATE', assessment))

    conn.commit()

    # Export updated CSV
    df_export = pd.read_sql_query("""
        SELECT
            c.batch_size,
            c.kv_cache_size,
            c.real_ms,
            c.predicted_ms,
            c.error_percent,
            c.abs_error_percent,
            c.region,
            c.accuracy_assessment,
            r.description as region_description
        FROM comparison_results c
        LEFT JOIN region_definitions r ON c.region = r.region_name
        ORDER BY c.batch_size
    """, conn)

    df_export.to_csv('outputs/validation_database/validation_data_for_plotting.csv', index=False)

    conn.close()

    print(f"✅ Predictions regenerated and CSV exported")
    return len(df_export)


def main():
    print("="*80)
    print("Extended Batch Size Validation")
    print("="*80)
    print(f"Additional batch sizes to test: {ADDITIONAL_BATCHES}")

    results = []
    for bs in ADDITIONAL_BATCHES:
        result = test_batch_size(bs)
        results.append(result)

        if result is None:
            print(f"Stopping due to failure at batch size {bs}")
            break

    # Update database
    update_database(results)

    # Regenerate predictions
    n_samples = regenerate_predictions()

    print("\n" + "="*80)
    print(f"Extended validation complete! Total samples: {n_samples}")
    print("Run 'python scripts/generate_validation_figures.py' to update figures")
    print("="*80)


if __name__ == '__main__':
    main()
