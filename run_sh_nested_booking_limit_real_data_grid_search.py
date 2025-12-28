from utils import run_nested_real_data
import subprocess

destination_folder = "./results_analysis/test39/grid_search_new"

# 定义所有的 arrival_rate 范围
arrival_rate_values = [2**k for k in range(8)]  # 2^0, 2^1, ..., 2^7

# 定义每个 prompt 的基本配置
prompt_types_template = [
    {"type": "type1", "prefill": 60, "decode": 100, "arrival_rate": None},
    {"type": "type2", "prefill": 60, "decode": 200, "arrival_rate": None},
    {"type": "type3", "prefill": 60, "decode": 300, "arrival_rate": None},
    {"type": "type4", "prefill": 60, "decode": 400, "arrival_rate": None},
    {"type": "type5", "prefill": 60, "decode": 500, "arrival_rate": None},
]

# 生成所有可能的 arrival_rate 组合
for i1 in range(len(arrival_rate_values)):
    for i2 in range(i1 + 1, len(arrival_rate_values)):
        for i3 in range(i2 + 1, len(arrival_rate_values)):
            for i4 in range(i3 + 1, len(arrival_rate_values)):
                for i5 in range(i4 + 1, len(arrival_rate_values)):
                    # 创建一个新的 prompt_types

                    # 通过嵌套循环来遍历每个 arrival_rate，确保满足递减的条件，即 arrival_rate 递减。

                    prompt_types = [dict(pt) for pt in prompt_types_template]  # 深拷贝

                    # 设置每个 type 的 arrival_rate
                    prompt_types[0]["arrival_rate"] = arrival_rate_values[i5]
                    prompt_types[1]["arrival_rate"] = arrival_rate_values[i4]
                    prompt_types[2]["arrival_rate"] = arrival_rate_values[i3]
                    prompt_types[3]["arrival_rate"] = arrival_rate_values[i2]
                    prompt_types[4]["arrival_rate"] = arrival_rate_values[i1]

                    print(prompt_types)

                    # 计算总 QPS
                    qps = sum(pt["arrival_rate"] for pt in prompt_types)
                    print(f"Total QPS: {qps}")

                    # 构造 add 字符串
                    add = "_qps=" + str(qps) + "_rates="
                    for pt in prompt_types:
                        add += f"_{pt['arrival_rate']}"
                    print(f"Add: {add}")

                    # 执行 run_nested_real_data
                    try:
                        run_nested_real_data(
                            destination_folder=destination_folder,
                            limit_start=132,
                            limit_end=133,
                            limit_interval=1,
                            num_requests=8000,
                            prompt_types=prompt_types,
                            qps=qps,
                            trace_file="./data/processed_traces/sample_2e5_input<200_output<500.csv",
                            add=add
                        )
                    except Exception as e:
                        print(f"Error occurred with parameters {add}: {str(e)}")
                        continue
                    
