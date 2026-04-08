#!/usr/bin/env python3
"""
WCP vs vLLM GPU Benchmark using actual vLLM inference

This runs real GPU inference comparing WCP-inspired scheduling vs vLLM default.
"""

import argparse
import json
import time
import os
import sys
from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass, asdict

import numpy as np
import torch
from vllm import LLM, SamplingParams


@dataclass
class BenchmarkConfig:
    model: str
    batch_sizes: List[int]
    prefill_lens: List[int]
    decode_len: int = 20
    num_iterations: int = 3
    output_dir: str = "outputs/wcp_vllm_benchmark"


def generate_prompt(prefill_len: int) -> str:
    base_text = "The quick brown fox jumps over the lazy dog. "
    words_needed = int(prefill_len / 0.75) + 10
    prompt = (base_text * (words_needed // 9 + 1))[:words_needed * 10]
    return prompt


def run_vllm_benchmark(config: BenchmarkConfig) -> List[Dict]:
    """Run benchmark with vLLM default scheduling"""
    print("\n" + "="*60)
    print("Running vLLM Default Benchmark")
    print("="*60)

    results = []

    for bs in config.batch_sizes:
        for pl in config.prefill_lens:
            print(f"\n  Config: batch={bs}, prefill={pl}")

            # Create vLLM engine
            llm = LLM(
                model=config.model,
                dtype="float16",
                max_model_len=4096,
                max_num_seqs=bs * 2,
                gpu_memory_utilization=0.85,
            )

            # Generate prompts
            prompt = generate_prompt(pl)
            prompts = [prompt] * bs

            sampling_params = SamplingParams(
                temperature=0.0,
                max_tokens=config.decode_len,
                ignore_eos=True,
            )

            # Warmup
            print("    Warmup...")
            _ = llm.generate(prompts[:1], sampling_params)
            torch.cuda.synchronize()

            # Benchmark
            print(f"    Benchmarking ({config.num_iterations} iterations)...")
            times = []
            for i in range(config.num_iterations):
                torch.cuda.synchronize()
                start = time.perf_counter()

                outputs = llm.generate(prompts, sampling_params)

                torch.cuda.synchronize()
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
                print(f"      Iter {i+1}: {elapsed:.2f} ms")

            memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

            results.append({
                "batch_size": bs,
                "prefill_len": pl,
                "mean_time_ms": np.mean(times),
                "std_time_ms": np.std(times),
                "memory_mb": memory_mb,
                "scheduler": "vllm_default",
            })

            print(f"    Mean: {np.mean(times):.2f} ms")

            del llm
            torch.cuda.empty_cache()

    return results


def run_wcp_benchmark(config: BenchmarkConfig) -> List[Dict]:
    """Run benchmark with WCP-inspired scheduling"""
    print("\n" + "="*60)
    print("Running WCP-Inspired Benchmark")
    print("="*60)
    print("Note: Using vLLM with constrained max_num_seqs to simulate WCP booking limit")

    results = []

    # WCP parameters
    tl = 21  # total_limit

    for bs in config.batch_sizes:
        for pl in config.prefill_lens:
            print(f"\n  Config: batch={bs}, prefill={pl}")

            # Simulate WCP by limiting max_num_seqs (booking limit concept)
            # In real WCP, this would be more sophisticated
            max_seqs = min(bs, tl) if bs <= tl else tl

            llm = LLM(
                model=config.model,
                dtype="float16",
                max_model_len=4096,
                max_num_seqs=max_seqs,  # WCP-inspired limit
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
            print("    Warmup...")
            _ = llm.generate(prompts[:1], sampling_params)
            torch.cuda.synchronize()

            # Benchmark
            print(f"    Benchmarking ({config.num_iterations} iterations)...")
            times = []
            for i in range(config.num_iterations):
                torch.cuda.synchronize()
                start = time.perf_counter()

                outputs = llm.generate(prompts, sampling_params)

                torch.cuda.synchronize()
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
                print(f"      Iter {i+1}: {elapsed:.2f} ms")

            memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

            results.append({
                "batch_size": bs,
                "prefill_len": pl,
                "mean_time_ms": np.mean(times),
                "std_time_ms": np.std(times),
                "memory_mb": memory_mb,
                "scheduler": "wcp_inspired",
                "wcp_tl": tl,
            })

            print(f"    Mean: {np.mean(times):.2f} ms")

            del llm
            torch.cuda.empty_cache()

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/modelscope/Llama-2-7b-ms")
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 4, 8, 16])
    parser.add_argument("--prefill-lens", type=int, nargs="+", default=[256, 512])
    parser.add_argument("--decode-len", type=int, default=20)
    parser.add_argument("--num-iterations", type=int, default=3)
    parser.add_argument("--output", default="outputs/wcp_vllm_benchmark")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("Error: CUDA not available")
        sys.exit(1)

    print(f"GPU: {torch.cuda.get_device_name(0)}")

    config = BenchmarkConfig(
        model=args.model,
        batch_sizes=args.batch_sizes,
        prefill_lens=args.prefill_lens,
        decode_len=args.decode_len,
        num_iterations=args.num_iterations,
        output_dir=args.output,
    )

    # Run benchmarks
    vllm_results = run_vllm_benchmark(config)
    wcp_results = run_wcp_benchmark(config)

    # Compare
    comparisons = []
    for v, w in zip(vllm_results, wcp_results):
        improvement = (v["mean_time_ms"] - w["mean_time_ms"]) / v["mean_time_ms"] * 100
        comparisons.append({
            "batch_size": v["batch_size"],
            "prefill_len": v["prefill_len"],
            "vllm_time_ms": v["mean_time_ms"],
            "wcp_time_ms": w["mean_time_ms"],
            "improvement_pct": improvement,
        })

    improvements = [c["improvement_pct"] for c in comparisons]
    overall = {
        "mean_improvement_pct": np.mean(improvements),
        "wcp_wins": sum(1 for i in improvements if i > 0),
        "vllm_wins": sum(1 for i in improvements if i < 0),
    }

    # Save results
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    results = {
        "config": asdict(config),
        "vllm_results": vllm_results,
        "wcp_results": wcp_results,
        "comparison": {"comparisons": comparisons, "overall": overall},
    }

    with open(output_path / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print("\n" + "="*60)
    print("Benchmark Complete!")
    print(f"Mean Improvement: {overall['mean_improvement_pct']:+.2f}%")
    print(f"WCP Wins: {overall['wcp_wins']}")
    print(f"vLLM Wins: {overall['vllm_wins']}")


if __name__ == "__main__":
    main()
