"""
PD分离场景的vLLM调度器

继承VLLMReplicaScheduler，修改抢占逻辑：
- restart时保持is_prefill_complete=True（模拟KV cache从CPU重新加载到GPU）
- 被抢占的请求放回队列最前面
"""
from vidur.entities.batch import Batch, Request
from vidur.scheduler.replica_scheduler.vllm_replica_scheduler import (
    VLLMReplicaScheduler,
)


class VLLMPDSeparatedReplicaScheduler(VLLMReplicaScheduler):
    """
    PD分离场景的vLLM调度器

    与标准vLLM调度器的唯一区别：
    - 抢占时使用_pd_restart()而非restart()
    - _pd_restart()保持is_prefill_complete=True，模拟KV cache从CPU重新加载
    """

    def _pd_restart(self, request: Request) -> None:
        """
        PD分离版restart：保持is_prefill_complete=True

        模拟：Prefill的KV cache存储在CPU内存中，
        被抢占后只需重新加载到GPU，无需重新计算prefill
        """
        request._num_processed_tokens = request._num_prefill_tokens
        request._scheduled = False
        request._preempted = False
        request._completed = False
        # 关键：不重置 _is_prefill_complete，保持为True
        request._num_restarts += 1

    def _get_next_batch(self) -> Batch:
        """
        重写_get_next_batch，将restart()替换为_pd_restart()
        """
        requests = []
        num_tokens = []
        num_batch_tokens = 0

        # 新增：统计变量
        num_admissions = 0
        admission_by_type = {}
        num_restarts_in_scheduling = 0

        while self._request_queue:
            request = self._request_queue[0]

            next_num_tokens = self._get_request_next_num_tokens(request)

            if not self._can_allocate_request(request):
                break

            new_num_tokens = num_tokens + [next_num_tokens]
            new_num_batch_tokens = len(new_num_tokens) * max(new_num_tokens)
            if new_num_batch_tokens > self._config.max_tokens_in_batch:
                break

            if len(self._allocation_map) == self._config.batch_size_cap:
                break

            if len(requests) == self._max_micro_batch_size:
                break

            request = self._request_queue.pop(0)

            # 新增：统计 admission
            num_admissions += 1
            prompt_type = getattr(request, 'prompt_type', 'default')
            admission_by_type[prompt_type] = admission_by_type.get(prompt_type, 0) + 1

            self._allocate_request(request)
            requests.append(request)
            num_tokens.append(next_num_tokens)
            num_batch_tokens += next_num_tokens

        if requests:
            return Batch(
                self._replica_id, requests, num_tokens,
                num_admissions=num_admissions,
                admission_by_type=admission_by_type,
                num_restarts_in_scheduling=num_restarts_in_scheduling,
            )

        # Safer to sort preempted_requests to maintain FIFO order
        self._preempted_requests.sort(key=lambda r: r.arrived_at)
        # all preempted_requests will have prefill completed
        while self._preempted_requests:
            if len(requests) == self._max_micro_batch_size:
                break

            request = self._preempted_requests.pop(0)

            while not self._can_allocate_request(request):
                if self._preempted_requests:
                    victim_request = self._preempted_requests.pop(-1)
                    self._pd_restart(victim_request)  # 改为_pd_restart
                    num_restarts_in_scheduling += 1  # 新增：统计 _pd_restart
                    self.free(victim_request.id)
                    self._request_queue = [victim_request] + self._request_queue
                else:
                    self._pd_restart(request)  # 改为_pd_restart
                    num_restarts_in_scheduling += 1  # 新增：统计 _pd_restart
                    self.free(request.id)
                    self._request_queue = [request] + self._request_queue
                    break
            else:
                self._allocate_request(request)
                next_num_tokens = self._get_request_next_num_tokens(request)
                requests.append(request)
                num_tokens.append(next_num_tokens)

        if not requests:
            return

        return Batch(
            self._replica_id, requests, num_tokens,
            num_admissions=num_admissions,
            admission_by_type=admission_by_type,
            num_restarts_in_scheduling=num_restarts_in_scheduling,
        )
