from utils import run_nested

import subprocess

destination_folder = "./results_analysis/test29/nested_1"

prompt_types = [
    {"type": "type1", "prefill": 120, "decode": 25, "arrival_rate": 300},
    {"type": "type2", "prefill": 120, "decode": 55, "arrival_rate": 50},
]

run_nested(
    destination_folder = destination_folder,
    limit_start = 128,
    limit_end = 129,
    limit_interval = 1,
    num_requests = 8000,
    prompt_types = prompt_types,
)