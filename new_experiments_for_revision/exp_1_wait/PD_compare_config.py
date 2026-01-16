"""
PD 分离场景下 WAIT vs vLLM vs Sarathi 公平比较实验配置

核心特点：
- 使用 pd_separated 请求生成器
- 请求到达时已完成 Prefill，只执行 Decode
- 模拟 Prefill-Decode 分离架构下的 Decode GPU 行为
"""

# ============ 公共配置 ============
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"

# 请求配置（与原实验保持一致便于对比）
PREFILL_TOKENS = 630  # KV 缓存大小
DECODE_TOKENS = 20    # 实际需要执行的 decode token 数
MAX_TOKENS = PREFILL_TOKENS + DECODE_TOKENS  # 650

# 内存配置
MEMORY_MARGIN_FRACTION = 0.1

# 实验参数
ARRIVAL_RATES = [14, 15, 16, 17, 18, 19, 20]
NUM_REQUESTS = 6000

# 输出目录
OUTPUT_DIR = "./PD分离比较测试"

# ============ WAIT (General Nested Booking Limit) ============
WAIT_CONFIG = {
    "scheduler_type": "general_nested_booking_limit",
    "total_limit": 720,  # n* x l1 = 36 x 20
    "force_clear": True,
}

# ============ vLLM ============
VLLM_CONFIG = {
    "scheduler_type": "vllm",
    "max_tokens_in_batch": 1000000,
    "batch_size_cap": 2000,
    "watermark_blocks_fraction": 0.01,
}

# ============ Sarathi ============
SARATHI_CONFIG = {
    "scheduler_type": "sarathi",
    "chunk_size": 1000000,
    "batch_size_cap": 2000,
    "watermark_blocks_fraction": 0.01,
}

# 调度器配置映射
SCHEDULER_CONFIGS = {
    "wait": WAIT_CONFIG,
    "vllm": VLLM_CONFIG,
    "sarathi": SARATHI_CONFIG,
}

# 要比较的调度器列表
SCHEDULERS_TO_COMPARE = ["wait", "vllm", "sarathi"]

# ============ 分析配置 ============
WARMUP_FRACTION = 0.5

# ============ PD 分离特有配置 ============
RANDOM_SEED = 42
