"""
Mixing Experiment Test - Two Request Types with Poisson Arrivals

设计目标：
1. 两种类型的请求，各自独立的 Poisson rate
2. 合并排序后按顺序发送（保持到达顺序）
3. 大连接池，最大化并发能力
4. Overloaded 场景：发送速率 > 处理速率，队列始终有积压
5. 记录详细 metrics，输出到 CSV

关键点：
- 使用 asyncio.sleep() 等待目标到达时间
- 即使实际发送有延迟，相对顺序保持正确
- 在 overloaded 场景下，scheduler 始终在处理积压队列
"""
import asyncio
import time
import numpy as np
import aiohttp
import csv
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from transformers import AutoTokenizer
from pathlib import Path

# ============================================================
# 配置区域 - 根据实验需求修改
# ============================================================

# Server 配置
SGLANG_URL = "http://localhost:30000/generate"
MODEL_PATH = "/data/pretrained_models/Qwen2.5-1.5B-Instruct" # /data/pretrained_models/qwen3-8b

# 请求类型配置
# 设计原则：combined rate > server processing rate -> overloaded
REQUEST_TYPES = {
    "short": {
        "prefill_tokens": 5000,   # 较短的 prefill
        "decode_tokens": 1200,     # 中等 decode
        "poisson_rate": 5000,      # 100 req/s
        "count": 10000,            # 2500 个请求
    },
    "long": {
        "prefill_tokens": 5000,   # 较长的 prefill
        "decode_tokens": 1000,     # 较短 decode
        "poisson_rate": 5000,       # 50 req/s
        "count": 10000,            # 2500 个请求
    }
}

# 随机种子（可复现）
SEED = 42

# 输出目录
OUTPUT_DIR = Path("/home/lg/vidur_or/mixing_experiments_for_DJ/sglang_mixing/results_mix")

# ============================================================
# 数据结构
# ============================================================

@dataclass
class RequestInfo:
    """请求调度信息"""
    request_id: int
    req_type: str
    target_arrival: float  # 目标到达时间 (相对于实验开始)
    prefill_tokens: int
    decode_tokens: int


@dataclass
class RequestResult:
    """请求结果"""
    request_id: int
    req_type: str
    prefill_tokens: int
    decode_tokens: int
    # 时间相关
    target_arrival: float      # 目标到达时间
    actual_send_offset: float  # 实际发送时间 (相对于实验开始)
    send_delay: float          # 发送延迟 = actual - target
    send_time_epoch: float     # 发送时间 (epoch)
    recv_time_epoch: float     # 接收时间 (epoch)
    client_latency: float      # 客户端延迟 = recv - send
    # Server 返回的 metrics
    server_prompt_tokens: int
    server_completion_tokens: int
    server_e2e_latency: float


# ============================================================
# 全局变量
# ============================================================

tokenizer = None
prompts: Dict[str, str] = {}


# ============================================================
# 工具函数
# ============================================================

def create_prompt_with_exact_tokens(target_tokens: int) -> str:
    """构造精确 token 数的 prompt"""
    base_text = "hello "
    text = base_text * (target_tokens + 100)
    tokens = tokenizer.encode(text, add_special_tokens=False)[:target_tokens]
    return tokenizer.decode(tokens)


def generate_request_schedule() -> List[RequestInfo]:
    """
    生成请求调度表

    为每种类型生成独立的 Poisson 到达时间，然后合并排序
    """
    np.random.seed(SEED)

    all_requests: List[RequestInfo] = []

    for req_type, config in REQUEST_TYPES.items():
        # 生成该类型的 Poisson 到达时间
        inter_arrivals = np.random.exponential(
            1.0 / config["poisson_rate"],
            config["count"]
        )
        arrival_times = np.cumsum(inter_arrivals)
        # 从 0 开始
        arrival_times = arrival_times - arrival_times[0]

        for i, arrival_time in enumerate(arrival_times):
            all_requests.append(RequestInfo(
                request_id=-1,  # 稍后重新分配
                req_type=req_type,
                target_arrival=arrival_time,
                prefill_tokens=config["prefill_tokens"],
                decode_tokens=config["decode_tokens"],
            ))

    # 按到达时间排序
    all_requests.sort(key=lambda r: r.target_arrival)

    # 重新分配 request_id (按排序后的顺序)
    for i, req in enumerate(all_requests):
        req.request_id = i

    return all_requests


# ============================================================
# HTTP 请求函数
# ============================================================

