"""
测试 sglang Engine 模式 - 直接调用，绕过 HTTP
- 无 HTTP 传输延迟
- 精确控制泊松过程到达时间
- 保留所有 Metrics 记录
- 并行提交请求（不是串行阻塞）
- 带 tqdm 进度条

关键：使用 engine.tokenizer_manager.generate_request() 的异步接口
"""
import asyncio
import time
import numpy as np
from transformers import AutoTokenizer
from tqdm.asyncio import tqdm_asyncio

# SGLang imports
from sglang import Engine
from sglang.srt.managers.io_struct import GenerateReqInput

# 配置
MODEL_PATH = "/root/Qwen2.5-1.5B-Instruct"

# 请求参数
NUM_REQUESTS = 6000
PREFILL_TOKENS = 6000
DECODE_TOKENS = 5000
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


async def submit_request_at_time(
    tokenizer_manager,
    prompt: str,
    sampling_params: dict,
    target_delay: float,
    start_time: float,
    request_id: int,
    pbar,  # <-- 新增：进度条对象
):
    """
    在指定时间提交请求到 tokenizer_manager
    """
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

    # <-- 新增：更新进度条
    pbar.update(1)

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
    运行泊松过程实验（带 tqdm 进度条）
    """
    start_time = time.time()
    num_requests = len(arrival_times)

    print(f"Creating {num_requests} async tasks...")

    # <-- 新增：创建 tqdm 进度条
    pbar = tqdm_asyncio(total=num_requests, desc="Processing requests", unit="req")

    tasks = [
        asyncio.create_task(
            submit_request_at_time(
                engine.tokenizer_manager,
                prompt,
                sampling_params,
                arrival_times[i],
                start_time,
                i,
                pbar,  # <-- 传递进度条
            )
        )
        for i in range(num_requests)
    ]

    print(f"All tasks created. Starting parallel execution...")
    print(f"Expected completion of submissions: {arrival_times[-1]*1000:.2f}ms")

    # <-- 修改：使用 tqdm.gather 自动更新进度
    results = await tqdm_asyncio.gather(*tasks, desc="Waiting for completion")

    # <-- 关闭进度条
    pbar.close()

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

    np.random.seed(SEED)
    inter_arrival_times = np.random.exponential(1.0 / POISSON_RATE, NUM_REQUESTS)
    arrival_times = np.cumsum(inter_arrival_times)
    arrival_times = arrival_times - arrival_times[0]

    print(f"\n泊松过程参数:")
    print(f"  预期总发送时间: {arrival_times[-1]*1000:.2f}ms")
    print(f"  平均间隔: {np.mean(inter_arrival_times)*1000:.2f}ms")

    print("\nCreating prompt...")
    prompt = create_prompt_with_exact_tokens(PREFILL_TOKENS)
    actual_tokens = len(tokenizer.encode(prompt))
    print(f"Prompt created with {actual_tokens} tokens")

    sampling_params = {
        "max_new_tokens": DECODE_TOKENS,
        "ignore_eos": True,
    }

    print("\n" + "=" * 70)
    print("Initializing SGLang Engine...")
    print("=" * 70)

    engine = Engine(
        model_path=MODEL_PATH,
        disaggregation_mode="decode",
        disaggregation_decode_enable_fake_auto=True,
        export_batch_metrics_to_file="/root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg_single_longer/output/batch_metrics_9.csv",
        export_request_metrics_to_csv="/root/vidur_or/mixing_experiments_for_DJ/sglang_mixing/0424_exp.lg_single_longer/output/request_metrics_9.csv",
        mem_fraction_static=0.7,
    )

    print("Engine initialized!")

    print("\n" + "=" * 70)
    print("Running Poisson Process Experiment (Async Parallel)")
    print("=" * 70)

    results, start_time, end_time = engine.loop.run_until_complete(
        run_poisson_experiment(engine, prompt, sampling_params, arrival_times)
    )

    total_time = end_time - start_time

    submit_offsets = [r["actual_submit_offset"] for r in results]
    submit_errors = [r["submit_error"] for r in results]

    print("\n" + "=" * 70)
    print("提交时间分析 (无 HTTP 延迟)")
    print("=" * 70)
    print(f"  Mean: {np.mean(submit_errors)*1000:.3f}ms")
    print(f"  Max:  {np.max(submit_errors)*1000:.3f}ms")
    print(f"  P99:  {np.percentile(submit_errors, 99)*1000:.3f}ms")

    latencies = [r["latency"] for r in results]

    print("\n" + "=" * 70)
    print("延迟统计 (无 HTTP 开销)")
    print("=" * 70)
    print(f"Total requests: {len(results)}")
    print(f"Total time: {total_time:.2f}s")
    print(f"Throughput: {len(results)/total_time:.2f} req/s")
    print()
    print(f"Latency:")
    print(f"  Mean: {np.mean(latencies)*1000:.2f}ms")
    print(f"  P50:  {np.percentile(latencies, 50)*1000:.2f}ms")
    print(f"  P90:  {np.percentile(latencies, 90)*1000:.2f}ms")
    print(f"  P99:  {np.percentile(latencies, 99)*1000:.2f}ms")
    print(f"  Max:  {np.max(latencies)*1000:.2f}ms")

    print("\n" + "=" * 70)
    print("Shutting down engine...")
    engine.shutdown()
    print("Done!")
    print("=" * 70)


if __name__ == "__main__":
    main()
