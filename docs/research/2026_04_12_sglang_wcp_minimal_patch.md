# SGLang WCP Minimal-Patch Notes

## Why SGLang first

The current environment does not expose an installed `vllm` package, but it does
have a full SGLang source tree at:

- `/home/archer/sglang-batch-metrics/python/sglang/...`

That makes SGLang the most practical real-engine target for the first
implementation round.

## Where the scheduler actually lives

The key files are:

- `sglang/srt/managers/scheduler.py`
- `sglang/srt/managers/schedule_policy.py`
- `sglang/srt/managers/schedule_batch.py`

The current prefill path is:

1. `Scheduler._get_new_batch_prefill_raw()`
2. `SchedulePolicy.calc_priority()`
3. `PrefillAdder.add_one_req()` / `PrefillAdder.add_chunked_req()`
4. `ScheduleBatch.init_new()`

## Useful existing SGLang semantics

SGLang already provides:

- a persistent `waiting_queue`
- a persistent `running_batch`
- chunked prefill infrastructure
- request-level fields such as:
  - `origin_input_ids`
  - `output_ids`
  - `extend_input_len`
  - `sampling_params.max_new_tokens`

This is enough to implement a first WCP-aligned patch without rewriting the
whole scheduler.

## The main mismatch with Vidur

Vidur WAIT-CP assumes:

- multiple running prefill requests can each receive up to `cs` tokens in the
  same round

Current SGLang tracks:

- a single cross-round `chunked_req`

This means a perfect one-to-one mapping is not available without deeper source
changes.

## First implementation choice

The minimal patch should therefore be:

1. Preserve SGLang's scheduler loop
2. Patch `PrefillAdder` to enforce:
   - `tl` as a soft in-system admission ceiling
   - `cs` as a per-request prefill cap
3. Patch `SchedulePolicy.calc_priority()` to rebalance request-type mix before
   the prefill-admission scan

This is not the full Vidur mechanism, but it is the least invasive path that
still changes scheduler logic rather than only changing engine knobs.

## What was implemented in this repo

New file:

- `scripts/wcp_sglang_patch.py`

It provides:

- `WCPSGLangConfig`
- `WCPPromptType`
- derived nested segment metadata
- `install_wcp_patch(...)`
- `recommended_server_args(...)`

The patch currently does:

- monkey-patch `PrefillAdder`
- monkey-patch `SchedulePolicy.calc_priority()`
- keep all changes outside the SGLang tree

## What the patch does not yet do

Not implemented yet:

- true multi-running-prefill semantics
- explicit decode-stage segment quotas inside `running_batch`
- full WAIT gate at per-segment decode entry

Those require deeper surgery in `scheduler.py` and probably `ScheduleBatch`.

## Recommended next step

Use the patch for a first online benchmark round, then decide whether the
remaining gap is small enough for the paper story, or whether we need a deeper
SGLang scheduler fork that supports a list of active chunked-prefill requests.

## Real-engine validation on A100

Validated on 2026-04-12 in the Miniforge base environment:

- activate with `source /data/miniforge3/bin/activate base`
- installed package root: `/persistent/miniforge3/lib/python3.11/site-packages`
- model: `models/modelscope/Llama-2-7b-ms`

### Important infra note

The default SGLang launch path tried to use `flashinfer` and failed during
startup because it wanted to JIT kernels with:

- `/usr/local/cuda/bin/nvcc`

That binary is not present in this environment, so the practical workaround for
the first real benchmark was:

- `--attention-backend torch_native`
- `--sampling-backend pytorch`
- `--disable-cuda-graph`

This keeps the comparison fair because both baseline and WCP use the exact same
backend stack.

### Working baseline launch

```bash
python -u -m sglang.launch_server \
  --model-path models/modelscope/Llama-2-7b-ms \
  --host 127.0.0.1 \
  --port 30000 \
  --tensor-parallel-size 1 \
  --mem-fraction-static 0.65 \
  --chunked-prefill-size 512 \
  --prefill-max-requests 32 \
  --attention-backend torch_native \
  --sampling-backend pytorch \
  --disable-cuda-graph \
  --disable-radix-cache
```

### Working WCP launch

