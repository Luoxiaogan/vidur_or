from utils import copy_latest_csv, run_modified, run_sarathi, run_vllm

import subprocess

destination_folder = "/Users/luogan/Code/vidur_or/selected_for_draw/test9__short_decode_high_rate/DRAW_small"

prompt_types = [
    {"type": "type1", "prefill": 10, "decode": 10, "arrival_rate": 1000},
    {"type": "type2", "prefill": 10, "decode": 20, "arrival_rate": 500},
]

run_modified(
    destination_folder = destination_folder,
    limit_start = 340,
    limit_end = 341,
    limit_interval = 1,
    num_requests = 10000,
    prompt_types = prompt_types
)