async def send_request(
    session: aiohttp.ClientSession,
    req_info: RequestInfo,
    start_time: float,
) -> RequestResult:
    """发送单个 HTTP 请求到 /generate endpoint"""

    prompt = prompts[req_info.req_type]

    payload = {
        "text": prompt,
        "sampling_params": {
            "max_new_tokens": req_info.decode_tokens,
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

    return RequestResult(
        request_id=req_info.request_id,
        req_type=req_info.req_type,
        prefill_tokens=req_info.prefill_tokens,
        decode_tokens=req_info.decode_tokens,
        target_arrival=req_info.target_arrival,
        actual_send_offset=send_time - start_time,
        send_delay=(send_time - start_time) - req_info.target_arrival,
        send_time_epoch=send_time,
        recv_time_epoch=recv_time,
        client_latency=recv_time - send_time,
        server_prompt_tokens=meta.get("prompt_tokens", 0),
        server_completion_tokens=meta.get("completion_tokens", 0),
        server_e2e_latency=meta.get("e2e_latency", 0),
    )


async def delayed_send_request(
    session: aiohttp.ClientSession,
    req_info: RequestInfo,
    start_time: float,
) -> RequestResult:
    """
    带延迟的请求发送

    等待到目标到达时间，然后发送请求
    即使落后于计划，也会立即发送（不会跳过）
    """
    target_time = start_time + req_info.target_arrival
    now = time.time()

    if target_time > now:
        await asyncio.sleep(target_time - now)

    return await send_request(session, req_info, start_time)


# ============================================================
# 实验运行
# ============================================================

async def run_experiment(requests: List[RequestInfo]) -> List[RequestResult]:
    """
    运行实验

    一次性创建所有 async task，每个 task 内部等待到目标时间再发送
    """
    num_requests = len(requests)

    # 创建大连接池 - 关键！避免连接数成为瓶颈
    connector = aiohttp.TCPConnector(
        limit=num_requests + 500,  # 足够大
        limit_per_host=num_requests + 500,
    )

    # 设置较长的超时时间（decode 可能很慢）
    timeout = aiohttp.ClientTimeout(total=3600)  # 1 hour

    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        start_time = time.time()

        print(f"\nCreating {num_requests} async tasks...")

        # 一次性创建所有任务
        tasks = [
            asyncio.create_task(
                delayed_send_request(session, req, start_time)
            )
            for req in requests
        ]

        task_creation_time = time.time()
        print(f"Tasks created in {(task_creation_time - start_time)*1000:.1f}ms")
        print(f"Expected send duration: {requests[-1].target_arrival:.2f}s")
        print(f"\nWaiting for all requests to complete...")

        # 并行执行所有任务
        results = await asyncio.gather(*tasks)

        end_time = time.time()
        print(f"\nAll requests completed in {end_time - start_time:.2f}s")

    return results


# ============================================================
# 结果分析
# ============================================================

def analyze_results(results: List[RequestResult]):
    """分析实验结果"""

    print("\n" + "=" * 70)
    print("实验结果分析")
    print("=" * 70)

    # 基本统计
    total = len(results)
    print(f"\n总请求数: {total}")

    # 按类型统计
    by_type: Dict[str, List[RequestResult]] = {}
    for r in results:
        if r.req_type not in by_type:
            by_type[r.req_type] = []
        by_type[r.req_type].append(r)

    print(f"\n按类型分布:")
    for req_type, type_results in by_type.items():
        print(f"  {req_type}: {len(type_results)} requests")

    # 发送时间分析
    print(f"\n--- 发送时间分析 ---")

    send_delays = [r.send_delay for r in results]
    print(f"发送延迟 (actual - target):")
    print(f"  Mean:  {np.mean(send_delays)*1000:8.2f}ms")
    print(f"  Std:   {np.std(send_delays)*1000:8.2f}ms")
    print(f"  P50:   {np.percentile(send_delays, 50)*1000:8.2f}ms")
    print(f"  P90:   {np.percentile(send_delays, 90)*1000:8.2f}ms")
    print(f"  P99:   {np.percentile(send_delays, 99)*1000:8.2f}ms")
    print(f"  Max:   {np.max(send_delays)*1000:8.2f}ms")

    # 检查顺序是否保持
    actual_send_times = [r.actual_send_offset for r in results]
    order_violations = 0
    for i in range(1, len(results)):
        if actual_send_times[i] < actual_send_times[i-1]:
            order_violations += 1
    print(f"\n顺序违反次数: {order_violations} / {total-1}")

    # 客户端延迟分析
    print(f"\n--- 客户端延迟分析 ---")

    for req_type, type_results in by_type.items():
        latencies = [r.client_latency for r in type_results]
        print(f"\n{req_type} (prefill={type_results[0].prefill_tokens}, decode={type_results[0].decode_tokens}):")
        print(f"  Mean:  {np.mean(latencies):8.2f}s")
        print(f"  P50:   {np.percentile(latencies, 50):8.2f}s")
        print(f"  P90:   {np.percentile(latencies, 90):8.2f}s")
        print(f"  P99:   {np.percentile(latencies, 99):8.2f}s")
        print(f"  Max:   {np.max(latencies):8.2f}s")

    # Server E2E 延迟分析
    print(f"\n--- Server E2E 延迟分析 ---")

    for req_type, type_results in by_type.items():
        e2e = [r.server_e2e_latency for r in type_results if r.server_e2e_latency > 0]
        if e2e:
            print(f"\n{req_type}:")
            print(f"  Mean:  {np.mean(e2e)*1000:8.2f}ms")
            print(f"  P50:   {np.percentile(e2e, 50)*1000:8.2f}ms")
            print(f"  P90:   {np.percentile(e2e, 90)*1000:8.2f}ms")
            print(f"  P99:   {np.percentile(e2e, 99)*1000:8.2f}ms")

    # 吞吐量分析
    print(f"\n--- 吞吐量分析 ---")

    first_send = min(r.send_time_epoch for r in results)
    last_recv = max(r.recv_time_epoch for r in results)
    total_duration = last_recv - first_send

    print(f"总时间: {total_duration:.2f}s")
    print(f"吞吐量: {total / total_duration:.2f} req/s")

    # Token 吞吐量
    total_prompt_tokens = sum(r.server_prompt_tokens for r in results)
    total_completion_tokens = sum(r.server_completion_tokens for r in results)
    print(f"Prompt tokens 吞吐: {total_prompt_tokens / total_duration:.0f} tokens/s")
    print(f"Completion tokens 吞吐: {total_completion_tokens / total_duration:.0f} tokens/s")


def save_results_to_csv(results: List[RequestResult], filepath: Path):
    """保存结果到 CSV"""
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'request_id', 'req_type', 'prefill_tokens', 'decode_tokens',
            'target_arrival', 'actual_send_offset', 'send_delay',
            'send_time_epoch', 'recv_time_epoch', 'client_latency',
            'server_prompt_tokens', 'server_completion_tokens', 'server_e2e_latency'
        ])
        writer.writeheader()
        for r in results:
            writer.writerow(asdict(r))

    print(f"\n结果已保存到: {filepath}")


