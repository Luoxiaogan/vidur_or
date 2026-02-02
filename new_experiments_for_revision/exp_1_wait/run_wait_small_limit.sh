#!/bin/bash
# WAIT 实验 - total_limit=21
# 输出目录: 比较测试_3_1_baseline_use_defaults/wait_small_limit

cd /home/lg/vidur_or

OUTPUT_DIR="new_experiments_for_revision/exp_1_wait/比较测试_3_1_baseline_use_defaults/wait_small_limit_new"
mkdir -p "$OUTPUT_DIR"

for rate in 14 15 16 17 18 19 20; do
    echo "===== Running rate=$rate ====="
    python -m vidur.main \
        --replica_config_device a100 \
        --replica_config_model_name "meta-llama/Meta-Llama-3-8B" \
        --replica_config_memory_margin_fraction 0.1 \
        --cluster_config_num_replicas 1 \
        --replica_config_tensor_parallel_size 1 \
        --replica_config_num_pipeline_stages 1 \
        --request_generator_config_type custom \
        --custom_request_generator_config_max_tokens 650 \
        --custom_request_generator_config_prompt_types "[{\"type\":\"type1\",\"prefill\":630,\"decode\":20,\"arrival_rate\":$rate}]" \
        --custom_request_generator_config_num_requests 10000 \
        --replica_scheduler_config_type general_nested_booking_limit \
        --general_nested_booking_limit_scheduler_config_prompt_types "[{\"type\":\"type1\",\"prefill\":630,\"decode\":20,\"arrival_rate\":$rate}]" \
        --general_nested_booking_limit_scheduler_config_total_limit 1 \
        --general_nested_booking_limit_scheduler_config_total_num_requests 10000 \
        --general_nested_booking_limit_scheduler_config_force_clear \
        --random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size 16384 \
        --random_forrest_execution_time_predictor_config_prediction_max_batch_size 2048 \
        --random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request 65536 \
        --metrics_config_keep_individual_batch_metrics

    # 复制结果到目标目录
    latest=$(ls -td simulator_output/*/ | head -1)
    cp -r "$latest" "$OUTPUT_DIR/lambda${rate}_req10000_prefill630_decode20_$(date +%Y%m%d_%H%M%S)"
    echo "Copied to $OUTPUT_DIR"
done

echo "===== All experiments completed! ====="
