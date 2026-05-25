"""
Batch-injection version of 04_24.lg.test_3.py.

This script preserves the logical queue order produced by independent Poisson
arrivals, but it does not sleep or submit one asyncio task per request. Instead,
it pre-tokenizes each request type once, builds one batched GenerateReqInput in
that sorted order, and submits it to SGLang in a single call.
"""

import os
import time

import numpy as np
from transformers import AutoTokenizer

from sglang import Engine
from sglang.srt.managers.io_struct import GenerateReqInput


# ==================== Config ====================
MODEL_PATH = "/root/Qwen2.5-1.5B-Instruct"
SEED = 49

REQUEST_TYPES = {
    "type_a": {
        "prefill_tokens": 300,
        "decode_tokens": 4,
        "poisson_rate": 1,
        "count": 30000,
    },
    "type_b": {
        "prefill_tokens": 300,
        "decode_tokens": 12,
        "poisson_rate": 1,
        "count": 30000,
    },
}

# REQUEST_TYPES = {
#     "type_a": {
#         "prefill_tokens": 300,
#         "decode_tokens": 6,
#         "poisson_rate": 1,
#         "count": 30000,
#     },
#     "type_b": {
#         "prefill_tokens": 300,
#         "decode_tokens": 7,
#         "poisson_rate": 1,
#         "count": 30000,
#     },
#     "type_c": {
#         "prefill_tokens": 300,
#         "decode_tokens": 12,
#         "poisson_rate": 1,
#         "count": 30000,
#     },
#     "type_d": {
#         "prefill_tokens": 300,
#         "decode_tokens": 14,
#         "poisson_rate": 1,
#         "count": 30000,
#     },
# }

# REQUEST_TYPES = {
#     "type_a": {
#         "prefill_tokens": 300,
#         "decode_tokens": 9,
#         "poisson_rate": 1,
#         "count": 40000,
#     },
#     "type_b": {
#         "prefill_tokens": 300,
#         "decode_tokens": 15,
#         "poisson_rate": 1,
#         "count": 40000,
#     },
# }

OUTPUT_DIR = "/root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0525_P_300_D_4_12/output"
BATCH_CSV = f"{OUTPUT_DIR}/batch_metrics.csv"
REQUEST_CSV = f"{OUTPUT_DIR}/request_metrics.csv"

# Fake disaggregation decode bootstrap host used by SGLang.
FAKE_BOOTSTRAP_HOST = "2.2.2.2"


print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)


def create_token_ids(target_tokens: int):
    base_text = "hello "
    text = base_text * (target_tokens + 100)
    return tokenizer.encode(text, add_special_tokens=False)[:target_tokens]


def generate_all_requests():
    """Generate independent Poisson streams and merge them by logical arrival."""
    np.random.seed(SEED)

    token_ids_by_type = {}
    all_requests = []

    for req_type, config in REQUEST_TYPES.items():
        token_ids = create_token_ids(config["prefill_tokens"])
        token_ids_by_type[req_type] = token_ids

        inter_arrivals = np.random.exponential(
            1.0 / config["poisson_rate"], config["count"]
        )
        arrival_times = np.cumsum(inter_arrivals)
        arrival_times = arrival_times - arrival_times[0]

        print(
            f"  {req_type}: {config['count']} reqs, "
            f"prefill={len(token_ids)}, decode={config['decode_tokens']}, "
            f"rate={config['poisson_rate']}"
        )

        for arr_time in arrival_times:
            all_requests.append(
                {
                    "req_type": req_type,
                    "decode": config["decode_tokens"],
                    "arrival_time": float(arr_time),
                }
            )

    all_requests.sort(key=lambda x: x["arrival_time"])
    for i, req in enumerate(all_requests):
        req["request_id"] = i

    return all_requests, token_ids_by_type


def build_batched_request(requests, token_ids_by_type, received_time):
    """Build one batched request in the already-sorted logical queue order."""
    input_ids = [token_ids_by_type[req["req_type"]] for req in requests]
    sampling_params = [
        {"max_new_tokens": req["decode"], "ignore_eos": True, "temperature": 0.0}
        for req in requests
    ]
    rids = [
        f"batchq-{req['request_id']:06d}-{req['req_type']}-"
        f"{req['arrival_time']:.9f}"
        for req in requests
    ]

    return GenerateReqInput(
        input_ids=input_ids,
        sampling_params=sampling_params,
        bootstrap_host=[FAKE_BOOTSTRAP_HOST] * len(requests),
        bootstrap_room=list(range(len(requests))),
        rid=rids,
        received_time=received_time,
    )


async def run_experiment(engine, requests, token_ids_by_type):
    print("\nBuilding one batched GenerateReqInput...")
    submit_start = time.time()
    batched_req = build_batched_request(
        requests, token_ids_by_type, received_time=submit_start
    )

    print(f"Submitting {len(requests)} requests as one sorted batch...")
    print(
        "Logical arrival span: "
        f"{requests[-1]['arrival_time'] * 1000:.2f} ms "
        "(preserved only as queue order, not wall-clock sleep)"
    )

    final_response = await engine.tokenizer_manager.generate_request(
        batched_req, request=None
    ).__anext__()
    end_time = time.time()

    num_outputs = len(final_response) if isinstance(final_response, list) else 1
    del final_response
    return submit_start, end_time, num_outputs


def main():
    print("=" * 70)
    print("Batch queue injection experiment")
    print("=" * 70)

    total = sum(c["count"] for c in REQUEST_TYPES.values())
    print(f"Total requests: {total}")
    print(f"Types: {list(REQUEST_TYPES.keys())}")

    print("\nGenerating logical request queue...")
    requests, token_ids_by_type = generate_all_requests()
    print(f"Total: {len(requests)} requests")
    print(f"First 5 logical arrival times (ms): "
          f"{[r['arrival_time'] * 1000 for r in requests[:5]]}")
    print(f"First 20 request types: {[r['req_type'] for r in requests[:20]]}")

    print("\n" + "=" * 70)
    print("Initializing SGLang Engine...")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    engine = Engine(
        model_path=MODEL_PATH,
        disaggregation_mode="decode",
        disaggregation_decode_enable_fake_auto=True,
        export_batch_metrics_to_file=BATCH_CSV,
        export_request_metrics_to_csv=REQUEST_CSV,
        # KV pool 给到正常水位，让真实可用 KV 大
        mem_fraction_static=0.3,
        # req-slot 上限；越大越不被 admission cap，但要配合下面的 cuda graph 限制
        max_running_requests=8192,
        # 不限制等待队列长度
        max_queued_requests=None,
        # 关掉「为每个 in-system req 预留 k 个 decode token」
        num_reserved_decode_tokens=0,
        # 关键：显式上限 cuda graph capture set，避免 max_running_requests=8192
        # 把 capture 拉到 8192 一档而 profile OOM
        cuda_graph_max_bs=512,
    )

    print("Engine initialized!")

    try:
        print("\n" + "=" * 70)
        print("Running experiment...")
        print("=" * 70)

        start_time, end_time, num_outputs = engine.loop.run_until_complete(
            run_experiment(engine, requests, token_ids_by_type)
        )

        total_time = end_time - start_time

        print("\n" + "=" * 70)
        print("Results")
        print("=" * 70)
        print(f"Completed outputs: {num_outputs}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {num_outputs / total_time:.2f} req/s")

        print("\nOutput:")
        print(f"  Batch metrics: {BATCH_CSV}")
        print(f"  Request metrics: {REQUEST_CSV}")
    finally:
        engine.shutdown()
        print("\nDone!")


if __name__ == "__main__":
    main()
