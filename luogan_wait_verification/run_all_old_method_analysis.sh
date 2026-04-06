#!/bin/bash
# run_all_old_method_analysis.sh
# 使用旧脚本方法（基于 my_request_metrics.csv 的滑动窗口）统一分析 throughput 和 latency
# 所有参数在此脚本中配置

set -e

# ============================================
# 参数配置区域（用户可修改）
# ============================================

# 输入目录
BATCH_DIR="/home/CPU/vidur_or/luogan_wait_verification/single/batch_20260406_170402"

# Latency 分析参数
LATENCY_WINDOW=5.0        # 滑动窗口大小（秒）
LATENCY_STEP=0.5          # 滑动步长（秒）
LATENCY_START_TIME=25.0   # 稳态起始时间（秒）
LATENCY_END_TIME=100.0    # 稳态结束时间（秒）

# Throughput 分析参数
THROUGHPUT_WINDOW=5.0     # 滑动窗口大小（秒）
THROUGHPUT_STEP=0.5       # 滑动步长（秒）
THROUGHPUT_START_TIME=50.0  # 稳态起始时间（秒）
THROUGHPUT_END_TIME=180.0   # 稳态结束时间（秒）

# 脚本目录
SCRIPT_DIR="/home/CPU/vidur_or/luogan_wait_verification"

# ============================================
# 执行部分（通常不需要修改）
# ============================================

echo "================================================================================"
echo "Unified Analysis using Old Method (my_request_metrics.csv)"
echo "================================================================================"
echo "Batch directory: $BATCH_DIR"
echo ""
echo "Latency Parameters:"
echo "  Window: ${LATENCY_WINDOW}s, Step: ${LATENCY_STEP}s"
echo "  Steady-state: [${LATENCY_START_TIME}, ${LATENCY_END_TIME}]s"
echo ""
echo "Throughput Parameters:"
echo "  Window: ${THROUGHPUT_WINDOW}s, Step: ${THROUGHPUT_STEP}s"
echo "  Steady-state: [${THROUGHPUT_START_TIME}, ${THROUGHPUT_END_TIME}]s"
echo ""

# 检查目录是否存在
if [ ! -d "$BATCH_DIR" ]; then
    echo "Error: Batch directory does not exist: $BATCH_DIR"
    exit 1
fi

# 检查 Python 脚本是否存在
if [ ! -f "$SCRIPT_DIR/analyze_throughput_old_method.py" ]; then
    echo "Error: Throughput analysis script not found: $SCRIPT_DIR/analyze_throughput_old_method.py"
    exit 1
fi

if [ ! -f "$SCRIPT_DIR/analyze_latency_old_method.py" ]; then
    echo "Error: Latency analysis script not found: $SCRIPT_DIR/analyze_latency_old_method.py"
    exit 1
fi

# 执行 Throughput 分析
echo "================================================================================"
echo "Step 1: Throughput Analysis (Old Method)"
echo "================================================================================"
cd /home/CPU/vidur_or
python "$SCRIPT_DIR/analyze_throughput_old_method.py" "$BATCH_DIR" \
    --window "$THROUGHPUT_WINDOW" \
    --step "$THROUGHPUT_STEP" \
    --start-time "$THROUGHPUT_START_TIME" \
    --end-time "$THROUGHPUT_END_TIME"

echo ""
echo ""

# 执行 Latency 分析
echo "================================================================================"
echo "Step 2: Latency Analysis (Old Method)"
echo "================================================================================"
cd /home/CPU/vidur_or
python "$SCRIPT_DIR/analyze_latency_old_method.py" "$BATCH_DIR" \
    --window "$LATENCY_WINDOW" \
    --step "$LATENCY_STEP" \
    --start-time "$LATENCY_START_TIME" \
    --end-time "$LATENCY_END_TIME"

echo ""
echo "================================================================================"
echo "All analyses completed!"
echo "================================================================================"
echo ""
echo "Output locations:"
echo "  - Throughput: $BATCH_DIR/analysis_old_method/throughput_*.png"
echo "  - Latency:    $BATCH_DIR/analysis_old_method/latency_*.png"
echo "  - Summary:    $BATCH_DIR/analysis_old_method/*_summary_old_method.csv"
echo "================================================================================"
