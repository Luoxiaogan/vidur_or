"""
绘制 batch scheduling metrics 图表

三张子图：
1. 总的 admission (num_admissions)
2. 分 type 的 admission
3. num_restarts_in_scheduling
"""

import os
import pandas as pd
import matplotlib.pyplot as plt


def plot_batch_scheduling_metrics(result_dir: str) -> str:
    """
    绘制 batch scheduling metrics 图表

    Args:
        result_dir: 结果目录路径，包含 batch_scheduling_metrics_*.csv

    Returns:
        生成的图片路径
    """
    # 查找 CSV 文件
    csv_files = [f for f in os.listdir(result_dir) if f.startswith('batch_scheduling_metrics_') and f.endswith('.csv')]
    if not csv_files:
        print(f"未找到 batch_scheduling_metrics_*.csv 文件: {result_dir}")
        return None

    csv_path = os.path.join(result_dir, csv_files[0])
    df = pd.read_csv(csv_path)

    # 获取 type 列（以 type_ 开头的列）
    type_cols = [col for col in df.columns if col.startswith('type_')]

    # 创建图表
    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)

    # 子图1: 总的 admission
    ax1 = axes[0]
    ax1.plot(df['batch_id'], df['num_admissions'], 'b-', linewidth=0.8, alpha=0.8)
    ax1.set_ylabel('Num Admissions')
    ax1.set_title('Total Admissions per Batch')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(bottom=0)

    # 子图2: 分 type 的 admission
    ax2 = axes[1]
    colors = plt.cm.tab10.colors
    for i, col in enumerate(type_cols):
        type_name = col.replace('type_', '')
        # 当 num_admissions=0 时，type 值为 NaN，填充为 0
        values = df[col].fillna(0)
        ax2.plot(df['batch_id'], values, color=colors[i % len(colors)],
                 linewidth=0.8, alpha=0.8, label=f'Type {type_name}')
    ax2.set_ylabel('Admissions by Type')
    ax2.set_title('Admissions by Type per Batch')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(bottom=0)

    # 子图3: num_restarts_in_scheduling
    ax3 = axes[2]
    ax3.plot(df['batch_id'], df['num_restarts_in_scheduling'], 'r-', linewidth=0.8, alpha=0.8)
    ax3.set_xlabel('Batch Index')
    ax3.set_ylabel('Num Restarts')
    ax3.set_title('Restarts in Scheduling per Batch')
    ax3.grid(True, alpha=0.3)
    ax3.set_ylim(bottom=0)

    plt.tight_layout()

    # 保存图片
    output_path = os.path.join(result_dir, 'batch_scheduling_metrics.png')
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"已生成图表: {output_path}")
    return output_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result_dir = sys.argv[1]
    else:
        # 默认使用最新的结果目录
        results_dir = os.path.join(os.path.dirname(__file__), "results")
        if os.path.exists(results_dir):
            dirs = sorted([d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))])
            if dirs:
                result_dir = os.path.join(results_dir, dirs[-1])
            else:
                print("未找到结果目录")
                sys.exit(1)
        else:
            print("results 目录不存在")
            sys.exit(1)

    plot_batch_scheduling_metrics(result_dir)
