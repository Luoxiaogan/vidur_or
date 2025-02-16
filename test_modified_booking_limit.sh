NUM_REQUESTS=100  # 你想要的请求总数

python -m vidur.main \
  --replica_config_device a100 \
  --replica_config_model_name meta-llama/Meta-Llama-3-8B \
  --cluster_config_num_replicas 1 \
  --replica_config_tensor_parallel_size 1 \
  --replica_config_num_pipeline_stages 1 \
  --request_generator_config_type custom \
  --custom_request_generator_config_prompt_types '[
  {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 6000}, 
  {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 4000}, 
  {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 8000}]' \
  --custom_request_generator_config_num_requests $NUM_REQUESTS \
  --replica_scheduler_config_type modified_booking_limit \
  --modified_booking_limit_scheduler_config_prompt_types '[
  {"type": "type1", "prefill": 20, "decode": 100, "arrival_rate": 6000}, 
  {"type": "type2", "prefill": 20, "decode": 200, "arrival_rate": 4000}, 
  {"type": "type3", "prefill": 20, "decode": 300, "arrival_rate": 8000}]' \
  --modified_booking_limit_scheduler_config_total_num_requests $NUM_REQUESTS \
  --modified_booking_limit_scheduler_config_total_limit 100 \
  --modified_booking_limit_scheduler_config_force_clear  \
  --random_forrest_execution_time_predictor_config_prediction_max_prefill_chunk_size 16384 \
  --random_forrest_execution_time_predictor_config_prediction_max_batch_size 2048 \
  --random_forrest_execution_time_predictor_config_prediction_max_tokens_per_request 16384

# 对于 --modified_booking_limit_scheduler_config_force_clear  \, 这是启用的意思
# 禁用的方法是: 直接删掉这一行, 就是在request到达完了之后, 不强制清除，而是继续调度执行