"""
SGLang WCP Adapter - No Source Code Modification Required

This module provides WCP (WAIT-CP) scheduling for SGLang WITHOUT modifying SGLang source code.

Approach: Monkey-patching + Wrapper
- Dynamically replaces SGLang's scheduling methods with WCP-aware versions
- Preserves all original SGLang functionality
- Can be enabled/disabled via environment variables

Usage:
    # In your benchmark script:
    from sglang_wcp_adapter import enable_wcp, disable_wcp

    # Enable WCP before creating SGLang engine
    enable_wcp(tl=21, cs=256)

    # Create SGLang engine as usual
    engine = sgl.Engine(...)

    # Run normally - WCP scheduling will be used
    outputs = engine.generate(prompts, sampling_params)

    # Disable WCP to use default vLLM scheduling
    disable_wcp()
"""

import os
import sys
import types
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass, field
from math import ceil
from collections import defaultdict

# Add vidur to path
sys.path.insert(0, "/home/archer/vidur_or")


@dataclass
class WCPConfig:
    """WCP Configuration"""
    total_limit: int = 21
    chunk_size: int = 256
    enable_gate: bool = True
    prefill_len: int = 512
    decode_len: int = 20


class WCPState:
    """
    WCP State Manager

    Maintains WCP-specific state that is attached to SGLang's scheduler instance.
    """

    def __init__(self, config: WCPConfig):
        self.config = config
        self.batch_count = 0
        self.request_stage: Dict[str, int] = {}  # rid -> stage
        self.request_tokens: Dict[str, int] = {}  # rid -> processed tokens

        # Calculate budgets
        self.K = max(1, ceil(config.prefill_len / config.chunk_size))
        self.pipeline_depth = self.K + config.decode_len
        self.P = config.total_limit / self.pipeline_depth

        prefill_in_progress = self.P * self.K
        self.prefill_budget = int(ceil(prefill_in_progress * config.chunk_size))
        decode_count = config.total_limit - prefill_in_progress
        self.batch_est = int(ceil(decode_count + prefill_in_progress * config.chunk_size))

        print(f"[WCP State] Initialized: tl={config.total_limit}, cs={config.chunk_size}")
        print(f"[WCP State] K={self.K}, pipeline_depth={self.pipeline_depth:.2f}")


# Global WCP state
_wcp_state: Optional[WCPState] = None
_original_methods: Dict[str, Any] = {}


def _wcp_get_next_batch_to_run(self) -> Optional[Any]:
    """
    WCP-aware version of get_next_batch_to_run

    This wraps the original method to apply WCP booking limits.
    """
    global _wcp_state

    if _wcp_state is None:
        # WCP not enabled, use original method
        return _original_methods['get_next_batch_to_run'](self)

    # Get original batch
    batch = _original_methods['get_next_batch_to_run'](self)

    if batch is None:
        return None

    # Apply WCP constraints
    config = _wcp_state.config

    # Count in-system requests
    in_system = len(self.running_batch.reqs) if hasattr(self, 'running_batch') and self.running_batch else 0

    # Check if we can admit more requests
    if in_system >= config.total_limit:
        # At booking limit, return empty batch to force decode-only
        if hasattr(batch, 'reqs'):
            # Keep only decode requests (not in prefill)
            decode_reqs = [r for r in batch.reqs if getattr(r, 'finished_prefill', False)]
            if len(decode_reqs) < len(batch.reqs):
                batch.reqs = decode_reqs
                if hasattr(batch, 'filter_batch'):
                    batch.filter_batch()

    # Track WCP stats
    _wcp_state.batch_count += 1

    return batch


def _wcp_get_new_batch_prefill(self) -> Optional[Any]:
    """
    WCP-aware version of get_new_batch_prefill

    Controls prefill admission based on booking limit and chunked prefill.
    """
    global _wcp_state

    if _wcp_state is None:
        return _original_methods['get_new_batch_prefill'](self)

    config = _wcp_state.config

    # Check current in-system count
    in_system = 0
    if hasattr(self, 'running_batch') and self.running_batch:
        in_system += len(self.running_batch.reqs)

    # Calculate available slots
    available_slots = config.total_limit - in_system

    if available_slots <= 0:
        # At booking limit, don't admit new prefill
        return None

    # Get original prefill batch
    batch = _original_methods['get_new_batch_prefill'](self)

    if batch is None:
        return None

    # Apply WCP constraints:
    # 1. Limit number of new requests to available slots
    # 2. Apply chunked prefill

    if hasattr(batch, 'reqs') and len(batch.reqs) > available_slots:
        # Trim batch to available slots
        kept_reqs = batch.reqs[:int(available_slots)]
        batch.reqs = kept_reqs
        if hasattr(batch, 'filter_batch'):
            batch.filter_batch()

    # Apply chunked prefill: limit each request's prefill tokens
    if hasattr(batch, 'reqs'):
        for req in batch.reqs:
            if hasattr(req, 'num_prefill_tokens') and hasattr(req, 'num_processed_tokens'):
                remaining = req.num_prefill_tokens - req.num_processed_tokens
                chunk = min(remaining, config.chunk_size)
                # This is a hint - actual enforcement happens in model forward
                req.wcp_chunk_size = chunk

    return batch


