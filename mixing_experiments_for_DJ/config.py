"""
vLLM PD 分离调度器实验配置（多 Type）

实验目的: 测试 VLLMPDSeparatedReplicaScheduler 调度器
- 无 Watermark
- restart 时保持 is_prefill_complete=True（模拟 KV cache 从 CPU 重新加载）
- 多 type 请求混合
"""

# GPU 和模型配置
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"

# PD 分离请求生成器参数（多 type 模式）
PROMPT_TYPES = [
    {"type": "A", "prefill": 5000, "decode": 110, "arrival_rate": 200000},
    {"type": "B", "prefill": 5000, "decode": 111, "arrival_rate": 200000},
]
SEED = 42

# 实验参数
NUM_REQUESTS = 10000
BATCH_SIZE_CAP = 50000  # vLLM 批处理大小上限

# vLLM PD 分离调度器参数
BLOCK_SIZE = 16
WATERMARK_BLOCKS_FRACTION = 0  # 禁用 watermark
MAX_TOKENS_IN_BATCH = 4096

# 内存配置
MAX_TOKENS = max(pt["prefill"] + pt["decode"] for pt in PROMPT_TYPES)
MEMORY_MARGIN_FRACTION = 0.1

# 目录配置
OUTPUT_DIR = "./results"
