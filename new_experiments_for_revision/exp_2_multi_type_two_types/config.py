#!/usr/bin/env python3
"""
多Type实验配置文件

2个type场景：
- type_A: decode长度较短
- type_B: decode长度较长
"""

# ============ GPU 和模型配置 ============
GPU_TYPE = "a100"
MODEL_NAME = "meta-llama/Meta-Llama-3-8B"

# ============ 请求配置 ============
# 共同的 prefill 长度
PREFILL_TOKENS = 630  # l_0

# type_A: 短decode
TYPE_A_DECODE = 10    # l_A

# type_B: 长decode
TYPE_B_DECODE = 20    # l_B

# 到达率比例 (p:q)
# 例如 p=1, q=1 表示 1:1
ARRIVAL_RATE_RATIO_P = 1  # type_A 比例
ARRIVAL_RATE_RATIO_Q = 1  # type_B 比例

# max_tokens 应该用最长的请求
MAX_TOKENS = PREFILL_TOKENS + TYPE_B_DECODE

# ============ 内存配置 ============
MEMORY_MARGIN_FRACTION = 0.1

# ============ 输出目录 ============
OUTPUT_DIR = "./results_multi_type"

# ============ prompt_types 构造辅助函数 ============
def get_prompt_types(total_arrival_rate: float):
    """
    根据总到达率和比例构造 prompt_types

    Args:
        total_arrival_rate: 总到达率 λ = λ_A + λ_B

    Returns:
        list: prompt_types 配置
    """
    total_ratio = ARRIVAL_RATE_RATIO_P + ARRIVAL_RATE_RATIO_Q
    lambda_A = total_arrival_rate * ARRIVAL_RATE_RATIO_P / total_ratio
    lambda_B = total_arrival_rate * ARRIVAL_RATE_RATIO_Q / total_ratio

    return [
        {
            "type": "type_A",
            "prefill": PREFILL_TOKENS,
            "decode": TYPE_A_DECODE,
            "arrival_rate": lambda_A
        },
        {
            "type": "type_B",
            "prefill": PREFILL_TOKENS,
            "decode": TYPE_B_DECODE,
            "arrival_rate": lambda_B
        }
    ]
