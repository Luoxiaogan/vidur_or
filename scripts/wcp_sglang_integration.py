#!/usr/bin/env python3
"""
WCP (WAIT-CP) SGLang Integration Module

This module provides the integration layer between WCP algorithm and SGLang runtime.

Architecture:
    WCPScheduler
        ├── SchedulePolicy (custom policy for SGLang)
        ├── WCPBatchBuilder (build batches with WCP constraints)
        └── WCPLimitEnforcer (enforce booking limits)

Usage:
    # In SGLang scheduler.py, replace default policy with:
    from wcp_sglang_integration import WCPScheduler
    self.scheduler = WCPScheduler(scheduler_config)
"""

import os
import sys
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple
from math import ceil
from collections import defaultdict


@dataclass
class WCPSchedulerConfig:
    """Configuration for WCP Scheduler"""

    # Core WCP parameters
    total_limit: int = 21          # tl: global booking limit
    chunk_size: int = 256          # cs: per-request chunk size
    seg_margin: float = 0.0        # segment margin for multi-type

    # Workload specification
    prefill_len: int = 512
    decode_len: int = 20

    # Prompt types for multi-type (single type if len=1)
    prompt_types: List[Dict] = None

    # Gate control
    enable_gate: bool = True       # Per-segment gate
    wait_gate: bool = False        # WAIT fill threshold

    def __post_init__(self):
        if self.prompt_types is None:
            self.prompt_types = [{
                "prefill": self.prefill_len,
                "decode": self.decode_len,
                "arrival_rate": 1.0
            }]

    @property
    def K(self) -> int:
        """Number of prefill chunks"""
        return max(1, ceil(self.prefill_len / self.chunk_size))

    @property
    def pipeline_depth(self) -> float:
        """Weighted pipeline depth"""
        total_rate = sum(pt.get("arrival_rate", 1) for pt in self.prompt_types)
        weighted_k = 0
        weighted_decode = 0

        for pt in self.prompt_types:
            l0 = pt.get("prefill", 512)
            l1 = pt.get("decode", 20)
            rate = pt.get("arrival_rate", 1)
            K = max(1, ceil(l0 / self.chunk_size))
            w = rate / total_rate
            weighted_k += w * K
            weighted_decode += w * l1

        return weighted_k + weighted_decode


class SegmentState:
    """State management for one segment in WCP"""

    def __init__(self, seg_info: Dict, config: WCPSchedulerConfig):
        self.start = seg_info["start"]
        self.end = seg_info["end"]
        self.n_k = seg_info["n_k"]
        self.seg_total_limit = seg_info["seg_total_limit"]

        # Runtime state
        self.requests_in_segment: Set[str] = set()
        self.batch_count = 0

    @property
    def num_stages(self) -> int:
        return self.end - self.start + 1

    def get_stage_limit(self, batch_idx: int) -> int:
        """WAIT: Get per-stage limit with rotation"""
        base = self.seg_total_limit // self.num_stages
        remainder = self.seg_total_limit % self.num_stages
        rotation = batch_idx % self.num_stages
        return base + (1 if rotation < remainder else 0)

    def can_admit(self, batch_idx: int, entry_count: int) -> bool:
        """Check if segment can admit more requests"""
        occupied = len(self.requests_in_segment)
        stage_limit = self.get_stage_limit(batch_idx)

        if self.seg_total_limit == 0:
            return True

        # Check if segment is full
        if occupied >= self.seg_total_limit:
            return False

        # WAIT gate: need enough entry requests
        if entry_count < stage_limit:
            return False

        return True


