"""
02_20 exp_two 复现：两类型互质 (coprime) 实验
- Type A: prefill=6000, decode=5000
- Type B: prefill=6211, decode=5000 (与 6000 互质，GCD=1)
- 各 ~7300 请求，Poisson 到达
- Engine 直接调用，绕过 HTTP
- 带 tqdm 进度条
"""
import asyncio
import time
import numpy as np
from transformers import AutoTokenizer
from tqdm.asyncio import tqdm_asyncio

from sglang import Engine
from sglang.srt.managers.io_struct import GenerateReqInput

# ==================== 配置 ====================
MODEL_PATH = "/root/Qwen2.5-1.5B-Instruct"
SEED = 42

# 两种请求类型 (coprime: 6000 vs 6211, GCD=1)
REQUEST_TYPES = {
    "type_a": {
        "prefill_tokens": 6000,
        "decode_tokens": 5000,
        "poisson_rate": 2500,
        "count": 9337,
    },
    "type_b": {
        "prefill_tokens": 6211,  # 与 6000 互质
        "decode_tokens": 5000,
        "poisson_rate": 2500,
        "count": 9344,
    }
}

# 输出路径
OUTPUT_DIR = "/root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg_coprime/output"
BATCH_CSV = f"{OUTPUT_DIR}/exp_two_coprime_batch.csv"
REQUEST_CSV = f"{OUTPUT_DIR}/exp_two_coprime_request.csv"

# ==============================================

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)


def create_prompt(target_tokens: int) -> str:
    base_text = "hello "
    text = base_text * (target_tokens + 100)
    tokens = tokenizer.encode(text, add_special_tokens=False)[:target_tokens]
    return tokenizer.decode(tokens)


async def submit_request(tokenizer_manager, prompt, sampling_params, target_delay, start_time, request_id, pbar):
    target_arrival_time = start_time + target_delay
    now = time.time()
    if target_arrival_time > now:
        await asyncio.sleep(target_arrival_time - now)

    actual_submit_time = time.time()

    req = GenerateReqInput(
        text=prompt,
        sampling_params=sampling_params,
        bootstrap_host="2.2.2.2",
        bootstrap_room=0,
        received_time=actual_submit_time,
    )

    final_response = None
    async for response in tokenizer_manager.generate_request(req, request=None):
        final_response = response

    completion_time = time.time()
    pbar.update(1)

    return {
        "request_id": request_id,
        "latency": completion_time - actual_submit_time,
    }


def generate_all_requests():
    """生成两种类型的请求，按到达时间合并排序"""
    np.random.seed(SEED)

    all_requests = []
    for req_type, config in REQUEST_TYPES.items():
        inter_arrivals = np.random.exponential(1.0 / config["poisson_rate"], config["count"])
        arrival_times = np.cumsum(inter_arrivals)
        arrival_times = arrival_times - arrival_times[0]

        prompt = create_prompt(config["prefill_tokens"])
        print(f"  {req_type}: {config['count']} reqs, prefill={config['prefill_tokens']}, "
              f"decode={config['decode_tokens']}, rate={config['poisson_rate']}")

        for i, arr_time in enumerate(arrival_times):
            all_requests.append({
                "req_type": req_type,
                "prefill": config["prefill_tokens"],
                "decode": config["decode_tokens"],
                "arrival_time": arr_time,
                "prompt": prompt,
                "request_id": len(all_requests),
            })

    # 按到达时间排序
    all_requests.sort(key=lambda x: x["arrival_time"])
    # 重新编号
    for i, req in enumerate(all_requests):
        req["request_id"] = i

    return all_requests


async def run_experiment(engine, requests):
    start_time = time.time()
    num_requests = len(requests)

    print(f"\nCreating {num_requests} async tasks...")
    pbar = tqdm_asyncio(total=num_requests, desc="Processing", unit="req")

    sampling_params = {"max_new_tokens": 5000, "ignore_eos": True}

    tasks = []
    for req in requests:
        task = asyncio.create_task(
            submit_request(
                engine.tokenizer_manager,
                req["prompt"],
                sampling_params,
                req["arrival_time"],
                start_time,
                req["request_id"],
                pbar,
            )
        )
        tasks.append(task)

    print(f"Expected submission duration: {requests[-1]['arrival_time']*1000:.2f}ms")

    results = await tqdm_asyncio.gather(*tasks, desc="Waiting")
    pbar.close()

    end_time = time.time()
    return results, start_time, end_time


def main():
    print("=" * 70)
    print("02_20 exp_two (coprime) 复现")
    print("=" * 70)

    total = sum(c["count"] for c in REQUEST_TYPES.values())
    print(f"Total requests: {total}")
    print(f"Types: {list(REQUEST_TYPES.keys())}")

    # 生成请求
    print("\nGenerating request schedule...")
    requests = generate_all_requests()
    print(f"Total: {len(requests)} requests")
    print(f"First 5 arrival times: {[r['arrival_time']*1000 for r in requests[:5]]}")

    # 初始化 Engine
    print("\n" + "=" * 70)
    print("Initializing SGLang Engine...")
    print("=" * 70)

    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    engine = Engine(
        model_path=MODEL_PATH,
        disaggregation_mode="decode",
        disaggregation_decode_enable_fake_auto=True,
        export_batch_metrics_to_file=BATCH_CSV,
        export_request_metrics_to_csv=REQUEST_CSV,
        mem_fraction_static=0.7,
    )

    print("Engine initialized!")

    # 运行实验
    print("\n" + "=" * 70)
    print("Running experiment...")
    print("=" * 70)

    results, start_time, end_time = engine.loop.run_until_complete(
        run_experiment(engine, requests)
    )

    total_time = end_time - start_time
    latencies = [r["latency"] for r in results]

    print("\n" + "=" * 70)
    print("Results")
    print("=" * 70)
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {len(results)/total_time:.2f} req/s")
    print(f"Latency:")
    print(f"  Mean: {np.mean(latencies)*1000:.2f}ms")
    print(f"  P50:  {np.percentile(latencies, 50)*1000:.2f}ms")
    print(f"  P90:  {np.percentile(latencies, 90)*1000:.2f}ms")
    print(f"  P99:  {np.percentile(latencies, 99)*1000:.2f}ms")
    print(f"  Max:  {np.max(latencies)*1000:.2f}ms")

    print(f"\nOutput:")
    print(f"  Batch metrics: {BATCH_CSV}")
    print(f"  Request metrics: {REQUEST_CSV}")

    engine.shutdown()
    print("\nDone!")


if __name__ == "__main__":
    main()