# ============================================================
# 主函数
# ============================================================

async def main():
    global tokenizer, prompts

    print("=" * 70)
    print("Mixing Experiment - Two Types with Poisson Arrivals")
    print("=" * 70)

    # 打印配置
    print(f"\nServer: {SGLANG_URL}")
    print(f"Model: {MODEL_PATH}")
    print(f"Seed: {SEED}")

    total_count = 0
    combined_rate = 0

    for req_type, config in REQUEST_TYPES.items():
        print(f"\n[{req_type}]")
        print(f"  prefill_tokens: {config['prefill_tokens']}")
        print(f"  decode_tokens:  {config['decode_tokens']}")
        print(f"  poisson_rate:   {config['poisson_rate']} req/s")
        print(f"  count:          {config['count']}")
        total_count += config['count']
        combined_rate += config['poisson_rate']

    print(f"\n总请求数: {total_count}")
    print(f"合并到达率: {combined_rate} req/s")

    # 加载 tokenizer
    print("\n" + "-" * 70)
    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)

    # 预生成 prompts
    print("Creating prompts for each type...")
    for req_type, config in REQUEST_TYPES.items():
        prompts[req_type] = create_prompt_with_exact_tokens(config['prefill_tokens'])
        actual_tokens = len(tokenizer.encode(prompts[req_type]))
        print(f"  {req_type}: {actual_tokens} tokens (target: {config['prefill_tokens']})")

    # 生成请求调度表
    print("\n" + "-" * 70)
    print("Generating request schedule (Poisson arrivals)...")
    requests = generate_request_schedule()

    expected_duration = requests[-1].target_arrival
    print(f"Total requests: {len(requests)}")
    print(f"Expected send duration: {expected_duration:.2f}s")
    print(f"Average inter-arrival: {expected_duration / len(requests) * 1000:.2f}ms")

    # 显示前几个请求的调度
    print(f"\n前 10 个请求的调度:")
    print(f"  {'ID':>4}  {'Type':>8}  {'Arrival':>10}  {'Prefill':>7}  {'Decode':>6}")
    for req in requests[:10]:
        print(f"  {req.request_id:>4}  {req.req_type:>8}  {req.target_arrival*1000:>8.2f}ms  {req.prefill_tokens:>7}  {req.decode_tokens:>6}")

    # 运行实验
    print("\n" + "=" * 70)
    print("Starting experiment...")
    print("=" * 70)

    results = await run_experiment(requests)

    # 分析结果
    analyze_results(results)

    # 保存结果
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"mix_results_{timestamp}.csv"
    save_results_to_csv(results, output_file)

    print("\n" + "=" * 70)
    print("Experiment completed!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
