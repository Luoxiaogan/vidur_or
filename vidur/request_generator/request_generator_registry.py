from vidur.request_generator.synthetic_request_generator import (
    SyntheticRequestGenerator,
)
from vidur.request_generator.trace_replay_request_generator import (
    TraceReplayRequestGenerator,
)

from vidur.request_generator.custom_prompt_generator import CustomPromptGenerator

from vidur.types import RequestGeneratorType
from vidur.utils.base_registry import BaseRegistry


class RequestGeneratorRegistry(BaseRegistry):
    pass


RequestGeneratorRegistry.register(
    RequestGeneratorType.SYNTHETIC, SyntheticRequestGenerator
)
RequestGeneratorRegistry.register(
    RequestGeneratorType.TRACE_REPLAY, TraceReplayRequestGenerator
)

RequestGeneratorRegistry.register(
    RequestGeneratorType.CUSTOM,  # 假设您在 RequestGeneratorType 中新增了 CUSTOM 类型
    CustomPromptGenerator
)