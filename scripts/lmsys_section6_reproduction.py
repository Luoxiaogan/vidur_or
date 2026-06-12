#!/usr/bin/env python3
"""Paper-facing LMSYS Section 6 reproduction entrypoint."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from vidur_or_experiments.lmsys import Section6LmsysConfig, build_runner_command
from vidur_or_experiments.lmsys.config import DEFAULT_DB_PATH
from vidur_or_experiments.lmsys.database import record_reproduction_config


def parse_args() -> argparse.Namespace:
    defaults = Section6LmsysConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-tag", default="")
    parser.add_argument("--db-path", type=Path, default=DEFAULT_DB_PATH)
    parser.add_argument("--mode", choices=["all", "baselines", "wcp"], default="all")
    parser.add_argument("--qps", default=defaults.qps)
    parser.add_argument("--wcp-chunk-sizes", default=defaults.wcp_chunk_sizes)
    parser.add_argument("--tl-values", default=defaults.tl_values)
    parser.add_argument("--nested-segment-counts", default=defaults.nested_segment_counts)
    parser.add_argument("--seg-margins", default=defaults.seg_margins)
    parser.add_argument("--wait-cp-gate-values", default=defaults.wait_cp_gate_values)
    parser.add_argument("--wait-gate-values", default=defaults.wait_gate_values)
    parser.add_argument("--segment-priority-orders", default=defaults.segment_priority_orders)
    parser.add_argument("--trim-head-frac", type=float, default=defaults.trim_head_frac)
    parser.add_argument("--trim-tail-frac", type=float, default=defaults.trim_tail_frac)
    parser.add_argument("--sarathi-baseline-chunk-sizes", default=defaults.sarathi_baseline_chunk_sizes)
    parser.add_argument(
        "--sarathi-baseline-batch-size-cap",
        type=int,
        default=defaults.sarathi_baseline_batch_size_cap,
        help=(
            "Maximum Sarathi scheduled requests per iteration. The default 256 keeps "
            "the baseline inside the Section 6 simulator calibration range while "
            "preserving Sarathi's 512-token chunked-prefill setting."
        ),
    )
    parser.add_argument("--include-vllm", action="store_true", default=True)
    parser.add_argument("--no-include-vllm", action="store_false", dest="include_vllm")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--prune-stale", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Run the generated command. Default only prints the plan.")
    parser.add_argument("--print-plan", action="store_true", help="Force runner --print-plan even when executing.")
    parser.add_argument(
        "--runner-arg",
        action="append",
        default=[],
        help="Extra argument appended to real_data_provenance_rerun.py. Repeat for multiple args.",
    )
    return parser.parse_args()


def build_config(args: argparse.Namespace) -> Section6LmsysConfig:
    return Section6LmsysConfig(
        run_tag=args.run_tag,
        db_path=args.db_path,
        mode=args.mode,
        qps=args.qps,
        include_vllm=args.include_vllm,
        sarathi_baseline_chunk_sizes=args.sarathi_baseline_chunk_sizes,
        sarathi_baseline_batch_size_cap=args.sarathi_baseline_batch_size_cap,
        wcp_chunk_sizes=args.wcp_chunk_sizes,
        tl_values=args.tl_values,
        nested_segment_counts=args.nested_segment_counts,
        seg_margins=args.seg_margins,
        wait_cp_gate_values=args.wait_cp_gate_values,
        wait_gate_values=args.wait_gate_values,
        segment_priority_orders=args.segment_priority_orders,
        trim_head_frac=args.trim_head_frac,
        trim_tail_frac=args.trim_tail_frac,
        limit=args.limit,
        force=args.force,
        prune_stale=args.prune_stale,
        print_plan=args.print_plan or not args.execute,
        extra_runner_args=tuple(args.runner_arg),
    )


def main() -> int:
    config = build_config(parse_args())
    command = build_runner_command(config)
    record_reproduction_config(
        config,
        notes="Paper-facing Section 6 LMSYS reproduction scaffold.",
    )
    print(" ".join(command), flush=True)
    return subprocess.run(command, cwd=REPO_ROOT).returncode


if __name__ == "__main__":
    raise SystemExit(main())