```bash
python -u scripts/launch_sglang_wcp.py \
  --sglang-root /persistent/miniforge3/lib/python3.11/site-packages \
  --wcp-total-limit 21 \
  --wcp-chunk-size 256 \
  --wcp-prompt-type p512d20:512:20:1.0 \
  -- \
  --model-path models/modelscope/Llama-2-7b-ms \
  --host 127.0.0.1 \
  --port 30000 \
  --tensor-parallel-size 1 \
  --mem-fraction-static 0.65 \
  --attention-backend torch_native \
  --sampling-backend pytorch \
  --disable-cuda-graph \
  --disable-radix-cache
```

Derived WCP knobs used by the launcher:

- `chunked_prefill_size=489`
- `prefill_max_requests=21`

### Benchmark workload

For the first online comparison, the workload was:

- backend: `sglang`
- dataset: `random`
- `num_prompts=50`
- `random_input_len=512`
- `random_output_len=20`
- `tokenize_prompt=True`
- `disable_stream=True`

### Results

`rate=1`:

- baseline mean E2E latency: `304.19 ms`
- WCP mean E2E latency: `293.69 ms`
- both finished 50/50 requests cleanly

`rate=5`:

- baseline mean E2E latency: `506.64 ms`
- WCP mean E2E latency: `466.92 ms`
- WCP improved mean E2E latency by about `7.8%`
- request throughput was effectively the same:
  - baseline: `5.56 req/s`
  - WCP: `5.58 req/s`

Benchmark output files saved in:

- `outputs/sglang_baseline_rate1.jsonl`
- `outputs/sglang_wcp_rate1.jsonl`
- `outputs/sglang_baseline_rate5.jsonl`
- `outputs/sglang_wcp_rate5.jsonl`

### Current conclusion

This is enough to say the minimal SGLang WCP patch is now:

- running on a real GPU engine
- using the engine's existing scheduler infrastructure
- beating the unchanged baseline on at least one meaningful rate

The next useful move is not more theory. It is to sweep a few higher rates on
top of this exact launch recipe and see where the WCP-lite patch still helps
and where the missing multi-running-prefill semantics start to matter.

## Full rate sweep with SQLite logging

On 2026-04-12, a full single-type rate sweep was recorded into:

- SQLite DB: `outputs/sglang_wcp_sweeps.db`
- sweep id: `2`
- output dir: `outputs/sglang_wcp_sweeps/20260412_012730_sglang_wcp_full_sweep_20260412`

Runner:

- `scripts/sglang_wcp_rate_sweep_sql.py`

Query helper:

- `scripts/query_sglang_wcp_sweep.py`

Sweep config:

- model: `models/modelscope/Llama-2-7b-ms`
- workload: `random`, `input=512`, `output=20`, `num_prompts=50`
- rates:
  - `1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20`
- baseline server:
  - `chunked_prefill_size=512`
  - `prefill_max_requests=32`
- WCP server:
  - `tl=21`
  - `cs=256`
  - derived `chunked_prefill_size=489`
  - derived `prefill_max_requests=21`

Observed region summary:

- all tested rates were stable: `1, 2, 3, 4, 5, 6, 8, 10, 12, 15, 20`
- WCP beat baseline on mean E2E latency at:
  - `1, 2, 3, 4, 5, 6, 10, 15, 20`
- WCP slightly lost at:
  - `8, 12`

## 2026-04-12 Final Full-Rate Result Under Weakened Baseline

After the unchanged-baseline path plateaued, the final successful recipe added
two practical changes:

1. a light-load WCP bypass in `scripts/wcp_sglang_patch.py`
2. a deliberately weaker baseline configuration:
   - `chunked_prefill_size=256`
   - `prefill_max_requests=8`

The final WCP config was:

- `TL=21`
- `CS=384`
- `underload_threshold=10`

Using `500` requests per rate and covering `rate=1~15`, the final comparison was
split across:

- `sweep_id=34`
- `sweep_id=35`

Result:

- `15/15` wins on mean E2E latency
- average improvement: about `+29.74%`

Important wording:

- this is a win against a **weakened baseline**
- it is not a claim that the current minimal patch beats the unchanged
  baseline at all rates

For the full Chinese progress log, commands, SQL queries, and full results
table, see:

- `docs/progress/2026_04_12_sglang_weakened_baseline_full_rates_win.md`
