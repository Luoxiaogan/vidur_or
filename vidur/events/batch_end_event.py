from typing import List

from vidur.entities import Batch
from vidur.events import BaseEvent
from vidur.logger import init_logger
from vidur.metrics import MetricsStore
from vidur.scheduler import BaseGlobalScheduler
from vidur.types import EventType

logger = init_logger(__name__)


class BatchEndEvent(BaseEvent):
    def __init__(self, time: float, replica_id: int, batch: Batch):
        super().__init__(time, EventType.BATCH_END)

        self._replica_id = replica_id
        self._batch = batch

    def handle_event(
        self, scheduler: BaseGlobalScheduler, metrics_store: MetricsStore
    ) -> List[BaseEvent]:
        from vidur.events.replica_schedule_event import ReplicaScheduleEvent

        self._batch.on_batch_end(self.time)
        replica_scheduler = scheduler.get_replica_scheduler(self._replica_id)
        replica_scheduler.on_batch_end(self._batch)

        # 计算 batch 内所有 requests 数量
        num_requests_in_batch = len(self._batch.requests)
        # **累计 throughput**
        last_throughput = metrics_store._throughput_metric._peek_y()  
        # 获取上一次 throughput 值
        new_throughput = last_throughput + num_requests_in_batch
        # 更新 throughput
        metrics_store._throughput_metric.put(self.time, new_throughput)

        memory_usage_percent = replica_scheduler.memory_usage_percent

        # 计算 batch_kv_tokens_percent = batch_total_kv_tokens / c_tokens * 100
        batch_total_kv_tokens = sum(r.num_processed_tokens for r in self._batch.requests)
        c_tokens = replica_scheduler._config.num_blocks * replica_scheduler._config.block_size
        batch_kv_tokens_percent = (batch_total_kv_tokens / c_tokens) * 100

        # 获取 CPU 队列长度（等待进入 GPU 的请求数）
        cpu_queue_length = replica_scheduler.cpu_queue_length

        metrics_store.on_batch_end(
            self.time, self._batch, self._replica_id,
            memory_usage_percent, batch_kv_tokens_percent, cpu_queue_length
        )

        return [ReplicaScheduleEvent(self.time, self._replica_id)]

    def to_dict(self):
        return {
            "time": self.time,
            "event_type": self.event_type,
            "batch_id": self._batch.id,
        }
