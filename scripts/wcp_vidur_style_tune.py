#!/usr/bin/env python3
"""
WCP Vidur-Style Systematic Tuning

Phase 1: Fix cs=256, tune tl (15, 20, 25, 30, 35, 40, 50)
Phase 2: Fix best tl, tune cs (64, 96, 128, 192, 256, 512)

Target: Win at rates 20, 30, 40, 50, 60
"""

import json
import time
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


def generate_requests_single(arrival_rate: float, num_requests: int):
    """Single type: p512d20"""
    random.seed(42)
    requests = []
    current_time = 0.0
    prefill_len, decode_len = 512, 20

    for _ in range(num_requests):
        inter_arrival = -math.log(1.0 - random.random()) / arrival_rate
        current_time += inter_arrival
        prompt = generate_prompt(prefill_len)
        requests.append((current_time, prompt, decode_len))

    return requests


def run_benchmark(model_path: str, arrival_rate: float, num_requests: int, tl: int, cs: int, is_wcp: bool) -> Dict:
    """Run single benchmark"""

    requests = generate_requests_single(arrival_rate, num_requests)

    if is_wcp:
        max_seqs = min(32, tl)
        max_tokens = cs * max_seqs
    else:
        max_seqs = 64
        max_tokens = 8192

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

    for arrival_time, prompt, decode_len in requests:
        current_elapsed = time.perf_counter() - start_time
        wait_time = arrival_time - current_elapsed
        if wait_time > 0:
            time.sleep(wait_time)

        request_start = time.perf_counter()
        _ = llm.generate(prompt, SamplingParams(max_tokens=decode_len, ignore_eos=True))
        request_end = time.perf_counter()
        latencies.append((request_end - request_start) * 1000)

    total_time = time.perf_counter() - start_time

    result = {
        "mean_ms": float(np.mean(latencies)),
        "p99_ms": float(np.percentile(latencies, 99)),
        "max_ms": float(np.max(latencies)),
        "throughput": num_requests / total_time,
    }

    del llm
    torch.cuda.empty_cache()

    return result


def phase1_tune_tl(model_path: str, rate: int, num_requests: int) -> Dict:
    """Phase 1: Fix cs=256, find best tl"""
    print(f"\n{'='*60}")
    print(f"Rate {rate}: Phase 1 - Tune tl (cs=256)")
    print(f"{'='*60}")

    tl_values = [15, 20, 25, 30, 35, 40, 50]

    # Baseline
    baseline = run_benchmark(model_path, rate, num_requests, 0, 0, False)
    print(f"vLLM Baseline: mean={baseline['mean_ms']:.1f}ms, p99={baseline['p99_ms']:.1f}ms")

    best_tl = None
    best_improvement = -999
    results = []

    for tl in tl_values:
        result = run_benchmark(model_path, rate, num_requests, tl, 256, True)
        improvement = (baseline['mean_ms'] - result['mean_ms']) / baseline['mean_ms'] * 100

        print(f"  tl={tl}: mean={result['mean_ms']:.1f}ms ({improvement:+.1f}%), p99={result['p99_ms']:.1f}ms")

        results.append({"tl": tl, **result, "improvement": improvement})

        if improvement > best_improvement:
            best_improvement = improvement
            best_tl = tl

    print(f"\nBest tl: {best_tl} ({best_improvement:+.1f}%)")

    return {
        "rate": rate,
        "baseline": baseline,
        "best_tl": best_tl,
        "tl_results": results,
    }


def phase2_tune_cs(model_path: str, rate: int, num_requests: int, best_tl: int) -> Dict:
    """Phase 2: Fix best_tl, tune cs"""
    print(f"\n{'='*60}")
    print(f"Rate {rate}: Phase 2 - Tune cs (tl={best_tl})")
    print(f"{'='*60}")

    cs_values = [64, 96, 128, 192, 256, 512]

    baseline = run_benchmark(model_path, rate, num_requests, 0, 0, False)
    print(f"vLLM Baseline: mean={baseline['mean_ms']:.1f}ms, p99={baseline['p99_ms']:.1f}ms")

    best_cs = None
    best_improvement = -999
    results = []

    for cs in cs_values:
        result = run_benchmark(model_path, rate, num_requests, best_tl, cs, True)
        improvement = (baseline['mean_ms'] - result['mean_ms']) / baseline['mean_ms'] * 100

        print(f"  cs={cs}: mean={result['mean_ms']:.1f}ms ({improvement:+.1f}%), p99={result['p99_ms']:.1f}ms")

        results.append({"cs": cs, **result, "improvement": improvement})

        if improvement > best_improvement:
            best_improvement = improvement
            best_cs = cs

    print(f"\nBest cs: {best_cs} ({best_improvement:+.1f}%)")

    return {
        "rate": rate,
        "baseline": baseline,
        "best_tl": best_tl,
        "best_cs": best_cs,
        "cs_results": results,
    }


def main():
    model = "models/modelscope/Llama-2-7b-ms"
    rates = [20, 30, 40, 50, 60]
    num_requests = 300

    all_results = {"rates": []}

    for rate in rates:
        # Phase 1: Tune tl
        phase1 = phase1_tune_tl(model, rate, num_requests)

        if phase1["best_tl"] is None:
            print(f"\nNo good tl found for rate {rate}")
            continue

        # Phase 2: Tune cs with best tl
        phase2 = phase2_tune_cs(model, rate, num_requests, phase1["best_tl"])

        # Calculate final improvement
        baseline = phase2["baseline"]
        best_result = next(r for r in phase2["cs_results"] if r["cs"] == phase2["best_cs"])
        improvement = best_result["improvement"]

        all_results["rates"].append({
            "arrival_rate": rate,
            "best_config": {"tl": phase2["best_tl"], "cs": phase2["best_cs"]},
            "baseline_mean_ms": baseline["mean_ms"],
            "wcp_mean_ms": best_result["mean_ms"],
            "improvement_pct": improvement,
            "won": improvement > 0,
        })

    # Final summary
    print("\n" + "="*70)
    print("FINAL TUNING SUMMARY")
    print("="*70)
    print(f"{'Rate':>8} {'Baseline':>12} {'WCP Best':>12} {'Config':>15} {'Improvement':>12} {'Win?':>6}")
    print("-"*70)

    wins = 0
    for r in all_results["rates"]:
        config = r["best_config"]
        win_mark = "✓" if r["won"] else "✗"
        if r["won"]:
            wins += 1

        print(f"{r['arrival_rate']:>8} "
              f"{r['baseline_mean_ms']:>12.1f} "
              f"{r['wcp_mean_ms']:>12.1f} "
              f"tl={config['tl']},cs={config['cs']:>3} "
              f"{r['improvement_pct']:>11.1f}% "
              f"{win_mark:>6}")

    print("-"*70)
    print(f"Total Wins: {wins}/{len(all_results['rates'])}")

    # Save
    output_path = Path("outputs/wcp_vidur_tune")
    output_path.mkdir(parents=True, exist_ok=True)
    with open(output_path / "results.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\nResults saved to: {output_path}/results.json")

    if wins == len(all_results["rates"]):
        print("\n🏆 ALL LOADS WIN! 🏆")
    elif wins >= len(all_results["rates"]) // 2:
        print(f"\n✓ Won {wins}/{len(all_results['rates'])} loads")
    else:
        print(f"\n✗ Only won {wins}/{len(all_results['rates'])} loads")


if __name__ == "__main__":
    main()
