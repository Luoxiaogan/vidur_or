from vidur.types.base_int_enum import BaseIntEnum


class ReplicaSchedulerType(BaseIntEnum):
    FASTER_TRANSFORMER = 1
    ORCA = 2
    SARATHI = 3
    VLLM = 4
    LIGHTLLM = 5
    BOOKING_LIMIT = 6
    NESTED_BOOKING_LIMIT = 7
    GENERAL_NESTED_BOOKING_LIMIT = 8 
