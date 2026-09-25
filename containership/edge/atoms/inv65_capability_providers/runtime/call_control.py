"""Deadlines, cancellation, bounded retries and backpressure (M14).

``Deadline`` is monotonic-clock based and propagated as remaining ms.  Dispatch
runs on a bounded worker pool; a full queue sheds immediately (backpressure)
instead of queueing unboundedly.  Retries only happen for retryable codes, only
for idempotent operations or calls carrying an idempotency key, with capped
exponential backoff + full jitter, and never past the deadline.
"""
from __future__ import annotations

import concurrent.futures as cf
import random
import threading
import time

from ..errors.mapping import CATALOG, ProviderFault

IDEMPOTENT_OPS = frozenset({"get", "head", "list", "exists", "health"})


class Deadline:
    def __init__(self, ms: int, *, clock=time.monotonic):
        if not isinstance(ms, int) or not 1 <= ms <= 600_000:
            raise ProviderFault("PK_PROVIDER_INVALID_LINK", "deadline_ms must be 1..600000")
        self._clock = clock
        self._end = clock() + ms / 1000.0

    def remaining(self) -> float:
        return max(0.0, self._end - self._clock())

    def remaining_ms(self) -> int:
        return int(self.remaining() * 1000)

    def expired(self) -> bool:
        return self.remaining() <= 0


class CancelToken:
    def __init__(self):
        self._ev = threading.Event()

    def cancel(self) -> None:
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()


class Dispatcher:
    """Bounded executor: max_workers running + max_queue waiting, else shed."""

    def __init__(self, max_workers: int = 8, max_queue: int = 64):
        self._pool = cf.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="inv65-dispatch")
        self._slots = threading.BoundedSemaphore(max_workers + max_queue)
        self.shed = 0

    def run(self, fn, *, deadline: Deadline, cancel: CancelToken | None = None):
        if cancel and cancel.cancelled:
            raise ProviderFault("PK_PROVIDER_CANCELLED", "cancelled before dispatch")
        if deadline.expired():
            raise ProviderFault("PK_PROVIDER_DEADLINE_EXCEEDED", "deadline elapsed before dispatch")
        if not self._slots.acquire(blocking=False):
            self.shed += 1
            raise ProviderFault("PK_PROVIDER_OVERLOADED", "dispatch queue full", retry_after_ms=50)
        fut = self._pool.submit(fn)
        fut.add_done_callback(lambda _f: self._slots.release())
        end = time.monotonic() + deadline.remaining()
        while True:
            left = end - time.monotonic()
            if left <= 0:
                fut.cancel()
                raise ProviderFault("PK_PROVIDER_DEADLINE_EXCEEDED", "call deadline exceeded")
            try:
                return fut.result(timeout=min(left, 0.01))
            except cf.TimeoutError:
                if cancel and cancel.cancelled:
                    fut.cancel()
                    raise ProviderFault("PK_PROVIDER_CANCELLED", "cancelled by caller") from None

    def close(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


def call_with_retry(attempt_fn, *, op: str, deadline: Deadline, idempotency_key: str | None = None,
                    max_attempts: int = 3, base_ms: int = 10, cap_ms: int = 200, rng=random.random, sleep=time.sleep):
    retry_allowed = op in IDEMPOTENT_OPS or bool(idempotency_key)
    attempt = 0
    while True:
        attempt += 1
        try:
            return attempt_fn(attempt)
        except ProviderFault as e:
            spec = CATALOG[e.code]
            if not (spec.retryable and retry_allowed) or attempt >= max_attempts:
                raise
            backoff = rng() * min(cap_ms, base_ms * 2 ** (attempt - 1)) / 1000.0
            if e.retry_after_ms:
                backoff = max(backoff, e.retry_after_ms / 1000.0)
            if backoff >= deadline.remaining():
                raise
            sleep(backoff)
