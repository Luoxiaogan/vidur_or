from utils import run_nested_real_data

import subprocess

destination_folder = "/Users/luogan/Code/vidur_or/selected_for_draw/test39/DRAW"

prompt_types = [
    {"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": 16},
    {"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": 8},
    {"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": 4},
    {"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 4},
]

qps = sum(prompt['arrival_rate'] for prompt in prompt_types)
print(f"Total QPS: {qps}")

add = "_qps="+str(qps)+"_rates="

for pt in prompt_types:
    add += f"_{pt['arrival_rate']}"

print(f"Add: {add}")

run_nested_real_data(
    destination_folder = destination_folder,
    limit_start = 129,
    limit_end = 130,
    limit_interval = 1,
    num_requests =8000,
    prompt_types = prompt_types,
    qps = qps,
    trace_file="./data/processed_traces/sample_5e5_input<200_output<500.csv",
    add = add
)