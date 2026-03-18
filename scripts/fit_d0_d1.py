"""
拟合 WAIT 理论模型的 d₀, d₁ 参数

模型: ΔT(batch) = d₀ + d₁ × total_tokens
其中 total_tokens = prefill_chunk + n_decode × 1

方法: 用 vidur 的 execution time predictor 生成不同 batch 组成的预测时间，
      然后线性回归拟合 d₀, d₁
"""
import sys, os
import numpy as np
from math import ceil

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from vidur.config.config import (
    ReplicaConfig, SimulationConfig, ClusterConfig, MetricsConfig,
    RandomForrestExecutionTimePredictorConfig,
)
from vidur.entities.replica import Replica
from vidur.entities.batch import Batch
from vidur.entities.request import Request
from vidur.execution_time_predictor import ExecutionTimePredictorRegistry
from vidur.types import ExecutionTimePredictorType

# 配置
DEVICE = "a100"
MODEL = "meta-llama/Meta-Llama-3-8B"
PREFILL_TOKENS = 630
DECODE_TOKENS = 20
MAX_TOKENS = 650
CHUNK_SIZE = 512


def create_predictor():
    """创建 execution time predictor"""
    replica_config = ReplicaConfig(
        model_name=MODEL,
        device=DEVICE,
        memory_margin_fraction=0.1,
        tensor_parallel_size=1,
        num_pipeline_stages=1,
    )

    predictor_config = RandomForrestExecutionTimePredictorConfig(
        prediction_max_prefill_chunk_size=16384,
        prediction_max_batch_size=2048,
        prediction_max_tokens_per_request=65536,
    )

    from vidur.config.config import CustomRequestGeneratorConfig
    gen_config = CustomRequestGeneratorConfig(max_tokens=MAX_TOKENS)

    replica = Replica(replica_config, gen_config)

    # 需要 metrics_config 和 scheduler_config
    from vidur.config.config import SarathiSchedulerConfig
    scheduler_config = SarathiSchedulerConfig(chunk_size=CHUNK_SIZE)

    metrics_config = MetricsConfig()

    predictor = ExecutionTimePredictorRegistry.get(
        ExecutionTimePredictorType.RANDOM_FORREST,
        predictor_config=predictor_config,
        replica_config=replica_config,
        replica_scheduler_config=scheduler_config,
        metrics_config=metrics_config,
    )
    return predictor


def make_decode_request(req_id, prefill_tokens=PREFILL_TOKENS, decode_step=1):
    """创建一个已完成 prefill、在 decode 阶段的 request"""
    req = Request(
        arrived_at=0.0,
        num_prefill_tokens=prefill_tokens,
        num_decode_tokens=DECODE_TOKENS,
    )
    req._id = req_id
    # 模拟已完成 prefill + decode_step 步
    req._num_processed_tokens = prefill_tokens + decode_step
    req._is_prefill_complete = True
    return req


def make_prefill_request(req_id, prefill_tokens=PREFILL_TOKENS, processed=0):
    """创建一个在 prefill 阶段的 request"""
    req = Request(
        arrived_at=0.0,
        num_prefill_tokens=prefill_tokens,
        num_decode_tokens=DECODE_TOKENS,
    )
    req._id = req_id
    req._num_processed_tokens = processed
    req._is_prefill_complete = False
    return req


def measure_batch_time(predictor, n_decode, prefill_chunk=0):
    """
    测量一个 batch 的预测执行时间
    batch = n_decode 个 decode 请求 + 可选的 prefill chunk
    """
    requests = []
    num_tokens = []
    rid = 0

    # decode 请求
    for i in range(n_decode):
        req = make_decode_request(rid, decode_step=i % DECODE_TOKENS + 1)
        requests.append(req)
        num_tokens.append(1)
        rid += 1

    # prefill 请求 (if any)
    if prefill_chunk > 0:
        req = make_prefill_request(rid, processed=0)
        requests.append(req)
        num_tokens.append(prefill_chunk)
        rid += 1

    if not requests:
        return 0.0, 0

    batch = Batch(replica_id=0, requests=requests, num_tokens=num_tokens)
    exec_time = predictor.get_execution_time(batch, pipeline_stage=0)
    total_tokens = sum(num_tokens)

    return exec_time.total_time, total_tokens


