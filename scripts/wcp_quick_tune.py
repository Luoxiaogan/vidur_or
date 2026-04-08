#!/usr/bin/env python3
"""
Quick WCP Tuning - Test key configs from Vidur paper
"""

import json
import time
import sys
import math
import random
from pathlib import Path
from typing import List, Dict

import numpy as np
import torch
from vllm import LLM, SamplingParams


def generate_prompt(prefill_len: int) -> str:
    base_text = "The quick brown fox jumps over the lazy dog. "
    words_needed = int(prefill_len / 0.75) + 10
    prompt = (base_text * (words_needed // 9 + 1))[:words_needed * 10]
    return prompt


def generate_requests(arrival_rate: float, num_requests: int, prefill_len: int):
    """Generate Poisson arrival requests"""
    random.seed(42)
    requests = []
    current_time = 0.0

    for _ in range(num_requests):
        inter_arrival = -math.log(1.0 - random.random()) / arrival_rate
        current_time += inter_arrival
        prompt = generate_prompt(prefill_len)
        requests.append((current_time, prompt))

    return requests


def benchmark(
    model_path: str,
    arrival_rate: float,
    num_requests: int,
    prefill_len: int,
    decode_len: int,
    tl: int,
    cs: int,
    is_wcp: bool
) -> Dict:
    """Run single benchmark"""

    requests = generate_requests(arrival_rate, num_requests, prefill_len)

    # Create LLM
    if is_wcp:
        max_seqs = min(32, tl)
        max_tokens = cs * max_seqs
    else:
        max_seqs = 48
        max_tokens = 8192

    print(f"  Creating engine (max_seqs={max_seqs}, max_tokens={max_tokens})...")

    llm = LLM(
        model=model_path,
        dtype="float16",
        max_model_len=4096,
        max_num_seqs=max_seqs,
        max_num_batched_tokens=max_tokens,
        gpu_memory_utilization=0.60,  # Lower memory usage
    )

    # Warmup
    _ = llm.generate(generate_prompt(256), SamplingParams(max_tokens=decode_len))
    torch.cuda.synchronize()

    # Benchmark
    latencies = []
    start_time = time.perf_counter()

    for i, (arrival_time, prompt) in enumerate(requests):
        current_elapsed = time.perf_counter() - start_time
        wait_time = arrival_time - current_elapsed
        if wait_time > 0:
            time.sleep(wait_time)

        request_start = time.perf_counter()
        _ = llm.generate(prompt, SamplingParams(max_tokens=decode_len, ignore_eos=True))
        request_end = time.perf_counter()
        latencies.append((request_end - request_start) * 1000)

        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{num_requests} done, mean: {np.mean(latencies[-50:]):.1f}ms")

    del llm
    torch.cuda.empty_cache()

    return {
        "mean_ms": float(np.mean(latencies)),
        "p99_ms": float(np.percentile(latencies, 99)),
        "max_ms": float(np.max(latencies)),
    }


def main():
    model = "models/modelscope/Llama-2-7b-ms"
    rates = [20, 30, 40, 50]
    num_requests = 200
    prefill_len = 512
    decode_len = 20

    # Key configs from Vidur
    wcp_configs = [
        {"tl": 21, "cs": 256, "name": "paper_best"},
        {"tl": 30, "cs": 128, "name": "high_rate"},
        {"tl": 25, "cs": 192, "name": "balanced"},
    ]

    results = {"rates": []}

    for rate in rates:
        print(f"\n{'='*60}")
        print(f"Arrival Rate: {rate} req/s")
        print(f"{'='*60}")

        # Baseline
        print("\nBaseline (vLLM Default)...")
        baseline = benchmark(model, rate, num_requests, prefill_len, decode_len, 0, 0, False)
        print(f"  Mean: {baseline['mean_ms']:.2f}ms, P99: {baseline['p99_ms']:.2f}ms")

        rate_results = {
            "arrival_rate": rate,
            "baseline": baseline,
            "wcp_configs": []
        }

        # Test WCP configs
        for config in wcp_configs:
            print(f"\nWCP {config['name']} (tl={config['tl']}, cs={config['cs']})...")
            wcp_result = benchmark(
                model, rate, num_requests, prefill_len, decode_len,
                config["tl"], config["cs"], True
            )

            improvement = (baseline["mean_ms"] - wcp_result["mean_ms"]) / baseline["mean_ms"] * 100

            print(f"  Mean: {wcp_result['mean_ms']:.2f}ms, P99: {wcp_result['p99_ms']:.2f}ms")
            print(f"  Improvement: {improvement:+.2f}%")

            rate_results["wcp_configs"].append({
                "name": config["name"],
                "tl": config["tl"],
                "cs": config["cs"],
                "result": wcp_result,
                "improvement_pct": improvement
            })

        results["rates"].append(rate_results)

    # Summary
    print("\n" + "="*60)
    print("FINAL SUMMARY")
    print("="*60)

    for r in results["rates"]:
        print(f"\nRate: {r['arrival_rate']} req/s")
        print(f"  Baseline: {r['baseline']['mean_ms']:.1f}ms")

        best = max(r["wcp_configs"], key=lambda x: x["improvement_pct"])
        print(f"  Best WCP: {best['name']} (tl={best['tl']}, cs={best['cs']})")
        print(f"    Mean: {best['result']['mean_ms']:.1f}ms ({best['improvement_pct']:+.1f}%)")

    # Save
    output_path = Path("outputs/wcp_quick_tune")
    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nResults saved to: {output_path}/results.json")


if __name__ == "__main__":
    main()