class WCPScheduler:
    """
    WCP (WAIT-CP) Scheduler for SGLang

    This scheduler implements the paper's strongest algorithm:
    - Nested Booking Limit with segment-wise control
    - Per-request chunked prefill
    - Per-segment gate mechanism

    Integration with SGLang:
        The scheduler hooks into SGLang's scheduling loop:
        1. SGLang calls scheduler.get_next_batch()
        2. WCPScheduler builds batch with WCP constraints
        3. Returns (batch, scheduling_metadata)
    """

    def __init__(self, config: WCPSchedulerConfig):
        self.config = config

        # Initialize segments
        self.segments = []
        self.segment_states = []

        # Build segments from prompt types
        self._build_segments()

        # Calculate budgets
        self._calculate_budgets()

        # Runtime counters
        self.batch_count = 0
        self.total_tokens_scheduled = 0

        # Request tracking
        self.request_stage: Dict[str, int] = {}  # request_id -> current_stage
        self.request_tokens_processed: Dict[str, int] = {}  # request_id -> tokens

        print(f"[WCP] Initialized with {len(self.segments)} segments")
        print(f"[WCP] tl={config.total_limit}, cs={config.chunk_size}")
        print(f"[WCP] Pipeline depth: {config.pipeline_depth:.2f}")

    def _build_segments(self):
        """Build segment structure from prompt types"""
        if len(self.config.prompt_types) == 1:
            # Single type: one segment covering all decode stages
            pt = self.config.prompt_types[0]
            l1 = pt.get("decode", 20)

            seg = {
                "start": 1,
                "end": l1,
                "n_k": self.config.K + 1,
                "seg_total_limit": int(ceil(self.config.total_limit * (self.config.K + 1) / self.config.pipeline_depth))
            }
            self.segments.append(seg)
            self.segment_states.append(SegmentState(seg, self.config))
        else:
            # Multi-type: build segments based on decode lengths
            # This is more complex and uses the paper's segment calculation
            pass  # TODO: implement multi-type segment building

    def _calculate_budgets(self):
        """Calculate per-segment and prefill budgets"""
        # Per-segment decode budgets
        self.seg_decode_budgets = []
        for seg_state in self.segment_states:
            budget = int(ceil(seg_state.n_k * seg_state.num_stages))
            self.seg_decode_budgets.append(budget)

        # Prefill budget
        P = self.config.total_limit / self.config.pipeline_depth
        prefill_in_progress = P * self.config.K
        self.prefill_budget = int(ceil(prefill_in_progress * self.config.chunk_size))

        # Total budget for gate
        decode_count = self.config.total_limit - prefill_in_progress
        self.batch_est = int(ceil(decode_count + prefill_in_progress * self.config.chunk_size))
        self.total_budget = self.batch_est if self.config.enable_gate else float('inf')

    def get_next_batch(
        self,
        waiting_requests: List[Dict],
        running_requests: List[Dict],
        max_batch_size: int,
        max_tokens: int,
        current_memory_usage: int,
        max_memory: int,
    ) -> Tuple[List[str], Dict]:
        """
        Get next batch using WCP scheduling policy

        Args:
            waiting_requests: List of waiting request dicts
            running_requests: List of running (continuing) request dicts
            max_batch_size: Maximum batch size
            max_tokens: Maximum tokens in batch
            current_memory_usage: Current KV cache usage
            max_memory: Maximum available memory

        Returns:
            (selected_request_ids, metadata)
        """
        selected = []
        metadata = {
            "tokens_per_request": {},
            "stages": {},
            "segment_usage": {},
        }

        batch_tokens = 0
        decode_count = 0

        # Phase 1: Handle running requests (continuing decode)
        for req in running_requests:
            if len(selected) >= max_batch_size:
                break
            if batch_tokens >= min(self.total_budget, max_tokens):
                break

            req_id = req["id"]
            stage = self.request_stage.get(req_id, 1)

            selected.append(req_id)
            metadata["tokens_per_request"][req_id] = 1
            metadata["stages"][req_id] = stage
            batch_tokens += 1
            decode_count += 1

            # Update segment state
            for seg_state in self.segment_states:
                if seg_state.start <= stage <= seg_state.end:
                    seg_state.requests_in_segment.add(req_id)

        # Phase 2: Process waiting requests by stage
        stage0_reqs = [r for r in waiting_requests if r.get("stage", 0) == 0]
        stage1_reqs = [r for r in waiting_requests if r.get("stage", 0) >= 1]

        # Phase 2a: Decode requests (stage 1+)
        for seg_idx, seg_state in enumerate(self.segment_states):
            seg_budget = self.seg_decode_budgets[seg_idx] if self.config.enable_gate else float('inf')
            seg_tokens = 0

            # Get requests in this segment's range
            seg_reqs = [
                r for r in stage1_reqs
                if seg_state.start <= r.get("stage", 1) <= seg_state.end
            ]

            for req in seg_reqs:
                if len(selected) >= max_batch_size:
                    break
                if batch_tokens >= min(self.total_budget, max_tokens):
                    break
                if seg_tokens >= seg_budget:
                    break

                # Check booking limit
                in_system = len(running_requests) + len(selected)
                if in_system >= self.config.total_limit:
                    break

                req_id = req["id"]
                stage = req.get("stage", 1)

                # Check if segment can admit
                entry_count = len([r for r in seg_reqs if r["id"] not in selected])
                if not seg_state.can_admit(self.batch_count, entry_count):
                    continue

                selected.append(req_id)
                metadata["tokens_per_request"][req_id] = 1
                metadata["stages"][req_id] = stage
                batch_tokens += 1
                decode_count += 1
                seg_tokens += 1
                seg_state.requests_in_segment.add(req_id)

                # Update request stage
                self.request_stage[req_id] = stage + 1

        # Phase 2b: Prefill requests (stage 0) - Chunked
        prefill_tokens_added = 0

        for req in stage0_reqs:
            if len(selected) >= max_batch_size:
                break
            if batch_tokens >= min(self.total_budget, max_tokens):
                break
            if self.config.enable_gate and prefill_tokens_added >= self.prefill_budget:
                break

            # Check booking limit
            in_system = len(running_requests) + len(selected)
            if in_system >= self.config.total_limit:
                break

            req_id = req["id"]

            # Calculate chunk
            prefill_len = req.get("prefill_len", self.config.prefill_len)
            processed = self.request_tokens_processed.get(req_id, 0)
            remaining = prefill_len - processed

            chunk = min(remaining, self.config.chunk_size)

            # Apply budget constraints
            if self.config.enable_gate:
                budget_left = min(
                    self.prefill_budget - prefill_tokens_added,
                    self.total_budget - batch_tokens,
                    max_tokens - batch_tokens
                )
                chunk = min(chunk, max(0, int(budget_left)))

            if chunk <= 0:
                break

            selected.append(req_id)
            metadata["tokens_per_request"][req_id] = chunk
            metadata["stages"][req_id] = 0
            batch_tokens += chunk
            prefill_tokens_added += chunk

            # Update tracking
            self.request_tokens_processed[req_id] = processed + chunk

            # Check if prefill complete
            if processed + chunk >= prefill_len:
                self.request_stage[req_id] = 1  # Move to decode stage

        # Update stats
        self.batch_count += 1
        self.total_tokens_scheduled += batch_tokens

        # Record segment usage
        for seg_idx, seg_state in enumerate(self.segment_states):
            metadata["segment_usage"][seg_idx] = len(seg_state.requests_in_segment)

        return selected, metadata

    def on_batch_complete(self, request_ids: List[str]):
        """Called when a batch completes"""
        # Clean up completed requests from segment states
        for seg_state in self.segment_states:
            seg_state.requests_in_segment -= set(request_ids)

    def get_stats(self) -> Dict:
        """Get scheduler statistics"""
        return {
            "batch_count": self.batch_count,
            "total_tokens": self.total_tokens_scheduled,
            "avg_tokens_per_batch": self.total_tokens_scheduled / max(1, self.batch_count),
            "config": {
                "tl": self.config.total_limit,
                "cs": self.config.chunk_size,
                "pipeline_depth": self.config.pipeline_depth,
            }
        }


