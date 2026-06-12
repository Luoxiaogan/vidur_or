-- Selected single-type Llama-2/cap-256 boundary winners.
--
-- Database:
--   outputs/databases/section6_single_type_reproduction.db
--
-- Selection tag:
--   section6_single_type_l2_cap256_boundary_winners_n10000_seed42_20260507
--
-- This query intentionally reads the durable selected-winner table rather
-- than recomputing winners from all exploratory runs.

.mode column
.headers on

SELECT
  arrival_rate AS qps,
  baseline_run_tag,
  printf('%.3f', baseline_mean_latency) AS sarathi_mean_s,
  wcp_run_tag,
  wcp_config_name,
  printf('%.3f', wcp_mean_latency) AS wait_mean_s,
  printf('%.1f%%', win_pct) AS win,
  total_limit AS tl,
  chunk_size,
  wait_gate
FROM single_type_selected_winners
WHERE selection_tag = 'section6_single_type_l2_cap256_boundary_winners_n10000_seed42_20260507'
ORDER BY arrival_rate;
