import torch
import time
import matplotlib.pyplot as plt
from transformers import AutoModelForCausalLM, AutoTokenizer
import csv

# 加载模型和分词器
model_path = "/root/GanLuo/llama7b/"  # 请替换为实际模型路径
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForCausalLM.from_pretrained(model_path, torch_dtype=torch.float16).to("cuda")

# 创建虚拟输入
def create_dummy_inputs(batch_size, sequence_length):
    input_ids = torch.full(
        (batch_size, sequence_length),
        tokenizer.eos_token_id,
        dtype=torch.long
    ).to("cuda")
    attention_mask = torch.ones(
        (batch_size, sequence_length),
        dtype=torch.long
    ).to("cuda")
    return input_ids, attention_mask

# 预热模型
def warmup_model(model, batch_size, sequence_length, num_warmups=5):
    """
    预热模型，运行几次前向传递以稳定 GPU 缓存和模型状态
    Args:
        model: 模型
        batch_size: 批大小
        sequence_length: 序列长度
        num_warmups: 预热次数
    """
    input_ids, attention_mask = create_dummy_inputs(batch_size, sequence_length)
    with torch.no_grad():
        for _ in range(num_warmups):
            model(input_ids, attention_mask=attention_mask)

# 测量推理时间
def measure_inference_time(batch_size, sequence_length, num_runs=10):
    input_ids, attention_mask = create_dummy_inputs(batch_size, sequence_length)
    times = []
    for _ in range(num_runs):
        with torch.no_grad():
            start_time = time.time()
            model(input_ids, attention_mask=attention_mask)
            end_time = time.time()
            times.append(end_time - start_time)
    return sum(times) / num_runs

# 实验参数
batch_sizes = range(1,65,1)
sequence_lengths = range(1, 21, 1)  # 注意：这里只会生成 [1]，可以根据需要调整范围
num_runs = 10
num_warmups = 5  # 预热次数

# 运行实验
results = {}
for batch_size in batch_sizes:
    print(f"Batch Size: {batch_size}")
    for sequence_length in sequence_lengths:
        print(f"Sequence Length: {sequence_length}")
        # 预热模型
        warmup_model(model, batch_size, sequence_length, num_warmups)
        # 测量推理时间
        avg_time = measure_inference_time(batch_size, sequence_length, num_runs)
        results[(batch_size, sequence_length)] = avg_time

# 绘制结果
for batch_size in batch_sizes:
    times = [results[(batch_size, seq_len)] for seq_len in sequence_lengths]
    plt.plot(sequence_lengths, times, label=f'Batch Size {batch_size}')

plt.xlabel('Sequence Length (Token Count)')
plt.ylabel('Average Inference Time (s)')
plt.title('Llama 7B Single-Step Inference Time')
plt.legend()
plt.grid(True)
plt.show()
plt.savefig("/root/GanLuo/Main_test_and_output/inference_time.png")

# 保存数据到 CSV 文件
csv_file_path = "/root/GanLuo/Main_test_and_output/inference_time_data.csv"
with open(csv_file_path, mode='w', newline='') as csv_file:
    writer = csv.writer(csv_file)
    # 写入表头
    writer.writerow(['Batch Size', 'Sequence Length', 'Average Inference Time (s)'])
    # 写入数据
    for (batch_size, sequence_length), avg_time in results.items():
        writer.writerow([batch_size, sequence_length, avg_time])

print(f"Data saved to {csv_file_path}")