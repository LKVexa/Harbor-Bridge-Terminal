"""Timeouts, cooperative cancellation, and bounded retry with jitter
(INV-37-C025, C053).  Only error codes whose registry entry says
``retryable`` are retried; integrity and security failures never are."""
from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, TypeVar

from .errors import BulkDataPlaneError, CodedError
from .outcomes import ERROR_CODES

T = TypeVar("T")


class CancelToken:
    def __init__(self, deadline: float | None = None) -> None:
        self._ev = threading.Event()
        self.reason = ""
        self.deadline = deadline  # monotonic seconds
        self._callbacks: list[Callable[[], None]] = []
        self._lock = threading.Lock()

    def cancel(self, reason: str = "cancelled") -> None:
        with self._lock:
            if self._ev.is_set():
                return
            self.reason = reason
            self._ev.set()
            cbs = list(self._callbacks)
        for cb in reversed(cbs):  # unwind in LIFO order
            try:
                cb()
            except Exception:  # noqa: BLE001 - unwinding must continue
                pass

    def on_cancel(self, cb: Callable[[], None]) -> None:
        with self._lock:
            if not self._ev.is_set():
                self._callbacks.append(cb)
                return
        cb()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def check(self) -> None:
        if self._ev.is_set():
            raise CodedError("cancelled", "operation cancelled", reason=self.reason)
        if self.deadline is not None and time.monotonic() > self.deadline:
            raise CodedError("timeout", "deadline exceeded")

    def sleep(self, seconds: float) -> None:
        if self.deadline is not None:
            seconds = min(seconds, max(0.0, self.deadline - time.monotonic()))
        self._ev.wait(seconds)
        self.check()


@dataclass
class RetryPolicy:
    base_delay: float = 0.1
    max_delay: float = 10.0
    max_attempts: int = 5
    budget_ratio: float = 0.1       # retries allowed as fraction of first attempts
    rng: random.Random = field(default_factory=random.Random)
    _first: int = 0
    _retries: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    stats: dict = field(default_factory=lambda: {"retries": 0, "budget_exhausted": 0, "gave_up": 0})

    def delay(self, attempt: int) -> float:
        """Full-jitter exponential backoff."""
        cap = min(self.max_delay, self.base_delay * (2 ** attempt))
        return self.rng.uniform(0, cap)

    def _budget_ok(self) -> bool:
        with self._lock:
            ok = self._retries < max(1, int(self._first * self.budget_ratio) + 1)
            if ok:
                self._retries += 1
            return ok

    def run(self, fn: Callable[[], T], *, cancel: CancelToken | None = None,
            sleep: Callable[[float], None] | None = None) -> T:
        with self._lock:
            self._first += 1
        attempt = 0
        while True:
            if cancel:
                cancel.check()
            try:
                return fn()
            except BulkDataPlaneError as exc:
                spec = ERROR_CODES.get(exc.code)
                limit = min(self.max_attempts, spec.max_attempts) if spec else 0
                if not (spec and spec.retryable) or attempt + 1 >= limit:
                    self.stats["gave_up"] += 1
                    raise
                if not self._budget_ok():
                    self.stats["budget_exhausted"] += 1
                    raise
                self.stats["retries"] += 1
                d = self.delay(attempt)
                if cancel:
                    cancel.sleep(d)
                else:
                    (sleep or time.sleep)(d)
                attempt += 1