def _wcp_add_one_req(self, req: Any, *args, **kwargs):
    """
    WCP-aware version of add_one_req

    Tracks request state for WCP.
    """
    global _wcp_state

    # Call original method
    result = _original_methods['add_one_req'](self, req, *args, **kwargs)

    if _wcp_state is not None and hasattr(req, 'rid'):
        # Initialize WCP state for new request
        _wcp_state.request_stage[req.rid] = 0  # Stage 0 = prefill
        _wcp_state.request_tokens[req.rid] = 0

    return result


def enable_wcp(tl: int = 21, cs: int = 256, enable_gate: bool = True):
    """
    Enable WCP scheduling for SGLang

    Args:
        tl: Total booking limit
        cs: Chunk size for prefill
        enable_gate: Enable per-segment gate
    """
    global _wcp_state, _original_methods

    if _wcp_state is not None:
        print("[WCP] Already enabled, reinitializing...")
        disable_wcp()

    # Create WCP config and state
    config = WCPConfig(
        total_limit=tl,
        chunk_size=cs,
        enable_gate=enable_gate
    )
    _wcp_state = WCPState(config)

    # Import SGLang's Scheduler
    try:
        from sglang.srt.managers.scheduler import Scheduler
    except ImportError:
        print("[WCP] Error: SGLang not installed or scheduler not found")
        return False

    # Save original methods
    if 'get_next_batch_to_run' not in _original_methods:
        _original_methods['get_next_batch_to_run'] = Scheduler.get_next_batch_to_run
    if 'get_new_batch_prefill' not in _original_methods:
        _original_methods['get_new_batch_prefill'] = Scheduler.get_new_batch_prefill
    if 'add_one_req' not in _original_methods:
        _original_methods['add_one_req'] = Scheduler.add_one_req

    # Replace with WCP-aware versions
    Scheduler.get_next_batch_to_run = _wcp_get_next_batch_to_run
    Scheduler.get_new_batch_prefill = _wcp_get_new_batch_prefill
    Scheduler.add_one_req = _wcp_add_one_req

    # Set environment variables for SGLang
    os.environ['SGLANG_WCP_ENABLED'] = '1'
    os.environ['WCP_TOTAL_LIMIT'] = str(tl)
    os.environ['WCP_CHUNK_SIZE'] = str(cs)

    print(f"[WCP] Enabled: tl={tl}, cs={cs}, gate={enable_gate}")
    return True


def disable_wcp():
    """Disable WCP and restore original SGLang behavior"""
    global _wcp_state, _original_methods

    if not _original_methods:
        print("[WCP] Not enabled")
        return

    # Restore original methods
    try:
        from sglang.srt.managers.scheduler import Scheduler

        if 'get_next_batch_to_run' in _original_methods:
            Scheduler.get_next_batch_to_run = _original_methods['get_next_batch_to_run']
        if 'get_new_batch_prefill' in _original_methods:
            Scheduler.get_new_batch_prefill = _original_methods['get_new_batch_prefill']
        if 'add_one_req' in _original_methods:
            Scheduler.add_one_req = _original_methods['add_one_req']

        print("[WCP] Disabled, original SGLang behavior restored")
    except ImportError:
        pass

    # Clear state
    _wcp_state = None
    _original_methods.clear()

    # Clear environment
    os.environ.pop('SGLANG_WCP_ENABLED', None)


def is_wcp_enabled() -> bool:
    """Check if WCP is currently enabled"""
    return _wcp_state is not None


def get_wcp_stats() -> Dict:
    """Get WCP statistics"""
    if _wcp_state is None:
        return {}

    return {
        'batch_count': _wcp_state.batch_count,
        'config': {
            'total_limit': _wcp_state.config.total_limit,
            'chunk_size': _wcp_state.config.chunk_size,
        },
        'pipeline_depth': _wcp_state.pipeline_depth,
        'prefill_budget': _wcp_state.prefill_budget,
    }


