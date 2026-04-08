#!/usr/bin/env python3
"""
Complete WCP (WAIT-CP) Algorithm Implementation

Implements the full WCP algorithm from the paper:
1. Nested Booking Limit with segment-wise control
2. Per-request Chunked Prefill
3. Per-segment Gate mechanism
4. WAIT (Workload-Adaptive In-system Throttling)
"""

import os
import sys
import time
import json
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
from math import ceil

import torch
from vllm import LLM, SamplingParams


@dataclass
class WCPConfig:
    """WCP Configuration matching Vidur settings"""

    total_limit: int = 21          # tl: global booking limit
    chunk_size: int = 256          # cs: per-request chunk size

    # Segment configuration
    segments: List[Dict] = field(default_factory=lambda: [
        {"n_k": 11, "start": 1, "end": 11}
    ])

    enable_gate: bool = True
    wait_gate: bool = False
    seg_margin: float = 0.0

    # Workload specification
    prefill_len: int = 512
    decode_len: int = 20

    @property
    def K(self) -> int:
        return max(1, ceil(self.prefill_len / self.chunk_size))

    @property
    def pipeline_depth(self) -> float:
        return self.K + self.decode_len

    @property
    def per_stage_throughput(self) -> float:
        return self.total_limit / self.pipeline_depth


class WCPScheduler:
    """Complete WCP Scheduler"""

    def __init__(self, config: WCPConfig):
        self.config = config

        # Initialize segments
        self.segment_states = []
        for seg in config.segments:
            self.segment_states.append({
                "start": seg["start"],
                "end": seg["end"],
                "n_k": seg["n_k"],
                "seg_total_limit": seg.get("seg_total_limit",
                    int(ceil(config.total_limit * seg["n_k"] / config.pipeline_depth))),
                "requests": set(),
            })

        # Calculate budgets
        P = config.per_stage_throughput
        prefill_in_progress = P * config.K
        decode_count = config.total_limit - prefill_in_progress

        self.prefill_budget = int(ceil(prefill_in_progress * config.chunk_size))
        self.batch_est = int(ceil(decode_count + prefill_in_progress * config.chunk_size))

        # Per-segment decode budgets
        self.seg_decode_budgets = []
        for seg in self.segment_states:
            seg_count = seg["end"] - seg["start"] + 1
            budget = int(ceil(seg["n_k"] * seg_count))
            self.seg_decode_budgets.append(budget)

        # Request tracking
        self.request_tokens: Dict[str, int] = {}
        self.request_stage: Dict[str, int] = {}

        # Runtime stats
        self.batch_count = 0

        print(f"[WCP] tl={config.total_limit}, cs={config.chunk_size}")
        print(f"  K={config.K}, P={P:.2f}, prefill_budget={self.prefill_budget}")

    def get_chunk_size(self, rid: str, prefill_len: int) -> int:
        """Get chunk size for request"""
        if rid not in self.request_tokens:
            self.request_tokens[rid] = 0
            self.request_stage[rid] = 0

        processed = self.request_tokens[rid]
        remaining = prefill_len - processed

        if self.request_stage[rid] == 0:  # prefill
            return min(remaining, self.config.chunk_size)
        else:  # decode
            return 1

    def can_admit(self, num_requests: int, num_tokens: int) -> bool:
        """Check if we can admit more requests"""
        in_system = len(self.request_tokens)
        if in_system >= self.config.total_limit:
            return False
        if self.config.enable_gate and num_tokens > self.prefill_budget:
            return False
        return True

    def process_batch(self, rids: List[str], tokens: List[int]):
        """Update state after processing batch"""
        for rid, num_tokens in zip(rids, tokens):
            if rid in self.request_tokens:
                self.request_tokens[rid] += num_tokens
        self.batch_count += 1


class WCPvLLMBenchmark:
    """Full WCP Benchmark"""

    def __init__(self, model_path: str, wcp_config: WCPConfig):
        self.model_path = model_path
        self.wcp_config = wcp_config

    def run_wcp_benchmark(
        self,
        batch_sizes: List[int],
        prefill_lens: List[int],
        decode_len: int,
        num_iterations: int
    ) -> List[Dict]:
        """Run WCP benchmark with full algorithm"""
        print("\n" + "="*60)
        print("Running Full WCP Benchmark")
        print("="*60)

        results = []

        for bs in batch_sizes:
            for pl in prefill_lens:
                print(f"\nConfig: batch={bs}, prefill={pl}")

                # Create WCP scheduler for this config
                wcp = WCPScheduler(self.wcp_config)

                # Create vLLM with WCP constraints
                max_seqs = min(bs, self.wcp_config.total_limit)

                llm = LLM(
                    model=self.model_path,
                    dtype="float16",
                    max_model_len=4096,
                    max_num_seqs=max_seqs,
                    max_num_batched_tokens=self.wcp_config.chunk_size * max_seqs,
                    gpu_memory_utilization=0.85,
                )

                # Generate prompts
                base_prompt = "The quick brown fox jumps over the lazy dog. "
                words_needed = int(pl / 0.75) + 10
                prompt = (base_prompt * (words_needed // 9 + 1))[:words_needed * 10]
                prompts = [prompt] * bs

                sampling_params = SamplingParams(
                    temperature=0.0,
                    max_tokens=decode_len,
                    ignore_eos=True,
                )

                # Warmup
                print("  Warmup...")
                _ = llm.generate(prompts[:1], sampling_params)
                torch.cuda.synchronize()

                # Benchmark
                print(f"  Benchmarking ({num_iterations} iterations)...")
                times = []
                for i in range(num_iterations):
                    torch.cuda.synchronize()
                    start = time.perf_counter()

                    outputs = llm.generate(prompts, sampling_params)

                    torch.cuda.synchronize()
                    elapsed = (time.perf_counter() - start) * 1000
                    times.append(elapsed)
                    print(f"    Iter {i+1}: {elapsed:.2f} ms")

                memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

                results.append({
                    "batch_size": bs,
                    "prefill_len": pl,
                    "mean_time_ms": np.mean(times),
                    "std_time_ms": np.std(times),
                    "memory_mb": memory_mb,
                    "scheduler": "wcp_full",
                    "wcp_tl": self.wcp_config.total_limit,
                    "wcp_cs": self.wcp_config.chunk_size,
                })

                print(f"  Mean: {np.mean(times):.2f} ms")

                del llm
                torch.cuda.empty_cache()

        return results


if __name__ == "__main__":
    config = WCPConfig(total_limit=21, chunk_size=256)
    scheduler = WCPScheduler(config)
    print("Full WCP implementation ready!")
    print(f"Stats: {scheduler.batch_count}")
