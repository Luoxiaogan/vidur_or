#!/bin/bash
# 运行 vidur 模拟器

python -m vidur.main \
--replica_config_device a100 \
--replica_config_model_name meta-llama/Meta-Llama-3-8B \
--cluster_config_num_replicas 1 \
--replica_config_tensor_parallel_size 1 \
--replica_config_num_pipeline_stages 1 \
--request_generator_config_type custom \
--custom_request_generator_config_num_requests 200 \
--replica_scheduler_config_type nested_booking_limit \
--random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size 16384 \
--random_forrest_execution_time_predictor_config_prediction_max_batch_size 2048 \
--random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request 16384 \
--time_limit 10
