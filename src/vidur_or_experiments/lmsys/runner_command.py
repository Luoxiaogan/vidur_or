"""Command construction for the LMSYS reproduction runner."""

from __future__ import annotations

from .config import Section6LmsysConfig


def build_runner_command(config: Section6LmsysConfig) -> list[str]:
    """Return the exact real_data_provenance_rerun.py command."""

    command = [
        "python",
        str(config.runner),
        "--run-tag",
        config.resolved_run_tag(),
        "--db-path",
        str(config.db_path),
        "--table",
        config.table,
        "--output-root",
        str(config.output_root),
        "--mode",
        config.mode,
        "--model-name",
        config.model_name,
        "--device",
        config.device,
        "--memory-margin-fraction",
        str(config.memory_margin_fraction),
        "--prediction-max-prefill-chunk-size",
        str(config.prediction_max_prefill_chunk_size),
        "--prediction-max-batch-size",
        str(config.prediction_max_batch_size),
        "--prediction-max-tokens-per-request",
        str(config.prediction_max_tokens_per_request),
        "--qps",
        config.qps,
        "--nreq",
        str(config.nreq),
        "--nbins",
        str(config.nbins),
        "--arrival-rate-round-digits",
        str(config.arrival_rate_round_digits),
        "--sarathi-baseline-chunk-sizes",
        config.sarathi_baseline_chunk_sizes,
        "--sarathi-baseline-batch-size-cap",
        str(config.sarathi_baseline_batch_size_cap),
        "--chunk-sizes",
        config.wcp_chunk_sizes,
        "--seg-margins",
        config.seg_margins,
        "--nested-segment-counts",
        config.nested_segment_counts,
        "--segment-counts",
        "",
        "--wait-cp-gate-values",
        config.wait_cp_gate_values,
        "--wait-gate-values",
        config.wait_gate_values,
        "--segment-priority-orders",
        config.segment_priority_orders,
        "--tl-values",
        config.tl_values,
        "--no-adaptive-tl-grid",
        "--trim-head-frac",
        str(config.trim_head_frac),
        "--trim-tail-frac",
        str(config.trim_tail_frac),
    ]
    if config.include_vllm:
        command.append("--include-vllm")
    if config.prune_stale:
        command.append("--prune-stale")
    if config.force:
        command.append("--force")
    if config.limit is not None:
        command.extend(["--limit", str(config.limit)])
    if config.print_plan:
        command.append("--print-plan")
    command.extend(config.extra_runner_args)
    return command
