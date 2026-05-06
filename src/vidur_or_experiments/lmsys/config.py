"""Configuration objects for the paper-facing LMSYS reproduction grid."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_DB_PATH = REPO_ROOT / "outputs" / "databases" / "lmsys_section6_reproduction.db"
DEFAULT_RUNNER = REPO_ROOT / "scripts" / "real_data_provenance_rerun.py"


def comma_range(start: int, stop: int, step: int) -> str:
    return ",".join(str(value) for value in range(start, stop + 1, step))


@dataclass(frozen=True)
class Section6LmsysConfig:
    """Single source of truth for the manuscript Section 6 LMSYS grid."""

    run_tag: str = ""
    db_path: Path = DEFAULT_DB_PATH
    table: str = "real_data_provenance_runs"
    output_root: Path = REPO_ROOT / "outputs" / "real_data_provenance"
    runner: Path = DEFAULT_RUNNER
    mode: str = "all"
    qps: str = field(default_factory=lambda: comma_range(10, 150, 10))
    nreq: int = 5000
    nbins: int = 50
    model_name: str = "meta-llama/Llama-2-7b-hf"
    device: str = "a100"
    memory_margin_fraction: float = 0.01
    prediction_max_prefill_chunk_size: int = 16384
    prediction_max_batch_size: int = 2048
    prediction_max_tokens_per_request: int = 65536
    arrival_rate_round_digits: int = 4
    include_vllm: bool = True
    sarathi_baseline_chunk_sizes: str = "512,256"
    sarathi_baseline_batch_size_cap: int = 256
    wcp_chunk_sizes: str = "128"
    tl_values: str = field(default_factory=lambda: comma_range(40, 300, 20))
    nested_segment_counts: str = "1,2,3,4,5,10,20"
    seg_margins: str = "0.05"
    wait_cp_gate_values: str = "on"
    wait_gate_values: str = "on"
    segment_priority_orders: str = "head"
    trim_head_frac: float = 0.25
    trim_tail_frac: float = 0.25
    limit: int | None = None
    force: bool = False
    prune_stale: bool = False
    print_plan: bool = True
    extra_runner_args: tuple[str, ...] = ()

    def resolved_run_tag(self) -> str:
        if self.run_tag:
            return self.run_tag
        return f"section6_lmsys_reproduction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
