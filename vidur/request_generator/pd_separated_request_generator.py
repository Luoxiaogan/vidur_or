"""
PD分离请求生成器

生成"已完成Prefill"的请求，用于模拟Prefill-Decode分离架构：
- 请求到达时 is_prefill_complete = True
- 内存按 prefill_tokens 分配（模拟KV缓存已从Prefill GPU传输过来）
- 执行时间只计算 decode 部分

适用于测试：
- vLLM 调度器
- Sarathi 调度器
- WAIT (GeneralizedNestedBookingLimit) 调度器
"""
from typing import List

import numpy as np

from vidur.config import PDSeparatedRequestGeneratorConfig
from vidur.entities import Request
from vidur.request_generator.base_request_generator import BaseRequestGenerator
from vidur.utils.random import set_seeds


class PDSeparatedRequestGenerator(BaseRequestGenerator):
    """
    PD分离请求生成器

    生成的每个请求都已经"完成了Prefill"阶段，直接进入Decode阶段。
    这用于测试在PD分离架构下，Decode GPU的调度行为。
    """

    def __init__(self, config: PDSeparatedRequestGeneratorConfig):
        super().__init__(config)

    def generate_requests(self) -> List[Request]:
        """
        生成已完成Prefill的请求列表

        Returns:
            List[Request]: 请求列表，每个请求的 is_prefill_complete = True
        """
        set_seeds(self.config.seed)

        requests = []
        current_time = 0.0

        for _ in range(self.config.num_requests):
            # Poisson 到达过程
            inter_arrival = np.random.exponential(1.0 / self.config.arrival_rate)
            current_time += inter_arrival

            # 创建请求，关键：num_processed_tokens 设为 prefill_tokens
            # 注意：不能设置为 prefill_tokens + 1，否则会超过 vLLM 分配的内存块空间
            request = Request(
                arrived_at=current_time,
                num_prefill_tokens=self.config.prefill_tokens,
                num_decode_tokens=self.config.decode_tokens,
                num_processed_tokens=self.config.prefill_tokens,  # 等于 prefill_tokens，不要 +1
            )

            # 设置 prefill 已完成标志
            # 注意：不要手动 += 1，让 on_batch_end 自然处理第一个 decode token
            request._is_prefill_complete = True

            # 对于 WAIT 调度器，设置 current_stage = 1（跳过 stage 0 的等待）
            request.current_stage = 1

            requests.append(request)

        return requests
