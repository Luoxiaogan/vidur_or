"""
测试 sglang Engine 模式 - 直接调用，绕过 HTTP
- 无 HTTP 传输延迟
- 精确控制泊松过程到达时间
- 保留所有 Metrics 记录
- 并行提交请求（不是串行阻塞）

关键：使用 engine.tokenizer_manager.generate_request() 的异步接口
"""
import asyncio
import time
import numpy as np
from transformers import AutoTokenizer

# SGLang imports
from sglang import Engine
from sglang.srt.managers.io_struct import GenerateReqInput

# 配置
MODEL_PATH = "/data/pretrained_models/Qwen2.5-1.5B-Instruct"

# 请求参数
NUM_REQUESTS = 500
PREFILL_TOKENS = 5000
DECODE_TOKENS = 2000
POISSON_RATE = 2000  # requests per second
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


async def submit_request_at_time(
    tokenizer_manager,
    prompt: str,
    sampling_params: dict,
    target_delay: float,
    start_time: float,
    request_id: int,
):
    """
    在指定时间提交请求到 tokenizer_manager

    这是核心函数：
    1. await sleep 到目标到达时间
    2. 创建 GenerateReqInput，设置 received_time
    3. 调用 tokenizer_manager.generate_request()（异步，非阻塞提交）
    4. 等待响应返回
    """
    # 计算目标到达时间
    target_arrival_time = start_time + target_delay

    # 等待到达时间
    now = time.time()
    if target_arrival_time > now:
        await asyncio.sleep(target_arrival_time - now)

    # 记录实际提交时间
    actual_submit_time = time.time()

    # 创建请求，设置 received_time 为实际提交时间
    # 这个时间会被传递到 scheduler，用于计算 metrics
    req = GenerateReqInput(
        text=prompt,
        sampling_params=sampling_params,
        # Fake decode 模式需要的参数
        bootstrap_host="2.2.2.2",
        bootstrap_room=0,
        # 精确控制到达时间 - 这是关键！
        # Scheduler 会使用这个时间计算 wait_time, e2e_time 等
        received_time=actual_submit_time,
    )

    # 调用 tokenizer_manager.generate_request()
    # 这是一个 async generator，需要迭代获取最终结果
    final_response = None
    async for response in tokenizer_manager.generate_request(req, request=None):
        final_response = response

    completion_time = time.time()

    return {
        "request_id": request_id,
        "target_delay": target_delay,
        "actual_submit_offset": actual_submit_time - start_time,
        "submit_error": abs((actual_submit_time - start_time) - target_delay),
        "completion_time": completion_time,
        "latency": completion_time - actual_submit_time,
        "response": final_response,
    }


async def run_poisson_experiment(engine, prompt, sampling_params, arrival_times):
    """
    运行泊松过程实验

    一次性创建所有任务，每个任务内部 await sleep 到目标时间
    然后并行执行所有任务
    """
    start_time = time.time()
    num_requests = len(arrival_times)

    print(f"Creating {num_requests} async tasks...")

    # 一次性创建所有任务
    # 每个任务会 await sleep 到自己的目标到达时间，然后提交请求
    tasks = [
        asyncio.create_task(
            submit_request_at_time(
                engine.tokenizer_manager,
                prompt,
                sampling_params,
                arrival_times[i],
                start_time,
                i,
            )
        )
        for i in range(num_requests)
    ]

    print(f"All tasks created. Starting parallel execution...")
    print(f"Expected completion of submissions: {arrival_times[-1]*1000:.2f}ms")

    # 并行执行所有任务
    results = await asyncio.gather(*tasks)

    end_time = time.time()

    return results, start_time, end_time


