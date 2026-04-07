#!/usr/bin/env python3
"""Test small prompt with large batch (B=600) on A100."""

import time
import torch
from vllm import LLM, SamplingParams

print("="*60)
print("Testing: Small prompt + Large batch on A100")
print("Config: prefill=20, decode=10, batch=600")
print("="*60)

try:
    llm = LLM(
        model="models/modelscope/Llama-2-7b-ms",
        dtype="float16",
        max_model_len=4096,
        max_num_seqs=640,
        gpu_memory_utilization=0.9,
    )

    # Small prompt
    prompt = "Hi, how are you? "
    prompts = [prompt] * 600

    sampling_params = SamplingParams(
        temperature=0.0,
        max_tokens=15,
        ignore_eos=True,
    )

    print("Warmup with batch=10...")
    _ = llm.generate(prompts[:10], sampling_params)

    print("Testing batch=600...")
    torch.cuda.synchronize()
    start = time.perf_counter()
    outputs = llm.generate(prompts, sampling_params)
    torch.cuda.synchronize()
    end = time.perf_counter()

    iteration_time_ms = (end - start) * 1000
    memory_mb = torch.cuda.max_memory_allocated() / 1024 / 1024

    print(f"\n✅ SUCCESS!")
    print(f"   Iteration time: {iteration_time_ms:.2f} ms")
    print(f"   Memory used: {memory_mb:.1f} MB ({memory_mb/1024:.1f} GB)")
    print(f"   Throughput: {600/(iteration_time_ms/1000):.1f} req/s")
    print(f"   Memory per request: {memory_mb/600:.1f} MB")

    # Save results
    import csv
    with open('outputs/large_batch_test.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['batch_size', 'prefill', 'decode', 'iteration_time_ms', 'memory_mb', 'throughput_rps'])
        writer.writerow([600, 20, 10, iteration_time_ms, memory_mb, 600/(iteration_time_ms/1000)])
    print(f"\nResults saved to: outputs/large_batch_test.csv")

    del llm
    torch.cuda.empty_cache()

except torch.cuda.OutOfMemoryError as e:
    print(f"\n❌ Out of Memory (OOM)")
    print(f"   Error: {e}")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
