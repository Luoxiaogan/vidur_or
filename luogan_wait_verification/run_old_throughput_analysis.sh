#!/bin/bash
# run_old_throughput_analysis.sh
# 使用旧脚本方法（基于 my_request_metrics.csv 的滑动窗口）分析 throughput

set -e

# 配置参数
BATCH_DIR="/home/CPU/vidur_or/luogan_wait_verification/single/batch_20260406_170402"
SCRIPT_DIR="/home/CPU/vidur_or/luogan_wait_verification"

echo "================================================================================"
echo "Throughput Analysis using Old Method (my_request_metrics.csv)"
echo "================================================================================"
echo "Batch directory: $BATCH_DIR"
echo ""

# 检查目录是否存在
if [ ! -d "$BATCH_DIR" ]; then
    echo "Error: Batch directory does not exist: $BATCH_DIR"
    exit 1
fi

# 检查 Python 脚本是否存在
if [ ! -f "$SCRIPT_DIR/analyze_throughput_old_method.py" ]; then
    echo "Error: Python script not found: $SCRIPT_DIR/analyze_throughput_old_method.py"
    exit 1
fi

# 执行分析
echo "Running analysis..."
cd /home/CPU/vidur_or
python "$SCRIPT_DIR/analyze_throughput_old_method.py" "$BATCH_DIR"

echo ""
echo "================================================================================"
echo "Done! Check the output in: $BATCH_DIR/analysis_old_method/"
echo "================================================================================"
