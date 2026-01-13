"""
实验 1 配置: WAIT 算法 - Mean Latency vs Arrival Rate

固定参数和变化参数的定义
"""

# GPU 和模型配置
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"

# 请求配置 (单一类型)
PREFILL_TOKENS = 595
DECODE_TOKENS = 20

# 内存配置
MAX_TOKENS = PREFILL_TOKENS + DECODE_TOKENS  
MEMORY_MARGIN_FRACTION = 0.1  

# 实验参数
THRESHOLDS = [740]  # Booking Limit n 列表
ARRIVAL_RATES = [12,13,14,15,16,17,18,19,20,21,22]     # Arrival Rate 范围 (qps)
NUM_REQUESTS = 6000                  # 每个实验的请求数量

# 目录配置
OUTPUT_DIR = "./第一个实验_total_740"
ANALYSIS_OUTPUT_DIR = OUTPUT_DIR + "/analysis"

# 分析参数
WARMUP_FRACTION = 0.1  # Warm-up 跳过比例
