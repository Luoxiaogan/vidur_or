"""
测试 sglang fake decode 模式 - 一次性并行发送所有请求
- 1000 个请求同时发送
- 无延迟，真正的并发
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
NUM_REQUESTS = 1000
PREFILL_TOKENS = 5000
DECODE_TOKENS = 2000

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
    print(f"Parallel Burst Request Test")
    print(f"  NUM_REQUESTS: {NUM_REQUESTS}")
    print(f"  PREFILL_TOKENS: {PREFILL_TOKENS}")
    print(f"  DECODE_TOKENS: {DECODE_TOKENS}")
    print("=" * 60)

    # 预先构造 prompt（避免在发送时重复计算）
    print("Creating prompt...")
    prompt = create_prompt_with_exact_tokens(PREFILL_TOKENS)
    print(f"Prompt created with {len(tokenizer.encode(prompt))} tokens")

    # 创建大连接池的 session (避免连接数限制)
    connector = aiohttp.TCPConnector(limit=NUM_REQUESTS + 100)

    # 发送请求
    print(f"\nSending {NUM_REQUESTS} requests in parallel...")
    start_time = time.time()

    async with aiohttp.ClientSession(connector=connector) as session:
        # 一次性创建所有任务
        tasks = [
            asyncio.create_task(
                send_request_async(session, prompt, DECODE_TOKENS, i)
            )
            for i in range(NUM_REQUESTS)
        ]

        tasks_created_time = time.time()
        print(f"  All {NUM_REQUESTS} tasks created in {(tasks_created_time - start_time)*1000:.2f}ms")

        # 等待所有请求完成
        print("\nWaiting for all requests to complete...")
        results = await asyncio.gather(*tasks)

    end_time = time.time()
    total_time = end_time - start_time

    # 分析发送时间分布
    send_times = sorted([r["send_time"] for r in results])
    send_duration = send_times[-1] - send_times[0]

    print("\n" + "=" * 60)
    print("发送时间分析")
    print("=" * 60)
    print(f"第 1 个请求发送时间: {(send_times[0] - start_time)*1000:.2f}ms (相对 start)")
    print(f"第 100 个请求发送时间: {(send_times[99] - start_time)*1000:.2f}ms")
    print(f"第 500 个请求发送时间: {(send_times[499] - start_time)*1000:.2f}ms")
    print(f"第 1000 个请求发送时间: {(send_times[999] - start_time)*1000:.2f}ms")
    print(f"所有请求发送耗时: {send_duration*1000:.2f}ms")

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
