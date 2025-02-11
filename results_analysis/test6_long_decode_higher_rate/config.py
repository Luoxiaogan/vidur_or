a = 10
# a 不会影响计算出来的booking_limit, 但是会影响总的到达速率

prompt_types = [
    {"type": "type1", "prefill": 50, "decode": 156, "arrival_rate": 167*a},
    {"type": "type2", "prefill": 100, "decode": 171, "arrival_rate": 31*a},
    # 可继续添加其他类型...
]

#total_arrival_rate = sum(item["arrival_rate"] for item in prompt_types)
#print(f"Total arrival rate: {total_arrival_rate}")

num_requests=10000

total_limit_1 = 500
per_stage_limit = [
    {"type": "type1", "limit":2},
    {"type": "type1", "limit":1},
]

total_limit_1 = 1000
per_stage_limit = [
    {"type": "type1", "limit":5},
    {"type": "type1", "limit":1},
]

total_limit_1 = 2000
per_stage_limit = [
    {"type": "type1", "limit":10},
    {"type": "type1", "limit":1},
]

total_limit = 2300
per_stage_limit = [
    {"type": "type1", "limit":12},
    {"type": "type1", "limit":2},
]
# 这个时候就会报错： 
#File "/Users/luogan/Desktop/vidur_or/vidur/execution_time_predictor/sklearn_execution_time_predictor.py", line 844, in _get_attention_decode_execution_time
#    return self._predictions["attn_decode"][
#           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#KeyError: (2058, 192)
# 我觉得是因为：整个batch_size太大了, simulation 没有存这个尺寸的batch的计算时间