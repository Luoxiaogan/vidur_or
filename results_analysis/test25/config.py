prompt_types = [
    {"type": "type1", "prefill": 1, "decode": 20, "arrival_rate": 500},
    {"type": "type2", "prefill": 1, "decode": 40, "arrival_rate": 250},
    {"type": "type3", "prefill": 1, "decode": 50, "arrival_rate": 100},
    {"type": "type4", "prefill": 1, "decode": 60, "arrival_rate": 50},
    {"type": "type5", "prefill": 1, "decode": 70, "arrival_rate": 20},
]

batch_size_list = [80, 180, 280, 399, 479, 579, 680, 800, 879, 979]

num_requests = 8000