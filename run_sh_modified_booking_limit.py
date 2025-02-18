from utils import copy_latest_csv, run_modified, run_sarathi, run_vllm

import subprocess

destination_folder = "/Users/luogan/Code/vidur_or/results_analysis/test16_one_type_plus_plus/modified_booking_limit"

prompt_types = [
    {"type": "type1", "prefill": 20, "decode": 10, "arrival_rate": 2000},
    {"type": "type2", "prefill": 20, "decode": 300, "arrival_rate": 2000},
]

run_modified(
    destination_folder = destination_folder,
    limit_start = 100,
    limit_end = 2100,
    limit_interval = 100,
    num_requests = 5000,
    prompt_types = prompt_types
)