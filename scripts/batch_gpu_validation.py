#!/usr/bin/env python3
"""
Batch GPU Validation - Multiple Models

Validates Vidur simulation against real GPU measurements for multiple models.
Tests: Qwen, Llama-2, Llama-3

Usage:
    python scripts/batch_gpu_validation.py --models qwen llama2 --output outputs/batch_validation
"""

import os
import sys
import json
import time
import argparse
import warnings
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

# Suppress warnings
warnings.filterwarnings('ignore')

# Check for GPU availability
try:
    import torch
    HAS_GPU = torch.cuda.is_available()
    GPU_NAME = torch.cuda.get_device_name(0) if HAS_GPU else "None"
except ImportError:
    HAS_GPU = False
    GPU_NAME = "None"

# Check for vLLM
try:
    import vllm
    HAS_VLLM = True
    VLLM_VERSION = vllm.__version__
except ImportError:
    HAS_VLLM = False
    VLLM_VERSION = "None"


@dataclass
class ModelConfig:
    """Configuration for a model to validate."""
    name: str
    model_path: str
    profiling_name: str  # Name in Vidur profiling data
    batch_sizes: List[int]
    prefill_lengths: List[int]
    decode_lengths: List[int]
    num_iterations: int = 10


def measure_real_gpu(
    model_path: str,
    batch_size: int,
    prefill_length: int,
    decode_length: int,
    num_iterations: int = 10,
    warmup: int = 3
) -> Optional[Dict]:
    """Measure iteration time on real GPU using vLLM."""
    if not HAS_VLLM or not HAS_GPU:
        print("  [SKIP] vLLM or GPU not available")
        return None

    try:
        from vllm import LLM, SamplingParams

        print(f"  Loading {model_path}...")
        llm = LLM(
            model=model_path,
            dtype="float16",
            max_model_len=4096,
            max_num_seqs=batch_size * 2,
            gpu_memory_utilization=0.9,
        )

        # Prepare prompt
        base_text = "The quick brown fox jumps over the lazy dog. "
        words_needed = int(prefill_length / 0.75) + 20
        long_text = (base_text * (words_needed // 9 + 1))[:words_needed * 10]
        prompts = [long_text] * batch_size

        sampling_params = SamplingParams(
            temperature=0.0,
            max_tokens=decode_length + 5,
            ignore_eos=True,
        )

        # Warmup
        print(f"  Warmup...", end=" ")
        for _ in range(warmup):
            _ = llm.generate(prompts, sampling_params)
        print("Done")

        torch.cuda.empty_cache()
        torch.cuda.synchronize()

        # Measure
        print(f"  Measuring {num_iterations} iterations...", end=" ")
        times = []
        for _ in range(num_iterations):
            torch.cuda.synchronize()
            start = time.perf_counter()
            _ = llm.generate(prompts, sampling_params)
            torch.cuda.synchronize()
            end = time.perf_counter()
            times.append((end - start) * 1000)
        print("Done")

        memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

        del llm
        torch.cuda.empty_cache()

        return {
            'mean_ms': np.mean(times),
            'std_ms': np.std(times),
            'min_ms': np.min(times),
            'max_ms': np.max(times),
            'memory_mb': memory_mb,
        }

    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def load_vidur_prediction(
    model_name: str,
    batch_size: int,
    prefill_len: int,
    decode_len: int
) -> Optional[float]:
    """Load Vidur profiling prediction for comparison."""
    # Map model names
    model_map = {
        "qwen": "Qwen/Qwen2.5-Math-1.5B",
        "llama2-7b": "meta-llama/Llama-2-7b-hf",
        "llama3-8b": "meta-llama/Meta-Llama-3-8B",
    }

    vidur_model = model_map.get(model_name, model_name)
    data_dir = Path(f"data/profiling/compute/a100/{vidur_model.replace('/', '-')}")

    if not data_dir.exists():
        # Try alternative paths
        alt_paths = [
            Path(f"data/profiling/compute/a100/{vidur_model.split('/')[-1]}"),
            Path(f"data/profiling/compute/a100/meta-llama/{vidur_model.split('/')[-1]}"),
        ]
        for alt in alt_paths:
            if alt.exists():
                data_dir = alt
                break

    if not data_dir.exists():
        print(f"  [WARN] Profiling data not found for {model_name}")
        return None

    # Load attention data for decode time prediction
    attn_file = data_dir / "attention.csv"
    if not attn_file.exists():
        return None

    try:
        df = pd.read_csv(attn_file)
        # Filter for decode (is_decode=True or prefill_chunk_size=0)
        if 'is_decode' in df.columns:
            decode_df = df[df['is_decode'] == True]
        elif 'prefill_chunk_size' in df.columns:
            decode_df = df[df['prefill_chunk_size'] == 0]
        else:
            decode_df = df

        # Find closest batch size
        if 'batch_size' in decode_df.columns and 'time_stats.attn_decode.median' in decode_df.columns:
            closest = decode_df.iloc[(decode_df['batch_size'] - batch_size).abs().argsort()[:1]]
            if len(closest) > 0:
                return closest['time_stats.attn_decode.median'].values[0]
    except Exception as e:
        print(f"  [WARN] Error loading profiling data: {e}")

    return None


def run_model_validation(config: ModelConfig, output_dir: Path) -> List[Dict]:
    """Run validation for a single model."""
    results = []

    print(f"\n{'='*80}")
    print(f"Validating: {config.name}")
    print(f"Model: {config.model_path}")
    print(f"{'='*80}")

    for batch_size in config.batch_sizes:
        for prefill_len in config.prefill_lengths:
            for decode_len in config.decode_lengths:
                print(f"\n[Config] batch={batch_size}, prefill={prefill_len}, decode={decode_len}")

                # Real GPU measurement
                real_result = measure_real_gpu(
                    config.model_path,
                    batch_size,
                    prefill_len,
                    decode_len,
                    config.num_iterations
                )

                # Vidur prediction
                vidur_pred = load_vidur_prediction(
                    config.profiling_name,
                    batch_size,
                    prefill_len,
                    decode_len
                )

                if real_result:
                    result = {
                        'model': config.name,
                        'batch_size': batch_size,
                        'prefill_length': prefill_len,
                        'decode_length': decode_len,
                        'kv_cache_size': batch_size * (prefill_len + decode_len),
                        'real_mean_ms': real_result['mean_ms'],
                        'real_std_ms': real_result['std_ms'],
                        'real_memory_mb': real_result['memory_mb'],
                        'vidur_pred_ms': vidur_pred,
                    }

                    if vidur_pred:
                        result['error_ms'] = real_result['mean_ms'] - vidur_pred
                        result['error_percent'] = (result['error_ms'] / real_result['mean_ms']) * 100
                        print(f"  Real: {real_result['mean_ms']:.2f}ms, "
                              f"Vidur: {vidur_pred:.2f}ms, "
                              f"Error: {result['error_percent']:.1f}%")
                    else:
                        print(f"  Real: {real_result['mean_ms']:.2f}ms, "
                              f"Vidur: N/A")

                    results.append(result)

    return results


def generate_comparison_report(all_results: List[Dict], output_dir: Path):
    """Generate comprehensive comparison report."""
    if not all_results:
        print("No results to report")
        return

    df = pd.DataFrame(all_results)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save raw data
    df.to_csv(output_dir / 'batch_validation_results.csv', index=False)

    # Generate plots
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Real vs Predicted by Model
    ax = axes[0, 0]
    for model in df['model'].unique():
        model_df = df[df['model'] == model].dropna(subset=['vidur_pred_ms'])
        if len(model_df) > 0:
            ax.scatter(model_df['real_mean_ms'], model_df['vidur_pred_ms'],
                      label=model, alpha=0.6, s=50)

    # Add diagonal line (perfect prediction)
    if 'real_mean_ms' in df.columns and 'vidur_pred_ms' in df.columns:
        valid_df = df.dropna(subset=['real_mean_ms', 'vidur_pred_ms'])
        if len(valid_df) > 0:
            max_val = max(valid_df['real_mean_ms'].max(), valid_df['vidur_pred_ms'].max())
            ax.plot([0, max_val], [0, max_val], 'r--', alpha=0.5, label='Perfect')

    ax.set_xlabel('Real GPU Time (ms)')
    ax.set_ylabel('Vidur Predicted (ms)')
    ax.set_title('Real vs Predicted by Model')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Error Distribution
    ax = axes[0, 1]
    error_df = df.dropna(subset=['error_percent'])
    if len(error_df) > 0:
        for model in error_df['model'].unique():
            model_errors = error_df[error_df['model'] == model]['error_percent']
            ax.hist(model_errors, bins=10, alpha=0.5, label=model)
        ax.set_xlabel('Prediction Error (%)')
        ax.set_ylabel('Count')
        ax.set_title('Prediction Error Distribution')
        ax.legend()
        ax.grid(True, alpha=0.3)

    # Plot 3: Time vs Batch Size
    ax = axes[1, 0]
    for model in df['model'].unique():
        model_df = df[df['model'] == model]
        ax.errorbar(model_df['batch_size'], model_df['real_mean_ms'],
                   yerr=model_df['real_std_ms'], label=model, marker='o', capsize=3)
    ax.set_xlabel('Batch Size')
    ax.set_ylabel('Iteration Time (ms)')
    ax.set_title('Iteration Time vs Batch Size')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: MAPE by Model
    ax = axes[1, 1]
    error_df = df.dropna(subset=['error_percent'])
    if len(error_df) > 0:
        mape_data = []
        models = []
        for model in error_df['model'].unique():
            model_errors = error_df[error_df['model'] == model]['error_percent'].abs()
            if len(model_errors) > 0:
                mape_data.append(model_errors.mean())
                models.append(model)

        if mape_data:
            ax.bar(models, mape_data)
            ax.set_ylabel('MAPE (%)')
            ax.set_title('Mean Absolute Percentage Error by Model')
            ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    plt.savefig(output_dir / 'batch_validation_analysis.png', dpi=300)
    plt.savefig(output_dir / 'batch_validation_analysis.pdf')

    # Generate summary report
    with open(output_dir / 'batch_validation_report.md', 'w') as f:
        f.write("# Batch GPU Validation Report\n\n")
        f.write("## Summary\n\n")

        error_df = df.dropna(subset=['error_percent'])
        if len(error_df) > 0:
            f.write(f"**Overall MAPE**: {error_df['error_percent'].abs().mean():.2f}%\n\n")

            f.write("**By Model:**\n\n")
            for model in error_df['model'].unique():
                model_df = error_df[error_df['model'] == model]
                mape = model_df['error_percent'].abs().mean()
                f.write(f"- {model}: MAPE = {mape:.2f}% (n={len(model_df)})\n")

        f.write("\n## Raw Data\n\n")
        f.write(df.to_markdown(index=False))

    print(f"\n{'='*80}")
    print("Batch Validation Complete!")
    print(f"Results saved to: {output_dir}")
    print(f"  - CSV: batch_validation_results.csv")
    print(f"  - Plots: batch_validation_analysis.png")
    print(f"  - Report: batch_validation_report.md")
    print(f"{'='*80}")


def main():
    parser = argparse.ArgumentParser(description='Batch GPU Validation')
    parser.add_argument('--models', nargs='+', choices=['qwen', 'llama2', 'llama3', 'all'],
                       default=['all'], help='Models to validate')
    parser.add_argument('--output-dir', type=str, default='outputs/batch_validation',
                       help='Output directory')

    args = parser.parse_args()

    if not HAS_GPU or not HAS_VLLM:
        print("ERROR: GPU or vLLM not available")
        sys.exit(1)

    # Define model configurations
    model_configs = []

    if 'qwen' in args.models or 'all' in args.models:
        if Path("~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Math-1.5B").expanduser().exists():
            model_configs.append(ModelConfig(
                name="Qwen-1.5B",
                model_path="Qwen/Qwen2.5-Math-1.5B",
                profiling_name="qwen",
                batch_sizes=[1, 2, 4, 8],
                prefill_lengths=[128, 256],
                decode_lengths=[20, 50],
                num_iterations=5
            ))

    if 'llama2' in args.models or 'all' in args.models:
        llama2_path = "models/modelscope/Llama-2-7b-ms"
        if Path(llama2_path).exists():
            # Check if complete
            if (Path(llama2_path) / "model-00001-of-00002.safetensors").exists():
                model_configs.append(ModelConfig(
                    name="Llama-2-7B",
                    model_path=llama2_path,
                    profiling_name="llama2-7b",
                    batch_sizes=[1, 2, 4, 8],
                    prefill_lengths=[256, 512],
                    decode_lengths=[20, 100],
                    num_iterations=5
                ))
            else:
                print(f"[WARN] Llama-2 model incomplete, skipping...")

    if 'llama3' in args.models or 'all' in args.models:
        # Llama-3 requires HuggingFace login
        print("[INFO] Llama-3 requires HuggingFace login, skipping...")

    if not model_configs:
        print("ERROR: No valid model configurations found")
        print("Available models:")
        print("  - Qwen: ~/.cache/huggingface/hub/models--Qwen--Qwen2.5-Math-1.5B")
        print("  - Llama-2: models/modelscope/Llama-2-7b-ms")
        sys.exit(1)

    print(f"\nRunning validation for {len(model_configs)} models:")
    for cfg in model_configs:
        print(f"  - {cfg.name}")

    # Run validation
    all_results = []
    for config in model_configs:
        results = run_model_validation(config, Path(args.output_dir))
        all_results.extend(results)

    # Generate report
    if all_results:
        generate_comparison_report(all_results, Path(args.output_dir))
    else:
        print("\nNo results generated!")


if __name__ == '__main__':
    main()
