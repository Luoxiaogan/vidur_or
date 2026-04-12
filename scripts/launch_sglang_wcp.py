#!/usr/bin/env python3
"""
Launch SGLang with the minimal WCP runtime patch enabled.

This script keeps the default SGLang scheduler infrastructure intact and only
installs the lightweight WCP wrapper from `scripts/wcp_sglang_patch.py`.

Example:
python3 scripts/launch_sglang_wcp.py \
  --sglang-root /home/archer/sglang-batch-metrics/python \
  --wcp-total-limit 21 \
  --wcp-chunk-size 256 \
  --wcp-prompt-type p512d20:512:20:1.0 \
  -- \
  --model-path models/modelscope/Llama-2-7b-ms \
  --host 0.0.0.0 \
  --port 30000
"""

import argparse
import sys
from pathlib import Path
from typing import List

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.wcp_sglang_patch import (
    WCPSGLangConfig,
    WCPPromptType,
    install_wcp_patch,
    recommended_server_args,
)


def parse_prompt_type(raw: str) -> WCPPromptType:
    """
    Parse one prompt type definition:
    name:prefill:decode:arrival_rate
    """

    parts = raw.split(":")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError(
            "prompt type must be name:prefill:decode:arrival_rate"
        )
    name, prefill, decode, arrival_rate = parts
    try:
        return WCPPromptType(
            name=name,
            prefill=int(prefill),
            decode=int(decode),
            arrival_rate=float(arrival_rate),
        )
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid prompt type definition: {raw}"
        ) from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Launch SGLang with a minimal WCP scheduler patch."
    )
    parser.add_argument(
        "--sglang-root",
        default="/home/archer/sglang-batch-metrics/python",
        help="Path whose child package is `sglang`.",
    )
    parser.add_argument(
        "--wcp-total-limit",
        type=int,
        default=21,
        help="WCP tl: in-system request ceiling.",
    )
    parser.add_argument(
        "--wcp-chunk-size",
        type=int,
        default=256,
        help="WCP cs: per-request prefill chunk cap.",
    )
    parser.add_argument(
        "--wcp-prompt-type",
        action="append",
        type=parse_prompt_type,
        default=[],
        help="Prompt type in format name:prefill:decode:arrival_rate. Repeatable.",
    )
    parser.add_argument(
        "--disable-wcp-mix-balance",
        action="store_true",
        help="Disable type-mix rebalance when sorting the waiting queue.",
    )
    parser.add_argument(
        "--disable-wcp-segment-bias",
        action="store_true",
        help="Disable segment-aware tie breaking.",
    )
    parser.add_argument(
        "--wcp-prefill-budget",
        type=int,
        default=None,
        help="Override the derived global prefill budget.",
    )
    parser.add_argument(
        "--disable-wcp-underload-bypass",
        action="store_true",
        help="Disable the light-load bypass that keeps WCP close to baseline under underload.",
    )
    parser.add_argument(
        "--wcp-underload-threshold",
        type=int,
        default=None,
        help="In-system request threshold below which WCP bypasses cap/rebalance logic.",
    )
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Print the derived config and resulting SGLang args, then exit.",
    )
    return parser


def _append_if_absent(extra: List[str], flag: str, value: int) -> None:
    if flag not in extra:
        extra.extend([flag, str(value)])


def main(argv: List[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)

    if "--" in argv:
        split_idx = argv.index("--")
        local_argv = argv[:split_idx]
        sglang_argv = argv[split_idx + 1 :]
    else:
        local_argv = argv
        sglang_argv = []

    parser = build_parser()
    args = parser.parse_args(local_argv)

    prompt_types = args.wcp_prompt_type or [
        WCPPromptType(name="p512d20", prefill=512, decode=20, arrival_rate=1.0)
    ]

    config = WCPSGLangConfig(
        total_limit=args.wcp_total_limit,
        chunk_size=args.wcp_chunk_size,
        prompt_types=prompt_types,
        enable_mix_balance=not args.disable_wcp_mix_balance,
        enable_segment_bias=not args.disable_wcp_segment_bias,
        enable_underload_bypass=not args.disable_wcp_underload_bypass,
        underload_bypass_threshold=args.wcp_underload_threshold,
        prefill_budget_tokens=args.wcp_prefill_budget,
        source_root=args.sglang_root,
    )

    derived = recommended_server_args(config)
    _append_if_absent(sglang_argv, "--chunked-prefill-size", derived["chunked_prefill_size"])
    _append_if_absent(sglang_argv, "--prefill-max-requests", derived["prefill_max_requests"])

    if args.print_only:
        print("WCP config:")
        print(f"  total_limit={config.total_limit}")
        print(f"  chunk_size={config.chunk_size}")
        print(f"  weighted_pipeline_depth={config.weighted_pipeline_depth:.3f}")
        print(f"  derived_prefill_budget={config.derived_prefill_budget_tokens}")
        print(f"  underload_bypass={config.enable_underload_bypass}")
        print(
            f"  underload_bypass_threshold={config.effective_underload_bypass_threshold}"
        )
        print(f"  segments={config.segments}")
        print("SGLang args:")
        print("  " + " ".join(sglang_argv))
        return 0

    modules = install_wcp_patch(config)
    from sglang.launch_server import run_server
    from sglang.srt.server_args import prepare_server_args

    server_args = prepare_server_args(sglang_argv)
    print("Installed WCP patch on SGLang runtime.")
    print(f"SGLang source root: {modules['source_root']}")
    print(f"Derived chunked_prefill_size={derived['chunked_prefill_size']}")
    print(f"Derived prefill_max_requests={derived['prefill_max_requests']}")
    print(f"Underload bypass enabled={config.enable_underload_bypass}")
    print(
        f"Underload bypass threshold={config.effective_underload_bypass_threshold}"
    )
    run_server(server_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
