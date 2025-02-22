from utils import run_nested

import subprocess

destination_folder = "./results_analysis/test31/modified_nested"

prompt_types=[
{"type": "type1", "prefill": 60, "decode": 50, "arrival_rate": 23},
{"type": "type2", "prefill": 60, "decode": 100, "arrival_rate": 11},
{"type": "type3", "prefill": 60, "decode": 150, "arrival_rate": 8},
{"type": "type4", "prefill": 60, "decode": 200, "arrival_rate": 7},
{"type": "type5", "prefill": 60, "decode": 250, "arrival_rate": 6},
{"type": "type6", "prefill": 60, "decode": 300, "arrival_rate": 4},
{"type": "type7", "prefill": 60, "decode": 350, "arrival_rate": 3},
{"type": "type8", "prefill": 60, "decode": 400, "arrival_rate": 2},
{"type": "type9", "prefill": 60, "decode": 450, "arrival_rate": 1},
{"type": "type10", "prefill": 60, "decode": 500, "arrival_rate": 1},
]

run_nested(
    destination_folder = destination_folder,
    limit_start = 120,
    limit_end = 175,
    limit_interval = 5,
    num_requests = 8000,
    prompt_types = prompt_types,
)