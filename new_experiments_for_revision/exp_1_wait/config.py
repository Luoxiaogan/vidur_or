"""
实验 1 配置: WAIT 算法 - Mean Latency vs Arrival Rate

固定参数和变化参数的定义
"""

# GPU 和模型配置
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"

# 请求配置 (单一类型)
PREFILL_TOKENS = 60
DECODE_TOKENS = 200

# 实验参数
TOTAL_LIMIT = 100  # Booking Limit 的 threshold n (待调整)
NUM_REQUESTS = 2000  # 每个实验的请求数量

# Arrival Rate 范围 (qps)
ARRIVAL_RATES = [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]

# 输出目录
OUTPUT_DIR = "./results"