# ==============================================================================
# SGLang Integration Helper
# ==============================================================================

class SGLangWCPAdapter:
    """
    Adapter to integrate WCP scheduler into SGLang

    This adapter translates between SGLang's request format and WCP's format.
    """

    def __init__(self, wcp_scheduler: WCPScheduler):
        self.wcp = wcp_scheduler

    def translate_sglang_request(self, sglang_req) -> Dict:
        """Translate SGLang request to WCP format"""
        return {
            "id": sglang_req.rid,
            "stage": getattr(sglang_req, 'stage', 0),
            "prefill_len": len(sglang_req.origin_input_ids),
            "decode_len": sglang_req.max_new_tokens,
        }

    def schedule(self, scheduler, waiting_queue, running_queue) -> Tuple[List, Dict]:
        """
        Main entry point for SGLang integration

        This method would be called by SGLang's scheduler to get the next batch.
        """
        # Translate requests
        waiting_wcp = [self.translate_sglang_request(r) for r in waiting_queue]
        running_wcp = [self.translate_sglang_request(r) for r in running_queue]

        # Get batch from WCP
        max_batch = scheduler.max_running_requests
        max_tokens = scheduler.max_num_token

        selected_ids, metadata = self.wcp.get_next_batch(
            waiting_requests=waiting_wcp,
            running_requests=running_wcp,
            max_batch_size=max_batch,
            max_tokens=max_tokens,
            current_memory_usage=scheduler.token_to_kv_pool_allocator.get_n空闲(),
            max_memory=scheduler.max_total_num_tokens,
        )

        # Map back to SGLang requests
        id_to_req = {r.rid: r for r in waiting_queue + running_queue}
        selected_requests = [id_to_req[rid] for rid in selected_ids if rid in id_to_req]

        return selected_requests, metadata


# ==============================================================================
# Example Usage
# ==============================================================================

def example_usage():
    """Example of using WCP scheduler"""

    # Create config
    config = WCPSchedulerConfig(
        total_limit=21,
        chunk_size=256,
        prefill_len=512,
        decode_len=20,
        enable_gate=True,
    )

    # Create scheduler
    scheduler = WCPScheduler(config)

    # Example requests
    waiting_requests = [
        {"id": "req_1", "stage": 0, "prefill_len": 512},
        {"id": "req_2", "stage": 0, "prefill_len": 512},
        {"id": "req_3", "stage": 1},
        {"id": "req_4", "stage": 1},
    ]

    running_requests = [
        {"id": "req_0", "stage": 2},
    ]

    # Get next batch
    selected, metadata = scheduler.get_next_batch(
        waiting_requests=waiting_requests,
        running_requests=running_requests,
        max_batch_size=32,
        max_tokens=8192,
        current_memory_usage=1000,
        max_memory=10000,
    )

    print("Selected requests:", selected)
    print("Metadata:", metadata)
    print("Stats:", scheduler.get_stats())


if __name__ == "__main__":
    example_usage()
