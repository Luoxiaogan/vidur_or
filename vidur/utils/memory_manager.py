"""
Memory Manager for Vidur Simulation - 长时间模拟的内存清理

按完成的请求数触发清理（与 workload 无关，直接反映处理进度）。

清理目标:
    - Simulator._event_trace / _event_chrome_trace（debug 数据）
    - MetricsStore 不清理（结果数据源）
"""

import gc
import logging
from typing import Dict, Optional

import psutil

logger = logging.getLogger(__name__)


class SimulationMemoryManager:
    """模拟专用内存管理器 - 按完成请求数清理 event trace"""

    def __init__(
        self,
        cleanup_every_n_completions: int = 500,
        threshold_gb: float = 12.0,
    ):
        """
        Args:
            cleanup_every_n_completions: 每完成 N 个请求清理一次
            threshold_gb: 内存阈值（仅用于日志报警）
        """
        self.cleanup_every = cleanup_every_n_completions
        self.threshold_gb = threshold_gb
        self.last_cleanup_completions = 0
        self.cleanup_count = 0
        self.process = psutil.Process()

    def step(self, simulator) -> Optional[Dict]:
        """每个 event 调用。按完成请求数触发清理。"""
        completed = getattr(simulator, '_completed_requests', None)
        if completed is None:
            # fallback: 从 metric_store 获取
            ms = getattr(simulator, '_metric_store', None)
            if ms is None:
                return None
            # 用 request metrics 的 data series 长度近似完成数
            try:
                completed = len(ms._request_metrics_time_distributions[
                    list(ms._request_metrics_time_distributions.keys())[0]
                ]._data_series)
            except (KeyError, IndexError, AttributeError):
                return None

        if completed - self.last_cleanup_completions < self.cleanup_every:
            return None

        self.last_cleanup_completions = completed
        return self.periodic_cleanup(simulator)

    def periodic_cleanup(self, simulator) -> Dict:
        """清理 event trace + gc.collect()"""
        before_memory = self.process.memory_info().rss
        trace_stats = self._clear_simulator_traces(simulator)
        collected = gc.collect()
        after_memory = self.process.memory_info().rss

        freed_mb = (before_memory - after_memory) / 1024 ** 2
        current_gb = after_memory / 1024 ** 3
        self.cleanup_count += 1

        if self.cleanup_count % 5 == 1:
            logger.info(
                f"[MemoryManager] cleanup #{self.cleanup_count} "
                f"at {self.last_cleanup_completions} completions: "
                f"freed {freed_mb:.1f}MB, traces -{trace_stats['removed']}, "
                f"mem={current_gb:.2f}GB"
            )

        if current_gb > self.threshold_gb:
            logger.warning(
                f"[MemoryManager] memory {current_gb:.2f}GB "
                f"exceeds threshold {self.threshold_gb}GB"
            )

        return {
            "memory_freed_mb": freed_mb,
            "traces_removed": trace_stats["removed"],
            "gc_collected": collected,
            "current_memory_gb": current_gb,
        }

    def _clear_simulator_traces(self, simulator) -> Dict[str, int]:
        """清理 event trace（debug 用，不影响结果）"""
        total_removed = 0
        for attr_name in ("_event_trace", "_event_chrome_trace"):
            trace_list = getattr(simulator, attr_name, None)
            if trace_list is None or len(trace_list) == 0:
                continue
            total_removed += len(trace_list)
            trace_list.clear()
        return {"removed": total_removed}
