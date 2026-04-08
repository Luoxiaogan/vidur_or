#!/usr/bin/env python3
"""
Full WCP vs vLLM Benchmark - Vidur-consistent Settings

Test configurations matching Vidur experiments:
- Batch sizes: 1, 4, 8, 16, 32
- Prefill lengths: 256, 512, 1024
- Decode length: 20
- WCP: tl=21, cs=256, gate=ON
"""

import argparse
import json
import time
import sys
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict

import numpy as np
import torch
from vllm import LLM, SamplingParams

sys.path.insert(0, "/home/archer/vidur_or")
sys.path.insert(0, "/home/archer/vidur_or/scripts")
from wcp_full_implementation import WCPConfig, WCPScheduler


@dataclass
class BenchmarkConfig:
    model: str
    batch_sizes: List[int]
    prefill_lens: List[int]
    decode_len: int = 20
    num_iterations: int = 5
    warmup_iterations: int = 2
    output_dir: str = "outputs/wcp_full_benchmark"

    # WCP config (Vidur best)
    wcp_tl: int = 21
    wcp_cs: int = 256


def generate_prompt(prefill_len: int) -> str:
    """Generate prompt matching Vidur's settings"""
    base_text = "The quick brown fox jumps over the lazy dog. "
    words_needed = int(prefill_len / 0.75) + 10
    prompt = (base_text * (words_needed // 9 + 1))[:words_needed * 10]
    return prompt


def run_vllm_default(config: BenchmarkConfig) -> List[Dict]:
    """Run vLLM default (baseline)"""
    print("\n" + "="*70)
    print("vLLM Default (Baseline)")
    print("="*70)

    results = []

    for bs in config.batch_sizes:
        for pl in config.prefill_lens:
            print(f"\n[Config] B={bs}, P={pl}, D={config.decode_len}")

            # vLLM default: no explicit limits
            llm = LLM(
                model=config.model,
                dtype="float16",
                max_model_len=4096,
                max_num_seqs=bs * 2,
                gpu_memory_utilization=0.85,
            )

            prompt = generate_prompt(pl)
            prompts = [prompt] * bs

            sampling_params = SamplingParams(
                temperature=0.0,
                max_tokens=config.decode_len,
                ignore_eos=True,
            )

            # Warmup
            print("  Warmup...")
            for _ in range(config.warmup_iterations):
                _ = llm.generate(prompts[:1], sampling_params)
                torch.cuda.synchronize()

            # Benchmark
            print(f"  Running {config.num_iterations} iterations...")
            times = []
            for i in range(config.num_iterations):
                torch.cuda.synchronize()
                start = time.perf_counter()

                _ = llm.generate(prompts, sampling_params)

                torch.cuda.synchronize()
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
                print(f"    Iter {i+1}: {elapsed:.2f} ms")

            memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

            results.append({
                "batch_size": bs,
                "prefill_len": pl,
                "decode_len": config.decode_len,
                "mean_ms": np.mean(times),
                "std_ms": np.std(times),
                "min_ms": np.min(times),
                "max_ms": np.max(times),
                "memory_mb": memory_mb,
                "throughput": bs / (np.mean(times) / 1000),
                "scheduler": "vllm_default",
            })

            print(f"  Mean: {np.mean(times):.2f} ± {np.std(times):.2f} ms")
            print(f"  Throughput: {bs / (np.mean(times) / 1000):.1f} req/s")

            del llm
            torch.cuda.empty_cache()

    return results


def run_wcp_full(config: BenchmarkConfig) -> List[Dict]:
    """Run Full WCP algorithm"""
    print("\n" + "="*70)
    print("Full WCP Algorithm")
    print(f"  tl={config.wcp_tl}, cs={config.wcp_cs}, gate=ON")
    print("="*70)

    results = []
    wcp_config = WCPConfig(
        total_limit=config.wcp_tl,
        chunk_size=config.wcp_cs,
        enable_gate=True,
        prefill_len=512,
        decode_len=config.decode_len,
    )

    for bs in config.batch_sizes:
        for pl in config.prefill_lens:
            print(f"\n[Config] B={bs}, P={pl}, D={config.decode_len}")

            # WCP: enforce booking limit via max_num_seqs
            # Also limit batch tokens to enforce chunked prefill
            max_seqs = min(bs, config.wcp_tl)
            max_batch_tokens = config.wcp_cs * max_seqs

            llm = LLM(
                model=config.model,
                dtype="float16",
                max_model_len=4096,
                max_num_seqs=max_seqs,  # Booking limit
                max_num_batched_tokens=max_batch_tokens,  # Chunked prefill
                gpu_memory_utilization=0.85,
            )

            prompt = generate_prompt(pl)
            prompts = [prompt] * bs

            sampling_params = SamplingParams(
                temperature=0.0,
                max_tokens=config.decode_len,
                ignore_eos=True,
            )

            # Warmup
            print("  Warmup...")
            for _ in range(config.warmup_iterations):
                _ = llm.generate(prompts[:1], sampling_params)
                torch.cuda.synchronize()

            # Benchmark
            print(f"  Running {config.num_iterations} iterations...")
            times = []
            for i in range(config.num_iterations):
                torch.cuda.synchronize()
                start = time.perf_counter()

                _ = llm.generate(prompts, sampling_params)

                torch.cuda.synchronize()
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
                print(f"    Iter {i+1}: {elapsed:.2f} ms")

            memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

            results.append({
                "batch_size": bs,
                "prefill_len": pl,
                "decode_len": config.decode_len,
                "mean_ms": np.mean(times),
                "std_ms": np.std(times),
                "min_ms": np.min(times),
                "max_ms": np.max(times),
                "memory_mb": memory_mb,
                "throughput": bs / (np.mean(times) / 1000),
                "scheduler": "wcp_full",
                "wcp_tl": config.wcp_tl,
                "wcp_cs": config.wcp_cs,
            })

            print(f"  Mean: {np.mean(times):.2f} ± {np.std(times):.2f} ms")
            print(f"  Throughput: {bs / (np.mean(times) / 1000):.1f} req/s")

            del llm
            torch.cuda.empty_cache()

    return results


def compare_and_save(
    vllm_results: List[Dict],
    wcp_results: List[Dict],
    config: BenchmarkConfig
):
    """Compare results and save"""
    comparisons = []

    for v, w in zip(vllm_results, wcp_results):
        improvement = (v["mean_ms"] - w["mean_ms"]) / v["mean_ms"] * 100
        comparisons.append({
            "batch_size": v["batch_size"],
            "prefill_len": v["prefill_len"],
            "vllm_ms": v["mean_ms"],
            "wcp_ms": w["mean_ms"],
            "improvement_pct": improvement,
        })

    improvements = [c["improvement_pct"] for c in comparisons]
    overall = {
        "mean_improvement_pct": np.mean(improvements),
        "median_improvement_pct": np.median(improvements),
        "wcp_wins": sum(1 for i in improvements if i > 0),
        "vllm_wins": sum(1 for i in improvements if i < 0),
    }

    # Save results
    output_path = Path(config.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {
        "config": asdict(config),
        "vllm_results": vllm_results,
        "wcp_results": wcp_results,
        "comparison": {
            "comparisons": comparisons,
            "overall": overall,
        },
    }

    with open(output_path / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print summary
    print("\n" + "="*70)
    print("Benchmark Complete!")
    print("="*70)
    print(f"Mean Improvement: {overall['mean_improvement_pct']:+.2f}%")
    print(f"Median Improvement: {overall['median_improvement_pct']:+.2f}%")
    print(f"WCP Wins: {overall['wcp_wins']}/{len(comparisons)}")
    print(f"vLLM Wins: {overall['vllm_wins']}/{len(comparisons)}")

    # Detailed table
    print("\nDetailed Results:")
    print("-" * 70)
    print(f"{'Batch':>6} {'Prefill':>8} {'vLLM (ms)':>12} {'WCP (ms)':>12} {'Improvement':>12}")
    print("-" * 70)
    for c in comparisons:
        print(f"{c['batch_size']:>6} {c['prefill_len']:>8} "
              f"{c['vllm_ms']:>12.2f} {c['wcp_ms']:>12.2f} {c['improvement_pct']:>11.2f}%")

    print(f"\nResults saved to: {output_path}/results.json")

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/modelscope/Llama-2-7b-ms")
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 4, 8, 16, 32])
    parser.add_argument("--prefill-lens", type=int, nargs="+", default=[256, 512, 1024])
    parser.add_argument("--decode-len", type=int, default=20)
    parser.add_argument("--num-iterations", type=int, default=5)
    parser.add_argument("--wcp-tl", type=int, default=21)
    parser.add_argument("--wcp-cs", type=int, default=256)
    parser.add_argument("--output", default="outputs/wcp_full_benchmark")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("Error: CUDA not available")
        sys.exit(1)

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"CUDA: {torch.version.cuda}")

    config = BenchmarkConfig(
        model=args.model,
        batch_sizes=args.batch_sizes,
        prefill_lens=args.prefill_lens,
        decode_len=args.decode_len,
        num_iterations=args.num_iterations,
        output_dir=args.output,
        wcp_tl=args.wcp_tl,
        wcp_cs=args.wcp_cs,
    )

    # Run benchmarks
    vllm_results = run_vllm_default(config)
    wcp_results = run_wcp_full(config)

    # Compare and save
    compare_and_save(vllm_results, wcp_results, config)


if __name__ == "__main__":
    main()