def main():
    print("=" * 70)
    print("SGLang Engine Direct Call Test (No HTTP, Async Parallel)")
    print("=" * 70)
    print(f"  NUM_REQUESTS: {NUM_REQUESTS}")
    print(f"  PREFILL_TOKENS: {PREFILL_TOKENS}")
    print(f"  DECODE_TOKENS: {DECODE_TOKENS}")
    print(f"  POISSON_RATE: {POISSON_RATE} req/s")
    print(f"  SEED: {SEED}")
    print("=" * 70)

    # 生成泊松过程的到达时间
    np.random.seed(SEED)
    inter_arrival_times = np.random.exponential(1.0 / POISSON_RATE, NUM_REQUESTS)
    arrival_times = np.cumsum(inter_arrival_times)
    arrival_times = arrival_times - arrival_times[0]  # 从 0 开始

    print(f"\n泊松过程参数:")
    print(f"  预期总发送时间: {arrival_times[-1]*1000:.2f}ms")
    print(f"  平均间隔: {np.mean(inter_arrival_times)*1000:.2f}ms")

    # 预先构造 prompt（只构造一次，复用）
    print("\nCreating prompt...")
    prompt = create_prompt_with_exact_tokens(PREFILL_TOKENS)
    actual_tokens = len(tokenizer.encode(prompt))
    print(f"Prompt created with {actual_tokens} tokens")

    # Sampling 参数
    sampling_params = {
        "max_new_tokens": DECODE_TOKENS,
        "ignore_eos": True,
    }

    # 初始化 Engine
    print("\n" + "=" * 70)
    print("Initializing SGLang Engine...")
    print("(This will load the model and start the scheduler)")
    print("=" * 70)

    engine = Engine(
        model_path=MODEL_PATH,
        # Fake decode 模式参数
        disaggregation_mode="decode",
        disaggregation_decode_enable_fake_auto=True,
        # Metrics 导出参数（使用我们实现的 CSV 导出）
        export_batch_metrics_to_file="/home/lg/vidur_or/mixing_experiments_for_DJ/sglang_mixing/results_batch/batch_metrics_9.csv",
        export_request_metrics_to_csv="/home/lg/vidur_or/mixing_experiments_for_DJ/sglang_mixing/results_req/request_metrics_9.csv",
        # 内存优化
        mem_fraction_static=0.7,
    )

    print("Engine initialized!")

    # 运行实验
    print("\n" + "=" * 70)
    print("Running Poisson Process Experiment (Async Parallel)")
    print("=" * 70)

    # 使用 engine 的事件循环运行异步实验
    # 这样可以正确地与 engine 内部的调度集成
    results, start_time, end_time = engine.loop.run_until_complete(
        run_poisson_experiment(engine, prompt, sampling_params, arrival_times)
    )

    total_time = end_time - start_time

    # 分析提交时间精度
    submit_offsets = [r["actual_submit_offset"] for r in results]
    target_offsets = [r["target_delay"] for r in results]
    submit_errors = [r["submit_error"] for r in results]

    print("\n" + "=" * 70)
    print("提交时间分析 (无 HTTP 延迟)")
    print("=" * 70)
    print(f"预期提交范围: 0 ~ {arrival_times[-1]*1000:.2f}ms")
    print(f"实际提交范围: {min(submit_offsets)*1000:.2f} ~ {max(submit_offsets)*1000:.2f}ms")
    print()
    print(f"提交时间误差:")
    print(f"  Mean: {np.mean(submit_errors)*1000:.3f}ms")
    print(f"  Max:  {np.max(submit_errors)*1000:.3f}ms")
    print(f"  P99:  {np.percentile(submit_errors, 99)*1000:.3f}ms")
    print()

    # 检查是否在预期时间内完成提交
    expected_duration = arrival_times[-1]
    actual_submit_duration = max(submit_offsets) - min(submit_offsets)
    print(f"提交时间对比:")
    print(f"  预期: {expected_duration*1000:.2f}ms")
    print(f"  实际: {actual_submit_duration*1000:.2f}ms")
    print(f"  匹配度: {min(expected_duration, actual_submit_duration) / max(expected_duration, actual_submit_duration) * 100:.1f}%")
    print()

    print("提交时间分布 (采样):")
    for idx in [0, 49, 99, 249, 499]:
        if idx < len(results):
            r = results[idx]
            print(f"  第 {idx+1:4d} 个: 目标 +{r['target_delay']*1000:8.2f}ms, "
                  f"实际 +{r['actual_submit_offset']*1000:8.2f}ms, "
                  f"误差 {r['submit_error']*1000:6.3f}ms")

    # 统计延迟结果
    print("\n" + "=" * 70)
    print("延迟统计 (无 HTTP 开销)")
    print("=" * 70)

    latencies = [r["latency"] for r in results]

    print(f"Total requests: {len(results)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {len(results)/total_time:.2f} req/s")
    print()
    print(f"Latency (从提交到完成):")
    print(f"  Mean: {np.mean(latencies)*1000:.2f}ms")
    print(f"  P50:  {np.percentile(latencies, 50)*1000:.2f}ms")
    print(f"  P90:  {np.percentile(latencies, 90)*1000:.2f}ms")
    print(f"  P99:  {np.percentile(latencies, 99)*1000:.2f}ms")
    print(f"  Max:  {np.max(latencies)*1000:.2f}ms")

    # 关闭 Engine
    print("\n" + "=" * 70)
    print("Shutting down engine...")
    engine.shutdown()
    print("Done!")
    print("=" * 70)

    print(f"\nMetrics 已导出到:")
    print(f"  - Batch: results_batch/batch_metrics_9.csv")
    print(f"  - Request: results_req/request_metrics_9.csv")


if __name__ == "__main__":
    main()
