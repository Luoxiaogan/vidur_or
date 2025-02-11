
prompt_types = [
    {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 20000},
    {"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 10000},
]

num_requests=50000

total_limit_1 = 200
per_stage_limit = [
    {"type": "type1", "limit":9},
    {"type": "type1", "limit":4},
]
batch_size = 170


total_limit_1 = 500
per_stage_limit = [
    {"type": "type1", "limit":23},
    {"type": "type1", "limit":11},
]
batch_size = 450