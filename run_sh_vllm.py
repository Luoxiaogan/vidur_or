from utils import copy_latest_csv, run_modified, run_sarathi, run_vllm

destination_folder = "/Users/luogan/Code/vidur_or/results_analysis/test29/vllm"

prompt_types = [
    {"type": "type1", "prefill": 120, "decode": 25, "arrival_rate": 200},
    {"type": "type2", "prefill": 120, "decode": 55, "arrival_rate": 100},
]

batch_size_list = [130]

run_vllm(
    destination_folder = destination_folder,
    batchsize_start = 500,
    batchsize_end = 600,
    batchsize_interval = 100,
    num_requests = 8000,
    prompt_types = prompt_types,
    batch_size_list = batch_size_list
)