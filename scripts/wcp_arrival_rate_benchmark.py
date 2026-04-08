#!/usr/bin/env python3
"""
WCP vs vLLM Benchmark with Arrival Rate (Vidur-style)

Key difference from previous benchmark:
- Requests arrive according to Poisson process (not fixed batch)
- Test different arrival rates (e.g., 12, 16, 20, 24 req/s)
- Measure mean latency and P99 latency
- Run for fixed number of requests or fixed duration

Usage:
    python scripts/wcp_arrival_rate_benchmark.py \
        --model models/modelscope/Llama-2-7b-ms \
        --rates 12 16 20 24 \
        --workload W3 \
        --num-requests 500
"""

import argparse
import json
import time
import sys
import math
import random
from pathlib import Path
from typing import List, Dict, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np
import torch
from vllm import LLM, SamplingParams


@dataclass
class WorkloadConfig:
    """Workload configuration matching Vidur"""
    name: str
    types: List[Dict]  # Each type has prefill, decode, arrival_rate_frac


# Vidur workload definitions
WORKLOADS = {
    "W3": WorkloadConfig(
        name="W3",
        types=[
            {"prefill": 512, "decode": 20, "arrival_rate_frac": 0.7},
            {"prefill": 512, "decode": 50, "arrival_rate_frac": 0.3},
        ]
    ),
    "W1": WorkloadConfig(
        name="W1",
        types=[
            {"prefill": 256, "decode": 10, "arrival_rate_frac": 0.7},
            {"prefill": 512, "decode": 50, "arrival_rate_frac": 0.3},
        ]
    ),
    "single": WorkloadConfig(
        name="single",
        types=[
            {"prefill": 512, "decode": 20, "arrival_rate_frac": 1.0},
        ]
    ),
}


