from utils import copy_latest_csv, run_modified, run_sarathi, run_vllm, run_nested

import subprocess



prompt_types = [
    {"type": "type1", "prefill": 10, "decode": 20, "arrival_rate": 20},
    {"type": "type1", "prefill": 10, "decode": 40, "arrival_rate": 40},
    {"type": "type2", "prefill": 10, "decode": 80, "arrival_rate": 80},
    {"type": "type3", "prefill": 10, "decode": 160, "arrival_rate": 160}
    # {"type": "type3", "prefill": 10, "decode": 320, "arrival_rate": 320},
]

batch_size_list = [128]

destination_folder = "./results_analysis/test29/sarathi"
run_sarathi(
    destination_folder = destination_folder,
    batchsize_start = 400,
    batchsize_end = 500,
    batchsize_interval = 100,
    num_requests = 8000,
    prompt_types = prompt_types,
    batch_size_list = batch_size_list
)

destination_folder = "./results_analysis/test29/vllm"
run_vllm(
    destination_folder = destination_folder,
    batchsize_start = 500,
    batchsize_end = 600,
    batchsize_interval = 100,
    num_requests = 8000,
    prompt_types = prompt_types,
    batch_size_list = batch_size_list
)

destination_folder = "./results_analysis/test29/nested_1"
run_nested(
    destination_folder = destination_folder,
    limit_start = batch_size_list[0],
    limit_end = batch_size_list[0]+1,
    limit_interval = 1,
    num_requests = 8000,
    prompt_types = prompt_types,
)