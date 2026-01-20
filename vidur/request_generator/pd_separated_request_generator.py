"""
PD分离请求生成器

生成"已完成Prefill"的请求，用于模拟Prefill-Decode分离架构：
- 请求到达时 is_prefill_complete = True
- 内存按 prefill_tokens 分配（模拟KV缓存已从Prefill GPU传输过来）
- 执行时间只计算 decode 部分

支持两种模式：
1. 单 type 模式：使用 prefill_tokens, decode_tokens, arrival_rate 参数
2. 多 type 模式：使用 prompt_types 参数，每个 type 有独立的 prefill, decode, arrival_rate

适用于测试：
- vLLM 调度器
- Sarathi 调度器
- WAIT (GeneralizedNestedBookingLimit) 调度器
"""
import random
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

    支持单 type 和多 type 两种模式（向后兼容）。
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

        if self.config.prompt_types:
            return self._generate_multi_type_requests()
        else:
            return self._generate_single_type_requests()

    def _generate_single_type_requests(self) -> List[Request]:
        """单 type 模式：原有逻辑"""
        requests = []
        current_time = 0.0

        for _ in range(self.config.num_requests):
            # Poisson 到达过程
            inter_arrival = np.random.exponential(1.0 / self.config.arrival_rate)
            current_time += inter_arrival

            request = self._create_pd_request(
                arrived_at=current_time,
                prefill_tokens=self.config.prefill_tokens,
                decode_tokens=self.config.decode_tokens,
                prompt_type="default",
            )
            requests.append(request)

        return requests

    def _generate_multi_type_requests(self) -> List[Request]:
        """多 type 模式：按 arrival_rate 权重随机选择 type"""
        requests = []
        current_time = 0.0

        # 总到达率
        total_arrival_rate = sum(pt["arrival_rate"] for pt in self.config.prompt_types)

        for _ in range(self.config.num_requests):
            # Poisson 到达过程（总到达率）
            inter_arrival = np.random.exponential(1.0 / total_arrival_rate)
            current_time += inter_arrival

            # 按 arrival_rate 权重随机选择 type
            prompt_type_info = random.choices(
                self.config.prompt_types,
                weights=[pt["arrival_rate"] for pt in self.config.prompt_types],
                k=1
            )[0]

            request = self._create_pd_request(
                arrived_at=current_time,
                prefill_tokens=prompt_type_info["prefill"],
                decode_tokens=prompt_type_info["decode"],
                prompt_type=prompt_type_info["type"],
            )
            requests.append(request)

        return requests

    def _create_pd_request(
        self,
        arrived_at: float,
        prefill_tokens: int,
        decode_tokens: int,
        prompt_type: str,
    ) -> Request:
        """创建一个已完成 Prefill 的请求"""
        request = Request(
            arrived_at=arrived_at,
            num_prefill_tokens=prefill_tokens,
            num_decode_tokens=decode_tokens,
            num_processed_tokens=prefill_tokens,  # 等于 prefill_tokens，不要 +1
            prompt_type=prompt_type,
        )

        # 设置 prefill 已完成标志
        request._is_prefill_complete = True

        # 注意：不要设置 current_stage = 1
        # WAIT 调度器需要请求从 stage 0 开始，以便正确地进行 booking limit 控制

        return request
