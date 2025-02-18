from utils import copy_latest_csv, run_modified, run_sarathi, run_vllm, run_nested

import subprocess

destination_folder = "/Users/luogan/Code/vidur_or/results_analysis/test17/modified_nested"

prompt_types = [
    {"type": "type1", "prefill": 5, "decode": 10, "arrival_rate": 100},
    {"type": "type2", "prefill": 5, "decode": 30, "arrival_rate": 100},
]

run_nested(
    destination_folder = destination_folder,
    limit_start = 300,
    limit_end = 400,
    limit_interval = 100,
    num_requests = 5000,
    prompt_types = prompt_types
)