#!/usr/bin/env python3
"""
WCP High Load Test - Test where WCP should win

Based on Vidur paper findings:
- Higher arrival rates (60, 80, 100+)
- Multi-type workload (W3: 70% p512d20 + 30% p512d50)
- Test stability under pressure
"""

import json
import time
import sys
import math
import random
from pathlib import Path
from typing import List, Dict, Tuple

import numpy as np
import torch
from vllm import LLM, SamplingParams


def generate_prompt(prefill_len: int) -> str:
    base_text = "The quick brown fox jumps over the lazy dog. "
    words_needed = int(prefill_len / 0.75) + 10
    prompt = (base_text * (words_needed // 9 + 1))[:words_needed * 10]
    return prompt


def generate_w3_requests(arrival_rate: float, num_requests: int) -> List[Tuple]:
    """Generate W3 workload: 70% p512d20 + 30% p512d50"""
    random.seed(42)
    requests = []
    current_time = 0.0

    for _ in range(num_requests):
        inter_arrival = -math.log(1.0 - random.random()) / arrival_rate
        current_time += inter_arrival

        # 70% short, 30% long
        if random.random() < 0.7:
            prefill, decode = 512, 20
        else:
            prefill, decode = 512, 50

        prompt = generate_prompt(prefill)
        requests.append((current_time, prompt, decode))

    return requests


def benchmark_w3(
    model_path: str,
    arrival_rate: float,
    num_requests: int,
    tl: int,
    cs: int,
    is_wcp: bool
) -> Dict:
    """Run W3 benchmark"""

    requests = generate_w3_requests(arrival_rate, num_requests)

    # Create LLM
    if is_wcp:
        max_seqs = min(32, tl)
        max_tokens = cs * max_seqs
        name = f"WCP(tl={tl},cs={cs})"
    else:
        max_seqs = 64
        max_tokens = 8192
        name = "vLLM Default"

    print(f"\n  Testing {name}...")
    print(f"    max_seqs={max_seqs}, max_tokens={max_tokens}")

    llm = LLM(
        model=model_path,
        dtype="float16",
        max_model_len=4096,
        max_num_seqs=max_seqs,
        max_num_batched_tokens=max_tokens,
        gpu_memory_utilization=0.55,
    )

    # Warmup
    _ = llm.generate(generate_prompt(256), SamplingParams(max_tokens=20))
    torch.cuda.synchronize()

    # Benchmark
    latencies = []
    start_time = time.perf_counter()

    for i, (arrival_time, prompt, decode_len) in enumerate(requests):
        current_elapsed = time.perf_counter() - start_time
        wait_time = arrival_time - current_elapsed
        if wait_time > 0:
            time.sleep(wait_time)

        request_start = time.perf_counter()
        _ = llm.generate(prompt, SamplingParams(max_tokens=decode_len, ignore_eos=True))
        request_end = time.perf_counter()
        latencies.append((request_end - request_start) * 1000)

        if (i + 1) % 100 == 0:
            recent = latencies[-100:]
            print(f"      {i+1}/{num_requests}: mean={np.mean(recent):.1f}ms, p99={np.percentile(recent, 99):.1f}ms")

    total_time = time.perf_counter() - start_time

    result = {
        "mean_ms": float(np.mean(latencies)),
        "p99_ms": float(np.percentile(latencies, 99)),
        "max_ms": float(np.max(latencies)),
        "throughput": num_requests / total_time,
    }

    print(f"    Mean: {result['mean_ms']:.2f}ms")
    print(f"    P99: {result['p99_ms']:.2f}ms")
    print(f"    Max: {result['max_ms']:.2f}ms")

    del llm
    torch.cuda.empty_cache()

    return result


def main():
    model = "models/modelscope/Llama-2-7b-ms"

    # High arrival rates where WCP should shine
    rates = [40, 60, 80, 100]
    num_requests = 500

    # Test configs
    configs = [
        {"name": "vLLM", "tl": 0, "cs": 0, "is_wcp": False},
        {"name": "WCP_cs256_tl21", "tl": 21, "cs": 256, "is_wcp": True},
        {"name": "WCP_cs192_tl30", "tl": 30, "cs": 192, "is_wcp": True},
        {"name": "WCP_cs128_tl40", "tl": 40, "cs": 128, "is_wcp": True},
        {"name": "WCP_cs96_tl50", "tl": 50, "cs": 96, "is_wcp": True},
    ]

    results = {"rates": []}

    for rate in rates:
        print(f"\n{'='*70}")
        print(f"W3 Workload - Arrival Rate: {rate} req/s")
        print(f"{'='*70}")

        rate_results = {"arrival_rate": rate, "configs": []}

        for config in configs:
            result = benchmark_w3(
                model, rate, num_requests,
                config["tl"], config["cs"], config["is_wcp"]
            )
            rate_results["configs"].append({
                "name": config["name"],
                **result
            })

        results["rates"].append(rate_results)

    # Find winners
    print("\n" + "="*70)
    print("FINAL RESULTS - W3 Workload")
    print("="*70)

    for r in results["rates"]:
        print(f"\nRate: {r['arrival_rate']} req/s")

        baseline = next(c for c in r["configs"] if c["name"] == "vLLM")
        print(f"  vLLM: mean={baseline['mean_ms']:.1f}ms, p99={baseline['p99_ms']:.1f}ms")

        best_wcp = None
        best_improvement = -999

        for c in r["configs"]:
            if c["name"] != "vLLM":
                improvement = (baseline["mean_ms"] - c["mean_ms"]) / baseline["mean_ms"] * 100
                p99_improvement = (baseline["p99_ms"] - c["p99_ms"]) / baseline["p99_ms"] * 100
                print(f"  {c['name']}: mean={c['mean_ms']:.1f}ms ({improvement:+.1f}%), p99={c['p99_ms']:.1f}ms ({p99_improvement:+.1f}%)")

                if improvement > best_improvement:
                    best_improvement = improvement
                    best_wcp = c

        if best_wcp and best_improvement > 0:
            print(f"  🏆 WINNER: {best_wcp['name']} ({best_improvement:+.1f}%)")
        else:
            print(f"  ❌ No winner (best: {best_improvement:+.1f}%)")

    # Save
    output_path = Path("outputs/wcp_high_load")
    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}/results.json")


if __name__ == "__main__":
    main()
