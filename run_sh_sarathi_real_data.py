from utils import run_sarathi_real_data

destination_folder = "/Users/luogan/Code/vidur_or/selected_for_draw/test36/DRAW"

prompt_types = [{"type": "type1", "prefill": 60, "decode": 300, "arrival_rate":64},
{"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": 8}
]

# # 实际上这里的prompt_types已经没用了，因为我们是用真实数据
# qps = sum(prompt['arrival_rate'] for prompt in prompt_types)
# print(f"Total QPS: {qps}")

batch_size_list = [64]

qps_list = [32]

# qps = 40
# print(f"Total QPS: {qps}")

for qps in qps_list:
    print(f"Total QPS: {qps}")

    run_sarathi_real_data(
        destination_folder = destination_folder,
        batchsize_start = 500,
        batchsize_end = 600,
        batchsize_interval = 100,
        num_requests = 8000,
        prompt_types = prompt_types,
        batch_size_list = batch_size_list,
        qps = qps,
        trace_file="/Users/luogan/Code/vidur_or/data/processed_traces/sample_5e5_input<200_output<500.csv"
    )