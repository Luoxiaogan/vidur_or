#!/usr/bin/env python3
"""
WCP vs vLLM Real GPU Benchmark using SGLang Adapter

This runs actual GPU inference comparing WCP vs vLLM default scheduling.
Uses monkey-patching to inject WCP without modifying SGLang source code.
"""

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List

import numpy as np
import torch

sys.path.insert(0, "/home/archer/vidur_or")
from scripts.sglang_wcp_adapter import enable_wcp, disable_wcp, get_wcp_stats


@dataclass
class BenchmarkConfig:
    model: str
    batch_sizes: List[int]
    prefill_lens: List[int]
    decode_len: int = 20
    num_iterations: int = 3
    warmup_iterations: int = 1
    output_dir: str = "outputs/wcp_real_gpu_benchmark"
    wcp_tl: int = 21
    wcp_cs: int = 256


def generate_prompt(prefill_len: int) -> str:
    base_text = "The quick brown fox jumps over the lazy dog. "
    words_needed = int(prefill_len / 0.75) + 10
    prompt = (base_text * (words_needed // 9 + 1))[:words_needed * 10]
    return prompt


def benchmark_config(engine, batch_size, prefill_len, decode_len, num_iterations, warmup_iterations):
    prompt = generate_prompt(prefill_len)
    prompts = [prompt] * batch_size

    sampling_params = {
        "temperature": 0.0,
        "max_new_tokens": decode_len,
        "ignore_eos": True,
    }

    # Warmup
    for _ in range(warmup_iterations):
        _ = engine.generate(prompts[0], sampling_params)
        torch.cuda.synchronize()

    # Benchmark
    times = []
    for i in range(num_iterations):
        torch.cuda.synchronize()
        start_time = time.perf_counter()

        for p in prompts:
            _ = engine.generate(p, sampling_params)

        torch.cuda.synchronize()
        iteration_time_ms = (time.perf_counter() - start_time) * 1000
        times.append(iteration_time_ms)
        print(f"      Iter {i+1}: {iteration_time_ms:.2f} ms")

    memory_allocated = torch.cuda.max_memory_allocated() / 1024 / 1024

    return {
        "mean_time_ms": np.mean(times),
        "std_time_ms": np.std(times),
        "memory_mb": memory_allocated,
        "throughput": batch_size / (np.mean(times) / 1000),
    }


def run_vllm_benchmark(config):
    import sglang as sgl

    print("\n" + "="*60)
    print("Running vLLM Default Benchmark")
    print("="*60)

    disable_wcp()
    print("[Status] WCP disabled, using vLLM default scheduling")

    results = []

    for bs in config.batch_sizes:
        for pl in config.prefill_lens:
            print(f"\n  Config: batch={bs}, prefill={pl}")

            engine = sgl.Engine(
                model_path=config.model,
                tp_size=1,
                dtype="float16",
                context_length=4096,
            )

            result = benchmark_config(engine, bs, pl, config.decode_len,
                                     config.num_iterations, config.warmup_iterations)
            result["batch_size"] = bs
            result["prefill_len"] = pl
            result["scheduler"] = "vllm"
            results.append(result)

            print(f"    Mean: {result['mean_time_ms']:.2f} ms")

            del engine
            torch.cuda.empty_cache()

    return results


def run_wcp_benchmark(config):
    import sglang as sgl

    print("\n" + "="*60)
    print("Running WCP Benchmark")
    print("="*60)

    success = enable_wcp(tl=config.wcp_tl, cs=config.wcp_cs)
    if not success:
        print("[Error] Failed to enable WCP")
        return []

    print(f"[Status] WCP enabled: tl={config.wcp_tl}, cs={config.wcp_cs}")

    results = []

    for bs in config.batch_sizes:
        for pl in config.prefill_lens:
            print(f"\n  Config: batch={bs}, prefill={pl}")

            engine = sgl.Engine(
                model_path=config.model,
                tp_size=1,
                dtype="float16",
                context_length=4096,
            )

            result = benchmark_config(engine, bs, pl, config.decode_len,
                                     config.num_iterations, config.warmup_iterations)
            result["batch_size"] = bs
            result["prefill_len"] = pl
            result["scheduler"] = "wcp"
            result["wcp_stats"] = get_wcp_stats()
            results.append(result)

            print(f"    Mean: {result['mean_time_ms']:.2f} ms")

            del engine
            torch.cuda.empty_cache()

    disable_wcp()
    return results


def compare_results(vllm_results, wcp_results):
    comparisons = []

    for v in vllm_results:
        w = next((x for x in wcp_results if x["batch_size"] == v["batch_size"]
                 and x["prefill_len"] == v["prefill_len"]), None)
        if w:
            improvement = (v["mean_time_ms"] - w["mean_time_ms"]) / v["mean_time_ms"] * 100
            comparisons.append({
                "batch_size": v["batch_size"],
                "prefill_len": v["prefill_len"],
                "vllm_time_ms": v["mean_time_ms"],
                "wcp_time_ms": w["mean_time_ms"],
                "improvement_pct": improvement,
            })

    improvements = [c["improvement_pct"] for c in comparisons]
    return {
        "comparisons": comparisons,
        "overall": {
            "mean_improvement_pct": np.mean(improvements) if improvements else 0,
            "wcp_wins": sum(1 for i in improvements if i > 0),
            "vllm_wins": sum(1 for i in improvements if i < 0),
        }
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="models/modelscope/Llama-2-7b-ms")
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 4, 8])
    parser.add_argument("--prefill-lens", type=int, nargs="+", default=[256, 512])
    parser.add_argument("--decode-len", type=int, default=20)
    parser.add_argument("--num-iterations", type=int, default=3)
    parser.add_argument("--wcp-tl", type=int, default=21)
    parser.add_argument("--wcp-cs", type=int, default=256)
    parser.add_argument("--output", default="outputs/wcp_real_gpu_benchmark")
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
        wcp_tl=args.wcp_tl,
        wcp_cs=args.wcp_cs,
    )

    vllm_results = run_vllm_benchmark(config)
    wcp_results = run_wcp_benchmark(config)

    comparison = compare_results(vllm_results, wcp_results)

    all_results = {
        "config": asdict(config),
        "vllm_results": vllm_results,
        "wcp_results": wcp_results,
        "comparison": comparison,
    }

    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print("\n" + "="*60)
    print("Benchmark Complete!")
    print(f"Mean Improvement: {comparison['overall']['mean_improvement_pct']:+.2f}%")
    print(f"WCP Wins: {comparison['overall']['wcp_wins']}")


if __name__ == "__main__":
    main()
