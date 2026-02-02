"""
测试 sglang fake decode 模式 - 泊松过程发送请求 (使用 OpenAI API)
- 使用 /v1/completions endpoint (正确记录 lb_entry_time)
- 泊松过程发送请求
"""
import asyncio
import time
import numpy as np
import aiohttp
from transformers import AutoTokenizer

# 配置
SGLANG_URL = "http://localhost:30000/v1/completions"
MODEL_PATH = "/data/pretrained_models/Qwen2.5-1.5B-Instruct"

# 请求参数
NUM_REQUESTS = 1000
PREFILL_TOKENS = 310
DECODE_TOKENS = 1000
POISSON_RATE = 5000  # requests per second
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
        "prompt": prompt,
        "max_tokens": max_new_tokens,
        "ignore_eos": True,
        "bootstrap_host": "2.2.2.2",
        "bootstrap_room": 0
    }

    send_time = time.time()
    async with session.post(SGLANG_URL, json=payload) as resp:
        result = await resp.json()
    recv_time = time.time()

    usage = result.get("usage", {})
    return {
        "request_id": request_id,
        "send_time": send_time,
        "recv_time": recv_time,
        "latency": recv_time - send_time,
        "prompt_tokens": usage.get("prompt_tokens", 0),
        "completion_tokens": usage.get("completion_tokens", 0),
        "e2e_latency": recv_time - send_time,  # OpenAI API 无此字段，用客户端延迟代替
    }


async def delayed_send_request(
    session: aiohttp.ClientSession,
    prompt: str,
    max_new_tokens: int,
    request_id: int,
    delay: float,
    start_time: float
):
    """带延迟的异步发送请求 - 等待到指定时间后发送"""
    # 等待到达时间
    target_time = start_time + delay
    now = time.time()
    if target_time > now:
        await asyncio.sleep(target_time - now)

    # 发送请求
    return await send_request_async(session, prompt, max_new_tokens, request_id)


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
    print("\nCreating all tasks...")

    # 创建大连接池，避免连接数限制导致背压
    connector = aiohttp.TCPConnector(limit=NUM_REQUESTS + 100)

    async with aiohttp.ClientSession(connector=connector) as session:
        start_time = time.time()

        # 一次性创建所有带延迟的任务
        tasks = [
            asyncio.create_task(
                delayed_send_request(
                    session, prompt, DECODE_TOKENS, i, arrival_times[i], start_time
                )
            )
            for i in range(NUM_REQUESTS)
        ]

        tasks_created_time = time.time()
        print(f"  All {NUM_REQUESTS} tasks created in {(tasks_created_time - start_time)*1000:.2f}ms")
        print(f"\nWaiting for all requests to complete...")

        # 并行执行所有任务（每个任务内部有自己的延迟）
        results = await asyncio.gather(*tasks)

    end_time = time.time()
    total_time = end_time - start_time

    # 发送时间分析
    send_times = sorted([r["send_time"] for r in results])
    send_duration = send_times[-1] - send_times[0]

    print("\n" + "=" * 60)
    print("发送时间分析")
    print("=" * 60)
    print(f"预期发送时间: {arrival_times[-1]*1000:.2f}ms")
    print(f"实际发送时间: {send_duration*1000:.2f}ms")
    print(f"第 1 个请求: {(send_times[0] - start_time)*1000:.2f}ms")
    print(f"第 {NUM_REQUESTS} 个请求: {(send_times[-1] - start_time)*1000:.2f}ms")

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