def main():
    print("Creating execution time predictor...")
    predictor = create_predictor()
    print("Done.\n")

    # 采样点：不同的 batch 组成
    data_points = []

    # 1. 纯 decode batch（不同 n_decode）
    print("=== Pure Decode Batches ===")
    for n in [1, 2, 5, 10, 15, 20, 30, 50, 80, 100, 150, 200]:
        t, tok = measure_batch_time(predictor, n_decode=n, prefill_chunk=0)
        data_points.append((tok, t))
        print(f"  n_decode={n:>3}, tokens={tok:>4}, time={t*1000:.3f}ms")

    # 2. Decode + prefill chunk（模拟 WAIT CP steady state）
    print("\n=== Decode + Prefill Chunk (chunk=512) ===")
    for n in [0, 1, 5, 10, 15, 19, 30, 50, 80, 100]:
        t, tok = measure_batch_time(predictor, n_decode=n, prefill_chunk=CHUNK_SIZE)
        data_points.append((tok, t))
        print(f"  n_decode={n:>3} + prefill={CHUNK_SIZE}, tokens={tok:>4}, time={t*1000:.3f}ms")

    # 3. Decode + smaller prefill chunk
    print("\n=== Decode + Prefill Chunk (chunk=256) ===")
    for n in [0, 5, 10, 19, 50, 100]:
        t, tok = measure_batch_time(predictor, n_decode=n, prefill_chunk=256)
        data_points.append((tok, t))
        print(f"  n_decode={n:>3} + prefill=256, tokens={tok:>4}, time={t*1000:.3f}ms")

    # 线性回归拟合 ΔT = d₀ + d₁ × total_tokens
    tokens_arr = np.array([p[0] for p in data_points], dtype=float)
    times_arr = np.array([p[1] for p in data_points], dtype=float)

    # 最小二乘: [1, tokens] @ [d0, d1] = times
    A = np.column_stack([np.ones_like(tokens_arr), tokens_arr])
    result = np.linalg.lstsq(A, times_arr, rcond=None)
    d0, d1 = result[0]

    # R²
    predicted = d0 + d1 * tokens_arr
    ss_res = np.sum((times_arr - predicted) ** 2)
    ss_tot = np.sum((times_arr - np.mean(times_arr)) ** 2)
    r_squared = 1 - ss_res / ss_tot

    print("\n" + "=" * 60)
    print("LINEAR FIT: ΔT = d₀ + d₁ × total_tokens")
    print("=" * 60)
    print(f"  d₀ = {d0:.6f} s  ({d0*1000:.4f} ms)")
    print(f"  d₁ = {d1:.8f} s/token  ({d1*1000:.6f} ms/token)")
    print(f"  R² = {r_squared:.6f}")

    # 计算不同 rate 下的 n*
    l1 = DECODE_TOKENS
    l_bar = PREFILL_TOKENS + (l1 + 1) / 2

    print(f"\n  l₀={PREFILL_TOKENS}, l₁={l1}, l̄={l_bar:.1f}")
    print(f"  稳定条件: d₁×l₁×l̄×λ < 1 → λ < {1/(d1*l1*l_bar):.1f}")

    print(f"\n{'Rate':>6} | {'n*(λ)':>8} | {'ceil(n*)':>8} | {'等待时间 n/(2λ)':>15} | {'处理时间 ΔT':>12}")
    print("-" * 65)
    for rate in [10, 12, 14, 15, 16, 17, 18, 19, 20, 21]:
        denom = 1 - d1 * l1 * l_bar * rate
        if denom <= 0:
            print(f"{rate:>6} | {'过载':>8} | {'n_max':>8} |")
            continue
        n_star = d0 * rate / denom
        n_ceil = max(1, ceil(n_star))
        wait_time = n_ceil / (2 * rate)
        delta_t = d0 + d1 * n_ceil * l1 * l_bar
        print(f"{rate:>6} | {n_star:>8.2f} | {n_ceil:>8} | {wait_time:>13.4f}s | {delta_t:>10.4f}s")


if __name__ == "__main__":
    main()
