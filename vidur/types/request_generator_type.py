from vidur.types.base_int_enum import BaseIntEnum


class RequestGeneratorType(BaseIntEnum):
    SYNTHETIC = 1
    TRACE_REPLAY = 2
    CUSTOM = 3  # 新增自定义生成器类型
    PD_SEPARATED = 4  # PD分离请求生成器
