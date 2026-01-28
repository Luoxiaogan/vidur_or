import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
import numpy as np

add = "test9_simulated_short_decode"

file_paths_throughput = [
    "./DRAW/throughput_modified_booking_limit_limit_340_batch_size_289.csv",
    "./DRAW/throughput_sarathi_batch_size_290.csv",
    "./DRAW/throughput_vllm_batch_size_290.csv"
]
labels_e2e = ['WAIT', 'Sarathi', 'vLLM']
s = 14

e2e_file_paths = [
    "./DRAW/request_e2e_time_normalized_modified.csv",
    "./DRAW/request_e2e_time_normalized_sarathi.csv",
    "./DRAW/request_e2e_time_normalized_vllm.csv"
]
a = 6000

# 设置 CMU Serif 字体
font_path = "/Users/luogan/Library/Fonts/CMU Serif Roman.ttf"
font_prop = fm.FontProperties(fname=font_path)

# 设置全局样式，但避免 Seaborn 覆盖刻度
plt.rcParams.update({
    'font.size': 15,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.titlesize': 16,
    'figure.figsize': (8, 7)
})

# 绘制第一个图：Throughput / T vs Time
plt.figure(figsize=(7, 6))
markers = ['o', 's', 'D']  # 圆圈、正方形、菱形
colors = ['blue', 'orange', 'green']

# 设置x轴刻度
xticks = np.arange(0, s + 2, 2)

for file_path, label, marker, color in zip(file_paths_throughput, labels_e2e, markers, colors):
    df = pd.read_csv(file_path)
    df['throughput_per_T'] = df['throughput'] / df['Time (sec)']
    df_filtered = df[df['Time (sec)'] < s]
    
    window = 2
    rolling_mean = df_filtered['throughput_per_T'].rolling(window=window, center=True).mean()
    rolling_std = df_filtered['throughput_per_T'].rolling(window=window, center=True).std()
    
    plt.fill_between(df_filtered['Time (sec)'],
                     rolling_mean - rolling_std,
                     rolling_mean + rolling_std,
                     color=color, alpha=0.2)
    
    plt.plot(df_filtered['Time (sec)'], rolling_mean,
             color=color, label=label, linestyle='-')
    
    for tick in xticks:
        closest_idx = (df_filtered['Time (sec)'] - tick).abs().idxmin()
        plt.plot(df_filtered['Time (sec)'].iloc[closest_idx], 
                rolling_mean.iloc[closest_idx], 
                color=color, marker=marker, markersize=6)

plt.title('Average Throughput vs Time Horizon (T)', fontsize=15, weight='bold')
plt.xlabel('Time Horizon (T)', fontsize=15, weight='bold')
plt.ylabel('Average Throughput', fontsize=15, weight='bold')

handles, labels = plt.gca().get_legend_handles_labels()
new_handles = []
for handle, label, marker, color in zip(handles, labels, markers, colors):
    new_handle = plt.Line2D([], [], color=color, linestyle='-', marker=marker, markersize=6, label=label)
    new_handles.append(new_handle)

for i, label in enumerate(labels):
    if label == 'WAIT':
        labels[i] = r"$\bf{WAIT}$"
    if label == 'Nested WAIT':
        labels[i] = r"$\bf{Nested\ WAIT}$"

plt.legend(new_handles, labels, loc='lower right', prop=font_prop, scatterpoints=1, handletextpad=0.5)

plt.xticks(xticks, fontproperties=font_prop)
plt.yticks(fontproperties=font_prop)

# 设置网格线样式（手动添加，避免 Seaborn 干扰）
plt.grid(True, linestyle='--', alpha=0.5, color='gray')

# 设置边框
plt.gca().spines['top'].set_color('black')
plt.gca().spines['top'].set_linewidth(0.5)
plt.gca().spines['right'].set_color('black')
plt.gca().spines['right'].set_linewidth(0.5)
plt.gca().spines['bottom'].set_color('black')
plt.gca().spines['bottom'].set_linewidth(0.5)
plt.gca().spines['left'].set_color('black')
plt.gca().spines['left'].set_linewidth(0.5)

# 设置刻度线向外延伸（放在最后，确保生效）
plt.tick_params(axis='both', which='major', direction='out', length=8, width=0.5)

plt.tight_layout()
plt.savefig(f"/Users/luogan/Code/vidur_or/PDF/{add}_throughput.pdf")
plt.show()

# 绘制第二个图：Normalized Request E2E Time vs Row Number
plt.figure(figsize=(7, 6))

xticks = np.arange(0, a + 1000, 1000)

for file_path, label, marker, color in zip(e2e_file_paths, labels_e2e, markers, colors):
    df_e2e = pd.read_csv(file_path)
    
    window = 100
    rolling_mean = df_e2e['request_e2e_time_normalized'][:a].rolling(window=window, center=True).mean()
    rolling_std = df_e2e['request_e2e_time_normalized'][:a].rolling(window=window, center=True).std()
    
    plt.fill_between(df_e2e.index[:a],
                     rolling_mean - rolling_std,
                     rolling_mean + rolling_std,
                     color=color, alpha=0.2)
    
    plt.plot(df_e2e.index[:a], rolling_mean,
             color=color, label=label, linestyle='-')
    
    for tick in xticks:
        if tick < a:
            closest_idx = min(tick, len(df_e2e.index[:a]) - 1)
            plt.plot(df_e2e.index[int(closest_idx)], 
                    rolling_mean.iloc[int(closest_idx)], 
                    color=color, marker=marker, markersize=6)

plt.title('Average Latency vs Prompt Number (N)', fontsize=15, weight='bold')
plt.xlabel('Prompt Number (N)', fontsize=15, weight='bold')
plt.ylabel('Average Latency',  fontsize=15, weight='bold')

handles, labels = plt.gca().get_legend_handles_labels()
new_handles = []
for handle, label, marker, color in zip(handles, labels, markers, colors):
    new_handle = plt.Line2D([], [], color=color, linestyle='-', marker=marker, markersize=6, label=label)
    new_handles.append(new_handle)

for i, label in enumerate(labels):
    if label == 'WAIT':
        labels[i] = r"$\bf{WAIT}$"
    if label == 'Nested WAIT':
        labels[i] = r"$\bf{Nested\ WAIT}$"

plt.legend(new_handles, labels, loc='lower right', prop=font_prop, scatterpoints=1, handletextpad=0.5)

plt.xticks(xticks, fontproperties=font_prop)
plt.yticks(fontproperties=font_prop)

# 设置网格线样式
plt.grid(True, linestyle='--', alpha=0.5, color='gray')

plt.gca().spines['top'].set_color('black')
plt.gca().spines['top'].set_linewidth(0.5)
plt.gca().spines['right'].set_color('black')
plt.gca().spines['right'].set_linewidth(0.5)
plt.gca().spines['bottom'].set_color('black')
plt.gca().spines['bottom'].set_linewidth(0.5)
plt.gca().spines['left'].set_color('black')
plt.gca().spines['left'].set_linewidth(0.5)

# 设置刻度线向外延伸（放在最后，确保生效）
plt.tick_params(axis='both', which='major', direction='out', length=8, width=0.5)

plt.tight_layout()
plt.savefig(f"/Users/luogan/Code/vidur_or/PDF/{add}_latency.pdf")
plt.show()