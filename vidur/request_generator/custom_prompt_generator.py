from vidur.request_generator.base_request_generator import BaseRequestGenerator
from typing import List  # 新增导入
from vidur.entities import Request  # 确保 Request 类已更新，包含 prompt_type 和 current_stage
import random

class CustomPromptGenerator(BaseRequestGenerator):
    def __init__(self, config):
        super().__init__(config)
        # 定义不同类型的 prompt 参数和到达率
        self.prompt_types = [
            {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 3},
            #{"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 2},
            #{"type": "type3", "prefill": 10, "decode": 30, "arrival_rate": 1},
            # 可以继续添加更多类型……
        ]
    def _generate_next_request(self, last_arrived_at: float) -> Request:
        # 选择一个 prompt 类型，例如基于到达率选择
        prompt_type_info = random.choices(
            self.prompt_types,
            weights=[pt["arrival_rate"] for pt in self.prompt_types],
            k=1
        )[0]
        
        prompt_type = prompt_type_info["type"]
        inter_request_time = random.expovariate(sum(pt["arrival_rate"] for pt in self.prompt_types))  # 示例：指数分布
        arrived_at = last_arrived_at + inter_request_time

        # 创建 Request 时传递 prompt_type
        return Request(
            arrived_at=arrived_at,
            num_prefill_tokens=prompt_type_info["prefill"],
            num_decode_tokens=prompt_type_info["decode"],
            prompt_type=prompt_type
        )

    def _generate_requests(self) -> List[Request]:
        requests = []
        current_time = 0

        if self.config.duration is not None:
            while current_time < self.config.duration:
                req = self._generate_next_request(current_time)
                current_time = req.arrived_at
                requests.append(req)
        elif self.config.num_requests is not None:
            for _ in range(self.config.num_requests):
                req = self._generate_next_request(current_time)
                current_time = req.arrived_at
                requests.append(req)
        else:
            # 处理其他情况或抛出异常
            pass

        return requests

    def generate_requests(self) -> List[Request]:
        # 调用内部方法生成请求列表
        requests = self._generate_requests()
        # 对请求排序或根据时间截断
        requests.sort(key=lambda x: x.arrived_at)
        if self.config.duration is not None:
            requests = [r for r in requests if r.arrived_at < self.config.duration]
        return requests