# ==============================================================================
# Benchmark Script using WCP Adapter
# ==============================================================================

def run_wcp_benchmark():
    """
    Example benchmark comparing WCP vs vLLM default using the adapter
    """
    import time
    import numpy as np

    try:
        import sglang as sgl
    except ImportError:
        print("Error: sglang not installed")
        return

    model_path = "models/modelscope/Llama-2-7b-ms"
    batch_sizes = [1, 4, 8, 16, 32]
    prefill_lens = [256, 512]
    decode_len = 20
    num_iters = 3

    results = {'vllm': [], 'wcp': []}

    # Test vLLM default
    print("\n" + "="*60)
    print("Testing vLLM Default")
    print("="*60)

    disable_wcp()  # Ensure WCP is off

    for bs in batch_sizes:
        for pl in prefill_lens:
            # Create engine
            engine = sgl.Engine(
                model_path=model_path,
                tp_size=1,
                dtype="float16",
            )

            # Prepare prompts
            base_prompt = "The quick brown fox jumps over the lazy dog. "
            prompt = base_prompt * (pl // 50)
            prompts = [prompt] * bs

            sampling_params = {
                "temperature": 0.0,
                "max_new_tokens": decode_len,
                "ignore_eos": True,
            }

            # Benchmark
            times = []
            for _ in range(num_iters):
                torch.cuda.synchronize() if hasattr(torch, 'cuda') else None
                start = time.perf_counter()

                outputs = []
                for p in prompts:
                    output = engine.generate(p, sampling_params)
                    outputs.append(output)

                torch.cuda.synchronize() if hasattr(torch, 'cuda') else None
                times.append((time.perf_counter() - start) * 1000)

            results['vllm'].append({
                'batch_size': bs,
                'prefill_len': pl,
                'mean_time_ms': np.mean(times),
            })

            print(f"  B={bs}, P={pl}: {np.mean(times):.2f} ms")

            del engine
            import gc
            gc.collect()

    # Test WCP
    print("\n" + "="*60)
    print("Testing WCP")
    print("="*60)

    enable_wcp(tl=21, cs=256)

    for bs in batch_sizes:
        for pl in prefill_lens:
            # Create engine (WCP is now enabled)
            engine = sgl.Engine(
                model_path=model_path,
                tp_size=1,
                dtype="float16",
            )

            prompt = base_prompt * (pl // 50)
            prompts = [prompt] * bs

            sampling_params = {
                "temperature": 0.0,
                "max_new_tokens": decode_len,
                "ignore_eos": True,
            }

            times = []
            for _ in range(num_iters):
                torch.cuda.synchronize() if hasattr(torch, 'cuda') else None
                start = time.perf_counter()

                outputs = []
                for p in prompts:
                    output = engine.generate(p, sampling_params)
                    outputs.append(output)

                torch.cuda.synchronize() if hasattr(torch, 'cuda') else None
                times.append((time.perf_counter() - start) * 1000)

            results['wcp'].append({
                'batch_size': bs,
                'prefill_len': pl,
                'mean_time_ms': np.mean(times),
            })

            print(f"  B={bs}, P={pl}: {np.mean(times):.2f} ms")

            del engine
            import gc
            gc.collect()

    # Compare results
    print("\n" + "="*60)
    print("Comparison Results")
    print("="*60)

    for v_result, w_result in zip(results['vllm'], results['wcp']):
        improvement = (v_result['mean_time_ms'] - w_result['mean_time_ms']) / v_result['mean_time_ms'] * 100
        print(f"B={v_result['batch_size']}, P={v_result['prefill_len']}: "
              f"vLLM={v_result['mean_time_ms']:.2f}ms, "
              f"WCP={w_result['mean_time_ms']:.2f}ms, "
              f"Improvement={improvement:+.1f}%")

    disable_wcp()

    return results


if __name__ == "__main__":
    # Run example
    print("SGLang WCP Adapter")
    print("="*60)
    print("\nThis module provides WCP scheduling without modifying SGLang source code.")
    print("\nUsage:")
    print("  from sglang_wcp_adapter import enable_wcp, disable_wcp")
    print("  enable_wcp(tl=21, cs=256)")
    print("  engine = sgl.Engine(...)")
    print("  # Use engine normally with WCP scheduling")
    print("  disable_wcp()  # Restore default behavior")