def generate_prompt(prefill_len: int) -> str:
    """Generate prompt with specific token length"""
    base_text = "The quick brown fox jumps over the lazy dog. "
    words_needed = int(prefill_len / 0.75) + 10
    prompt = (base_text * (words_needed // 9 + 1))[:words_needed * 10]
    return prompt


def generate_requests_arrival_pattern(
    workload: WorkloadConfig,
    arrival_rate: float,  # requests per second
    num_requests: int,
    seed: int = 42
) -> List[Tuple[float, str, int, int]]:
    """
    Generate requests with Poisson arrival pattern

    Returns list of (arrival_time, prompt, prefill_len, decode_len)
    """
    random.seed(seed)

    requests = []
    current_time = 0.0

    # Generate inter-arrival times using exponential distribution
    for _ in range(num_requests):
        # Poisson process: inter-arrival time ~ Exp(rate)
        inter_arrival = -math.log(1.0 - random.random()) / arrival_rate
        current_time += inter_arrival

        # Select request type based on arrival_rate_frac
        rand = random.random()
        cumulative = 0.0
        selected_type = workload.types[0]
        for t in workload.types:
            cumulative += t["arrival_rate_frac"]
            if rand <= cumulative:
                selected_type = t
                break

        prompt = generate_prompt(selected_type["prefill"])
        requests.append((
            current_time,
            prompt,
            selected_type["prefill"],
            selected_type["decode"]
        ))

    return requests


def run_arrival_rate_benchmark_vllm(
    model_path: str,
    workload: WorkloadConfig,
    arrival_rate: float,
    num_requests: int,
    use_wcp: bool = False,
    wcp_tl: int = 21,
    wcp_cs: int = 256,
) -> Dict:
    """
    Run benchmark with specific arrival rate

    This simulates requests arriving over time and being processed
    """
    print(f"\n{'='*70}")
    print(f"Arrival Rate: {arrival_rate} req/s | Workload: {workload.name}")
    print(f"Scheduler: {'WCP' if use_wcp else 'vLLM Default'}")
    if use_wcp:
        print(f"WCP Config: tl={wcp_tl}, cs={wcp_cs}")
    print(f"{'='*70}")

    # Generate arrival pattern
    requests = generate_requests_arrival_pattern(
        workload, arrival_rate, num_requests
    )
    print(f"Generated {len(requests)} requests")
    print(f"Total duration: {requests[-1][0]:.2f}s")

    # Create vLLM engine
    if use_wcp:
        # WCP: limit concurrent requests
        max_seqs = min(32, wcp_tl)
        max_batch_tokens = wcp_cs * max_seqs
    else:
        max_seqs = 64
        max_batch_tokens = 8192

    print(f"Creating engine (max_seqs={max_seqs})...")
    llm = LLM(
        model=model_path,
        dtype="float16",
        max_model_len=4096,
        max_num_seqs=max_seqs,
        max_num_batched_tokens=max_batch_tokens,
        gpu_memory_utilization=0.85,
    )

    # Warmup
    print("Warmup...")
    warmup_prompt = generate_prompt(256)
    _ = llm.generate(warmup_prompt, SamplingParams(max_tokens=20))
    torch.cuda.synchronize()

    # Run benchmark
    print(f"Running benchmark ({num_requests} requests)...")

    latencies = []
    start_time = time.perf_counter()

    # Process requests as they "arrive"
    # In real scenario, requests arrive over time
    # Here we simulate by submitting them with delays

    for i, (arrival_time, prompt, prefill_len, decode_len) in enumerate(requests):
        # Wait until this request should arrive
        current_elapsed = time.perf_counter() - start_time
        wait_time = arrival_time - current_elapsed
        if wait_time > 0:
            time.sleep(wait_time)

        # Submit request and measure latency
        request_start = time.perf_counter()

        output = llm.generate(
            prompt,
            SamplingParams(max_tokens=decode_len, ignore_eos=True)
        )

        request_end = time.perf_counter()
        latency_ms = (request_end - request_start) * 1000
        latencies.append(latency_ms)

        if (i + 1) % 100 == 0:
            print(f"  Completed {i+1}/{num_requests} requests, "
                  f"mean latency: {np.mean(latencies[-100:]):.2f}ms")

    total_time = time.perf_counter() - start_time

    # Calculate metrics
    latencies = np.array(latencies)
    metrics = {
        "arrival_rate": arrival_rate,
        "num_requests": num_requests,
        "total_time_sec": total_time,
        "scheduler": "wcp" if use_wcp else "vllm_default",
        "mean_latency_ms": float(np.mean(latencies)),
        "p50_latency_ms": float(np.percentile(latencies, 50)),
        "p99_latency_ms": float(np.percentile(latencies, 99)),
        "std_latency_ms": float(np.std(latencies)),
        "min_latency_ms": float(np.min(latencies)),
        "max_latency_ms": float(np.max(latencies)),
        "throughput_req_per_sec": num_requests / total_time,
    }

    if use_wcp:
        metrics["wcp_tl"] = wcp_tl
        metrics["wcp_cs"] = wcp_cs

    print(f"\nResults:")
    print(f"  Mean Latency: {metrics['mean_latency_ms']:.2f}ms")
    print(f"  P99 Latency: {metrics['p99_latency_ms']:.2f}ms")
    print(f"  Throughput: {metrics['throughput_req_per_sec']:.2f} req/s")
    print(f"  Total Time: {total_time:.2f}s")

    del llm
    torch.cuda.empty_cache()

    return metrics


def run_rate_sweep(
    model_path: str,
    workload_name: str,
    rates: List[float],
    num_requests: int,
    wcp_tl: int = 21,
    wcp_cs: int = 256,
) -> Dict:
    """Run benchmark across multiple arrival rates"""

    workload = WORKLOADS[workload_name]

    results = {
        "workload": workload_name,
        "model": model_path,
        "num_requests": num_requests,
        "rates": [],
    }

    for rate in rates:
        print(f"\n{'#'*70}")
        print(f"# Testing Arrival Rate: {rate} req/s")
        print(f"{'#'*70}")

        # vLLM Default
        vllm_result = run_arrival_rate_benchmark_vllm(
            model_path, workload, rate, num_requests,
            use_wcp=False
        )

        # WCP
        wcp_result = run_arrival_rate_benchmark_vllm(
            model_path, workload, rate, num_requests,
            use_wcp=True, wcp_tl=wcp_tl, wcp_cs=wcp_cs
        )

        # Calculate improvement
        improvement = (
            vllm_result["mean_latency_ms"] - wcp_result["mean_latency_ms"]
        ) / vllm_result["mean_latency_ms"] * 100

        p99_improvement = (
            vllm_result["p99_latency_ms"] - wcp_result["p99_latency_ms"]
        ) / vllm_result["p99_latency_ms"] * 100

        results["rates"].append({
            "arrival_rate": rate,
            "vllm": vllm_result,
            "wcp": wcp_result,
            "mean_improvement_pct": improvement,
            "p99_improvement_pct": p99_improvement,
        })

        print(f"\n{'='*70}")
        print(f"Rate {rate} req/s Summary:")
        print(f"  Mean Latency: {vllm_result['mean_latency_ms']:.2f}ms -> "
              f"{wcp_result['mean_latency_ms']:.2f}ms ({improvement:+.1f}%)")
        print(f"  P99 Latency: {vllm_result['p99_latency_ms']:.2f}ms -> "
              f"{wcp_result['p99_latency_ms']:.2f}ms ({p99_improvement:+.1f}%)")
        print(f"{'='*70}")

    return results


def main():
    parser = argparse.ArgumentParser(
        description="WCP vs vLLM with Arrival Rate (Vidur-style)"
    )
    parser.add_argument("--model", default="models/modelscope/Llama-2-7b-ms")
    parser.add_argument("--rates", type=float, nargs="+",
                        default=[12, 16, 20, 24],
                        help="Arrival rates to test (req/s)")
    parser.add_argument("--workload", default="single",
                        choices=["W1", "W2", "W3", "single"],
                        help="Workload type")
    parser.add_argument("--num-requests", type=int, default=500,
                        help="Number of requests to generate")
    parser.add_argument("--wcp-tl", type=int, default=21)
    parser.add_argument("--wcp-cs", type=int, default=256)
    parser.add_argument("--output", default="outputs/wcp_arrival_rate")
    args = parser.parse_args()

    if not torch.cuda.is_available():
        print("Error: CUDA not available")
        sys.exit(1)

    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"Workload: {args.workload}")
    print(f"Arrival Rates: {args.rates} req/s")
    print(f"Num Requests: {args.num_requests}")

    # Run rate sweep
    results = run_rate_sweep(
        args.model,
        args.workload,
        args.rates,
        args.num_requests,
        args.wcp_tl,
        args.wcp_cs,
    )

    # Save results
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    with open(output_path / "arrival_rate_results.json", "w") as f:
        json.dump(results, f, indent=2)

    # Print final summary
    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"{'Rate':>8} {'vLLM Mean':>12} {'WCP Mean':>12} {'Improvement':>12}")
    print("-"*70)

    for r in results["rates"]:
        print(f"{r['arrival_rate']:>8.0f} "
              f"{r['vllm']['mean_latency_ms']:>12.2f} "
              f"{r['wcp']['mean_latency_ms']:>12.2f} "
              f"{r['mean_improvement_pct']:>11.1f}%")

    mean_improvement = np.mean([r["mean_improvement_pct"] for r in results["rates"]])
    print("-"*70)
    print(f"Mean Improvement: {mean_improvement:+.2f}%")
    print(f"Results saved to: {output_path}/arrival_rate_results.json")


if __name__ == "__main__":
    main()
