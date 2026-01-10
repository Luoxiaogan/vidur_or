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
THRESHOLDS = [20, 40, 60, 80, 100]  # Booking Limit n 列表
ARRIVAL_RATES = [5, 10, 15, 20]     # Arrival Rate 范围 (qps)
NUM_REQUESTS = 2000                  # 每个实验的请求数量

# 目录配置
OUTPUT_DIR = "./results"
ANALYSIS_OUTPUT_DIR = "./results/analysis"

# 分析参数
WARMUP_FRACTION = 0.1  # Warm-up 跳过比例
