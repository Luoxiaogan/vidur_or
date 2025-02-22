from utils import copy_latest_csv, run_modified, run_sarathi, run_vllm

import subprocess

destination_folder = "./results_analysis/test31/sarathi"

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

batch_size_list = [115,119,126,130,134,139,148,155,159,164]

run_sarathi(
    destination_folder = destination_folder,
    batchsize_start = 400,
    batchsize_end = 500,
    batchsize_interval = 100,
    num_requests = 8000,
    prompt_types = prompt_types,
    batch_size_list = batch_size_list
)