from utils import copy_latest_csv, run_modified, run_sarathi, run_vllm, run_nested

import subprocess

destination_folder = "/Users/luogan/Code/vidur_or/results_analysis/test23/nested"

prompt_types = [
    {"type": "type1", "prefill": 0, "decode": 20, "arrival_rate": 500},
    {"type": "type2", "prefill": 0, "decode": 40, "arrival_rate": 250},
]

run_nested(
    destination_folder = destination_folder,
    limit_start = 100,
    limit_end = 1100,
    limit_interval = 100,
    num_requests = 8000,
    prompt_types = prompt_types
)