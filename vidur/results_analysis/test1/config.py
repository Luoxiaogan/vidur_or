
prompt_types = [
    {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 20},
    {"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 10},
]

num_requests=5000

total_limit_1 = 400
per_stage_limit = [
    {"type": "type1", "limit":18},
    {"type": "type1", "limit":9},
]

total_limit_1 = 1000
per_stage_limit = [
    {"type": "type1", "limit":46},
    {"type": "type1", "limit":23},
]

total_limit_1 = 43
per_stage_limit = [
    {"type": "type1", "limit":2},
    {"type": "type1", "limit":1},
]