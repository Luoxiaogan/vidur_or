"""
vLLM 调度器混合请求类型实验配置

实验目的: 测试 vLLM 调度器处理两种类型请求的性能
"""

# GPU 和模型配置
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"

# 请求类型定义 (两种类型)
PROMPT_TYPES = [
    {"type": "A", "prefill": 20, "decode": 10, "arrival_rate": 1},
    {"type": "B", "prefill": 11, "decode": 8, "arrival_rate": 1},
]

# 实验参数
NUM_REQUESTS = 2000
BATCH_SIZE_CAP = 500  # vLLM 批处理大小上限

# vLLM 调度器参数
BLOCK_SIZE = 16
WATERMARK_BLOCKS_FRACTION = 0.01
MAX_TOKENS_IN_BATCH = 4096

# 内存配置
MAX_TOKENS = max(pt["prefill"] + pt["decode"] for pt in PROMPT_TYPES)
MEMORY_MARGIN_FRACTION = 0.1

# 目录配置
OUTPUT_DIR = "./results"
