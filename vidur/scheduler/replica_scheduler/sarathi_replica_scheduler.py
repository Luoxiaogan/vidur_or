from math import ceil

from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.base_replica_scheduler import (
    BaseReplicaScheduler,
)


class SarathiReplicaScheduler(BaseReplicaScheduler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # sarathi config
        self._num_running_batches = 0
        self._preempted_requests = []
        # For vLLM and its derivatives, we only need to set a loose max batch size
        # Memory requirements are handled explicitly by the scheduler
        self._max_micro_batch_size = self._config.batch_size_cap // self._num_stages
        self._watermark_blocks = int(
            self._config.watermark_blocks_fraction * self._config.num_blocks
        )

    def _can_allocate_request(self, request: Request) -> bool:
        if request.id not in self._allocation_map:
            # new request
            num_required_blocks = ceil(
                request.num_prefill_tokens / self._config.block_size
            )
            return (
                self._config.num_blocks
                - self._num_allocated_blocks
                - num_required_blocks
                >= self._watermark_blocks
            )

        # vllm requires at least one block to be available
        return self._config.num_blocks - self._num_allocated_blocks >= 1

    def _allocate_request(self, request: Request) -> None:
        if request.id not in self._allocation_map:
            # new request
            num_required_blocks = ceil(
                request.num_prefill_tokens / self._config.block_size
            )
            self.allocate(request.id, num_required_blocks)
            return

        num_tokens_reserved = self._allocation_map[request.id] * self._config.block_size
        num_tokens_required = max(0, request.num_processed_tokens - num_tokens_reserved)

        assert (
            num_tokens_required == 0 or num_tokens_required == 1
        ), f"num_tokens_required: {num_tokens_required}"

        if num_tokens_required == 0:
            return

        self.allocate(request.id, 1)

    def on_batch_end(self, batch: Batch) -> None:
        self._num_running_batches -= 1

        for request in batch.requests:
            if request.completed:
                self.free(request.id)
            else:
                self._preempted_requests.append(request)

    def _get_request_next_num_tokens(
        self, request: Request, batch_contains_prefill: bool, num_batch_tokens: int
    ) -> int:
        assert not request.completed

        if request.is_prefill_complete:
            return 1

        next_num_tokens = min(
            request.num_prefill_tokens - request.num_processed_tokens,
            self._config.chunk_size - num_batch_tokens,
        )

        next_num_tokens = max(0, next_num_tokens)

        return next_num_tokens

    def _get_next_batch(self) -> Batch:
        requests = []
        num_tokens = []
        skipped_requests = []
        running_prefills = []
        contains_prefill = False
        num_batch_tokens = 0

        # preempted requests could contain multiple requests which have
        # partial prefills completed, so we need to be careful
        while self._preempted_requests:
            if len(requests) == self._max_micro_batch_size:
                break

            request = self._preempted_requests.pop(0)

            if not request.is_prefill_complete:
                running_prefills.append(request)
                continue

            next_num_tokens = self._get_request_next_num_tokens(
                request, contains_prefill, num_batch_tokens
            )

            if next_num_tokens == 0:
                skipped_requests.append(request)
                continue

            while not self._can_allocate_request(request):
                if self._preempted_requests:
                    victim_request = self._preempted_requests.pop(-1)
                    victim_request.restart()
                    self.free(victim_request.id)
                    self._request_queue = [victim_request] + self._request_queue
                else:
                    request.restart()
                    self.free(request.id)
                    self._request_queue = [request] + self._request_queue
                    break
            else:
                self._allocate_request(request)
                assert request.is_prefill_complete
                num_batch_tokens += next_num_tokens
                requests.append(request)
                num_tokens.append(next_num_tokens)

        for request in running_prefills:
            assert not request.is_prefill_complete

            next_num_tokens = self._get_request_next_num_tokens(
                request, contains_prefill, num_batch_tokens
            )

            if next_num_tokens == 0:
                skipped_requests.append(request)
                continue

            contains_prefill = True
            num_batch_tokens += next_num_tokens
            requests.append(request)
            num_tokens.append(next_num_tokens)

        # re-add the skipped requests, but make sure that we add them to the
        # front of the queue so that they are scheduled first and we maintain FIFO ordering
        self._preempted_requests = skipped_requests + self._preempted_requests
        self._preempted_requests = sorted(
            self._preempted_requests, key=lambda req: req.arrived_at
        )
        skipped_requests = []

        while self._request_queue:
            if len(self._allocation_map) == self._config.batch_size_cap:
                break

            if len(requests) == self._max_micro_batch_size:
                break

            if not self._can_allocate_request(self._request_queue[0]):
                break

            next_num_tokens = self._get_request_next_num_tokens(
                self._request_queue[0], contains_prefill, num_batch_tokens
            )

            if next_num_tokens == 0:
                break

            request = self._request_queue.pop(0)

            self._allocate_request(request)

            # all new requests will have a prefill
            contains_prefill = True
            num_batch_tokens += next_num_tokens
            requests.append(request)
            num_tokens.append(next_num_tokens)

        if not requests:
            return

        #  # 分析batch种的请求的组成
        # prefill_incomplete_count = sum(1 for req in requests if not req._is_prefill_complete)
        # num = len(requests)
        # stage1_num = sum(1 for req in requests if req._num_processed_tokens == req._num_prefill_tokens+1)
        # stage_last = sum(1 for req in requests if req._num_processed_tokens == req._num_prefill_tokens+req._num_decode_tokens-1)
        # print(f"prefill数目={prefill_incomplete_count}, stage1数目={stage1_num}, stage_end数目={stage_last}, 总数目={num}, 比例={prefill_incomplete_count/num}")
        return Batch(self._replica_id, requests, num_tokens)

    # def _get_next_batch(self) -> Batch:
    #     requests = []
    #     num_tokens = []
    #     skipped_requests = []
    #     running_prefills = []
    #     contains_prefill = False
    #     num_batch_tokens = 0

    #     # 1. 处理排队队列中的请求
    #     while self._request_queue:
    #         if len(requests) == self._max_micro_batch_size:
    #             break

    #         request = self._request_queue[0]

    #         next_num_tokens = self._get_request_next_num_tokens(request, contains_prefill, num_batch_tokens)

    #         # 如果该请求无法分配资源，停止处理新请求
    #         if not self._can_allocate_request(request):
    #             break

    #         if next_num_tokens == 0:
    #             break

    #         # 分配资源并将请求加入当前批次
    #         self._allocate_request(request)
    #         contains_prefill = True
    #         num_batch_tokens += next_num_tokens
    #         requests.append(request)
    #         num_tokens.append(next_num_tokens)

    #         # 从队列中移除已处理的请求
    #         self._request_queue.pop(0)

    #     # 2. 处理被抢占的请求
    #     for request in self._preempted_requests:
    #         if len(requests) == self._max_micro_batch_size:
    #             break

    #         if request.is_prefill_complete:
    #             next_num_tokens = self._get_request_next_num_tokens(request, contains_prefill, num_batch_tokens)

    #             if next_num_tokens == 0:
    #                 skipped_requests.append(request)
    #                 continue

    #             # 分配资源并将被抢占请求加入当前批次
    #             while not self._can_allocate_request(request):
    #                 if self._preempted_requests:
    #                     victim_request = self._preempted_requests.pop(-1)
    #                     victim_request.restart()
    #                     self.free(victim_request.id)
    #                     self._request_queue = [victim_request] + self._request_queue
    #                 else:
    #                     request.restart()
    #                     self.free(request.id)
    #                     self._request_queue = [request] + self._request_queue
    #                     break
    #             else:
    #                 self._allocate_request(request)
    #                 num_batch_tokens += next_num_tokens
    #                 requests.append(request)
    #                 num_tokens.append(next_num_tokens)

    #     # 3. 重新调整跳过的请求，确保FIFO顺序
    #     self._preempted_requests = skipped_requests + self._preempted_requests
    #     self._preempted_requests = sorted(self._preempted_requests, key=lambda req: req.arrived_at)

    #     # 如果没有请求，返回空
    #     if not requests:
    #         return

    #     return Batch(self._replica_id, requests, num_tokens)
