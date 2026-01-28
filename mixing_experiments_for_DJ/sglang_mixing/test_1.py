"""
测试 sglang fake decode 模式 - 泊松过程发送请求
- 2000 个请求
- prefill_tokens=1000, decode_tokens=20
- 泊松过程 rate=1000, seed=42
"""
import asyncio
import time
import numpy as np
import aiohttp
from transformers import AutoTokenizer

# 配置
SGLANG_URL = "http://localhost:30000/generate"
MODEL_PATH = "/data/pretrained_models/Qwen2.5-1.5B-Instruct"

# 请求参数
NUM_REQUESTS = 2000
PREFILL_TOKENS = 1000
DECODE_TOKENS = 410
POISSON_RATE = 1000  # requests per second
SEED = 42

# 加载 tokenizer
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)


def create_prompt_with_exact_tokens(target_tokens: int) -> str:
    """构造精确 token 数的 prompt"""
    base_text = "hello "
    text = base_text * (target_tokens + 100)
    tokens = tokenizer.encode(text, add_special_tokens=False)[:target_tokens]
    return tokenizer.decode(tokens)


async def send_request_async(session: aiohttp.ClientSession, prompt: str, max_new_tokens: int, request_id: int):
    """异步发送请求"""
    payload = {
        "text": prompt,
        "sampling_params": {
            "max_new_tokens": max_new_tokens,
            "ignore_eos": True
        },
        "bootstrap_host": "2.2.2.2",
        "bootstrap_room": 0
    }

    send_time = time.time()
    async with session.post(SGLANG_URL, json=payload) as resp:
        result = await resp.json()
    recv_time = time.time()

    meta = result.get("meta_info", {})
    return {
        "request_id": request_id,
        "send_time": send_time,
        "recv_time": recv_time,
        "latency": recv_time - send_time,
        "prompt_tokens": meta.get("prompt_tokens", 0),
        "completion_tokens": meta.get("completion_tokens", 0),
        "e2e_latency": meta.get("e2e_latency", 0),
    }


async def main():
    print("=" * 60)
    print(f"Poisson Process Request Test")
    print(f"  NUM_REQUESTS: {NUM_REQUESTS}")
    print(f"  PREFILL_TOKENS: {PREFILL_TOKENS}")
    print(f"  DECODE_TOKENS: {DECODE_TOKENS}")
    print(f"  POISSON_RATE: {POISSON_RATE} req/s")
    print(f"  SEED: {SEED}")
    print("=" * 60)

    # 生成泊松过程的到达时间
    np.random.seed(SEED)
    inter_arrival_times = np.random.exponential(1.0 / POISSON_RATE, NUM_REQUESTS)
    arrival_times = np.cumsum(inter_arrival_times)
    arrival_times = arrival_times - arrival_times[0]  # 从 0 开始

    print(f"Total expected duration: {arrival_times[-1]:.2f}s")
    print(f"Average inter-arrival time: {np.mean(inter_arrival_times)*1000:.2f}ms")

    # 预先构造 prompt（避免在发送时重复计算）
    print("Creating prompt...")
    prompt = create_prompt_with_exact_tokens(PREFILL_TOKENS)
    print(f"Prompt created with {len(tokenizer.encode(prompt))} tokens")

    # 发送请求
    print("\nSending requests...")
    start_time = time.time()

    results = []
    tasks = []

    async with aiohttp.ClientSession() as session:
        for i in range(NUM_REQUESTS):
            # 等待到达时间
            target_time = start_time + arrival_times[i]
            now = time.time()
            if target_time > now:
                await asyncio.sleep(target_time - now)

            # 创建异步任务
            task = asyncio.create_task(
                send_request_async(session, prompt, DECODE_TOKENS, i)
            )
            tasks.append(task)

            # 进度显示
            if (i + 1) % 200 == 0:
                elapsed = time.time() - start_time
                print(f"  Sent {i+1}/{NUM_REQUESTS} requests, elapsed: {elapsed:.2f}s")

        # 等待所有请求完成
        print("\nWaiting for all requests to complete...")
        results = await asyncio.gather(*tasks)

    end_time = time.time()
    total_time = end_time - start_time

    # 统计结果
    print("\n" + "=" * 60)
    print("Results Summary")
    print("=" * 60)

    latencies = [r["latency"] for r in results]
    e2e_latencies = [r["e2e_latency"] for r in results]
    prompt_tokens = [r["prompt_tokens"] for r in results]
    completion_tokens = [r["completion_tokens"] for r in results]

    print(f"Total requests: {len(results)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {len(results)/total_time:.2f} req/s")
    print()
    print(f"Latency (client-side):")
    print(f"  Mean: {np.mean(latencies)*1000:.2f}ms")
    print(f"  P50:  {np.percentile(latencies, 50)*1000:.2f}ms")
    print(f"  P90:  {np.percentile(latencies, 90)*1000:.2f}ms")
    print(f"  P99:  {np.percentile(latencies, 99)*1000:.2f}ms")
    print()
    print(f"E2E Latency (server-side):")
    print(f"  Mean: {np.mean(e2e_latencies)*1000:.2f}ms")
    print(f"  P50:  {np.percentile(e2e_latencies, 50)*1000:.2f}ms")
    print(f"  P90:  {np.percentile(e2e_latencies, 90)*1000:.2f}ms")
    print(f"  P99:  {np.percentile(e2e_latencies, 99)*1000:.2f}ms")
    print()
    print(f"Token counts:")
    print(f"  Prompt tokens:  {np.mean(prompt_tokens):.1f} (expected: {PREFILL_TOKENS})")
    print(f"  Completion tokens: {np.mean(completion_tokens):.1f} (expected: {DECODE_TOKENS})")


if __name__ == "__main__":
    asyncio.run(main())
