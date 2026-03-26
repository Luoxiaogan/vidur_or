"""
Uniform Segment Chunked Replica Scheduler

用于 single-type 长 decode 场景。将 decode stages 等分为若干 segment，
每个 segment 的 per-stage limit (n_k) 完全相同。

继承 GeneralNestedChunkedReplicaScheduler，只 override segment 计算逻辑。
Batch 构建（per-seg gate、prefill chunking、entry gate）完全复用父类。

参数:
    segment_size: 每个 segment 的 stages 数 (如 200)
    tl: 全局 booking limit
    cs: chunk size (prefill chunking)

Segment 结构示例 (d=1000, segment_size=200):
    Seg 0: stages 0-199,   n_k = tl/1000
    Seg 1: stages 200-399, n_k = tl/1000
    Seg 2: stages 400-599, n_k = tl/1000
    Seg 3: stages 600-799, n_k = tl/1000
    Seg 4: stages 800-999, n_k = tl/1000
"""

from math import ceil
from typing import Dict, List, Tuple
from vidur.scheduler.replica_scheduler.general_nested_chunked_replica_scheduler import (
    GeneralNestedChunkedReplicaScheduler,
)


class UniformSegmentChunkedReplicaScheduler(GeneralNestedChunkedReplicaScheduler):

    def calculate_nested_booking_limits(self) -> Tuple[Dict[int, int], List[Dict]]:
        """
        Override: 等分 segment，每个 segment 的 n_k 相同。

        n_k = tl / total_stages (uniform across all segments)
        seg_total_limit = n_k * stages_in_segment
        """
        segment_size = self._config.segment_size
        pts = self._config.prompt_types if self._config.prompt_types else [{"decode": 20}]
        max_decode = max(pt.get("decode", 20) for pt in pts)

        num_segments = max(1, ceil(max_decode / segment_size))
        total_stages = max_decode

        # Uniform n_k
        n_k = self.total_limit / total_stages if total_stages > 0 else 0

        print(f"UniformSegment: segment_size={segment_size}, num_segments={num_segments}, "
              f"total_stages={total_stages}, n_k={n_k:.4f}")

        nested_booking_limits = {}
        segments_info = []
        global_stage = 0
        total_limit_real = 0

        for k in range(num_segments):
            seg_start = k * segment_size
            seg_end = min((k + 1) * segment_size, max_decode) - 1
            seg_count = seg_end - seg_start + 1

            seg_total_limit_int = int(round(n_k * seg_count))

            # 整数分配: base + 余数
            base = seg_total_limit_int // seg_count if seg_count > 0 else 0
            remainder = seg_total_limit_int % seg_count if seg_count > 0 else 0

            for i in range(seg_count):
                nested_booking_limits[global_stage] = base + 1 if i < remainder else base
                global_stage += 1

            total_limit_real += seg_total_limit_int

            n_k_floor = max(1, int(n_k))
            n_k_ceil = int(ceil(n_k))

            segments_info.append({
                "start": seg_start, "end": seg_end,
                "per_stage_limit": base + 1 if remainder > 0 else base,
                "seg_total_limit": seg_total_limit_int,
                "n_k": n_k, "n_k_floor": n_k_floor, "n_k_ceil": n_k_ceil,
            })
            print(f"  seg {k}: stages {seg_start}-{seg_end}, "
                  f"seg_limit={seg_total_limit_int}, n_k={n_k:.4f}")

        print(f"设定的总limit: {self.total_limit}, 实际的总limit: {total_limit_real}")

        return nested_booking_limits, segments_info
