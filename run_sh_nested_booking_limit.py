from utils import run_nested

import subprocess

destination_folder = "/Users/luogan/Code/vidur_or/selected_for_draw/test32/DRAW"

prompt_types = [
{"type": "type1", "prefill": 60, "decode": 50, "arrival_rate": 230},
{"type": "type2", "prefill": 60, "decode": 100, "arrival_rate": 110},
{"type": "type3", "prefill": 60, "decode": 150, "arrival_rate": 80},
{"type": "type4", "prefill": 60, "decode": 200, "arrival_rate": 70},
{"type": "type5", "prefill": 60, "decode": 250, "arrival_rate": 60},
{"type": "type6", "prefill": 60, "decode": 300, "arrival_rate": 40},
{"type": "type7", "prefill": 60, "decode": 350, "arrival_rate": 30},
{"type": "type8", "prefill": 60, "decode": 400, "arrival_rate": 20},
{"type": "type9", "prefill": 60, "decode": 450, "arrival_rate": 10},
{"type": "type10", "prefill": 60, "decode": 500, "arrival_rate": 10},
]

run_nested(
    destination_folder = destination_folder,
    limit_start = 155,
    limit_end = 156,
    limit_interval = 1,
    num_requests = 8000,
    prompt_types = prompt_types,
)