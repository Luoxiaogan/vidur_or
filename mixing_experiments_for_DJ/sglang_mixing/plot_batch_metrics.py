"""绘制 batch_metrics CSV 的关键指标"""
import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
csv_path = "results_batch/batch_metrics_5.csv"
df = pd.read_csv(csv_path)

# 创建 2x2 子图
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle('Batch Metrics Analysis', fontsize=14)

# 1. gpu_num_reqs
axes[0, 0].plot(df.index, df['gpu_num_reqs'], 'b-', linewidth=0.8)
axes[0, 0].set_xlabel('Batch Index')
axes[0, 0].set_ylabel('gpu_num_reqs')
axes[0, 0].set_title('GPU Running Requests')
axes[0, 0].grid(True, alpha=0.3)

# 2. num_queue_reqs
axes[0, 1].plot(df.index, df['num_queue_reqs'], 'g-', linewidth=0.8)
axes[0, 1].set_xlabel('Batch Index')
axes[0, 1].set_ylabel('num_queue_reqs')
axes[0, 1].set_title('Waiting Queue Length')
axes[0, 1].grid(True, alpha=0.3)

# 3. num_retracted_reqs
axes[1, 0].plot(df.index, df['num_retracted_reqs'], 'r-', linewidth=0.8)
axes[1, 0].set_xlabel('Batch Index')
axes[1, 0].set_ylabel('num_retracted_reqs')
axes[1, 0].set_title('Retracted Requests')
axes[1, 0].grid(True, alpha=0.3)

# 4. token_usage
axes[1, 1].plot(df.index, df['token_usage'], 'm-', linewidth=0.8)
axes[1, 1].set_xlabel('Batch Index')
axes[1, 1].set_ylabel('token_usage')
axes[1, 1].set_title('KV Cache Token Usage')
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('batch_metrics_5.png', dpi=150)
print(f"Saved to batch_metrics_5.png")
print(f"Total batches: {len(df)}")
print(f"gpu_num_reqs max: {df['gpu_num_reqs'].max()}")
print(f"num_queue_reqs max: {df['num_queue_reqs'].max()}")
print(f"num_retracted_reqs max: {df['num_retracted_reqs'].max()}")
print(f"token_usage max: {df['token_usage'].max():.4f}")
