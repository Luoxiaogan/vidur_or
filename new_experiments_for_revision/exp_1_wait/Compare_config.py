"""
WAIT vs vLLM vs Sarathi 公平比较实验配置

核心思路：移除人为限制，让内存成为唯一约束
"""

# ============ 公共配置 ============
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"

# 请求配置
PREFILL_TOKENS = 630
DECODE_TOKENS = 20
MAX_TOKENS = PREFILL_TOKENS + DECODE_TOKENS  # 650

# 内存配置
MEMORY_MARGIN_FRACTION = 0.1

# 实验参数
# ARRIVAL_RATES = [14]  # 测试不同负载
ARRIVAL_RATES = [14, 15,16, 17, 18, 19, 20]  # 测试不同负载
# ARRIVAL_RATES = [16, 17, 18, 19, 20, 21]  # 测试不同负载
# ARRIVAL_RATES = [14, 15,16, 17, 18, 19, 20, 21]  # 测试不同负载
NUM_REQUESTS = 10000

# 输出目录
OUTPUT_DIR = "./PD分离实验4_统一测试_vllm_full_mem"
# OUTPUT_DIR = "./比较测试_3_1_baseline_use_defaults"

# ============ WAIT (General Nested Booking Limit) ============
WAIT_CONFIG = {
    "scheduler_type": "general_nested_booking_limit",
    "total_limit": 725,  
    "force_clear": True,
}

# ============ vLLM ============
VLLM_CONFIG = {
    "scheduler_type": "vllm",
    "max_tokens_in_batch": 1000000,  # 足够大，不成为瓶颈，1000000；4096
    "batch_size_cap": 2000,          # 足够大，不成为瓶颈，2000；128
    "watermark_blocks_fraction": 0.01,
}

# VLLM_CONFIG = {
#     "scheduler_type": "vllm",
#     "max_tokens_in_batch": 4096,  # 足够大，不成为瓶颈，1000000；4096
#     "batch_size_cap": 128,          # 足够大，不成为瓶颈，2000；128
#     "watermark_blocks_fraction": 0.01,
# }

# ============ Sarathi ============
SARATHI_CONFIG = {
    "scheduler_type": "sarathi",
    "chunk_size": 1000000,           # 足够大，不成为瓶颈，默认是512
    "batch_size_cap": 2000,          # 足够大，不成为瓶颈；128
    "watermark_blocks_fraction": 0.01,
}

# SARATHI_CONFIG = {
#     "scheduler_type": "sarathi",
#     "chunk_size": 512,           # 足够大，不成为瓶颈，默认是512
#     "batch_size_cap": 128,          # 足够大，不成为瓶颈；128
#     "watermark_blocks_fraction": 0.01,
# }

# 调度器配置映射
SCHEDULER_CONFIGS = {
    "wait": WAIT_CONFIG,
    "vllm": VLLM_CONFIG,
    "sarathi": SARATHI_CONFIG,
}

# 要比较的调度器列表
SCHEDULERS_TO_COMPARE = ["wait", "vllm"]
# SCHEDULERS_TO_COMPARE = ["sarathi"]

# ============ 分析配置 ============
WARMUP_FRACTION = 0.5

# ============================================================
# ============================================================
# ============ Throughput 分析配置 ============
# ============================================================
# ============================================================
THROUGHPUT_WINDOW = 6      # 滑动窗口大小（秒）
THROUGHPUT_STEP = 1         # 滑动步长（秒）
THROUGHPUT_START_TIME = 20   # 大窗口起始时刻（秒）
THROUGHPUT_END_TIME = 100     # 大窗口结束时刻（秒）

# ============================================================
# ============================================================
# ============ Latency 分析配置 ============
# ============================================================
# ============================================================
LATENCY_WINDOW = THROUGHPUT_WINDOW          # 滑动窗口大小（秒）
LATENCY_STEP = THROUGHPUT_STEP              # 滑动步长（秒）
LATENCY_START_TIME = THROUGHPUT_START_TIME  # 大窗口起始时刻（秒）
LATENCY_END_TIME = THROUGHPUT_END_TIME      # 大窗口结束时刻（秒）
