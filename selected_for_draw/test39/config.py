# 应该还是只能选128的情况(对应132limit)

# 实际上, 在固定bs的时候, sarath和vllm是不变的
# 应该是, 在固定bs和总rate的时候是不变的, 因此可以首先测一下sarath和vllm在bs=128的时候，遍历rate，看看比较


# 只用在不同的p_t下面测试nested

prompt_types = [
    {"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": 16},
    {"type": "type2", "prefill": 60, "decode": 200, "arrival_rate": 8},
    {"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": 4},
    {"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": 2},
    {"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 1},
]

# 上面的rate对应乘1,2,3就是基本的数据

# 对于 nested_other

#乘1.5倍?

prompt_types_1 = [
    {"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": 20},
    {"type": "type2", "prefill": 60, "decode": 200, "arrival_rate": 10},
    {"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": 5},
    {"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": 3},
    {"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 2},
]
