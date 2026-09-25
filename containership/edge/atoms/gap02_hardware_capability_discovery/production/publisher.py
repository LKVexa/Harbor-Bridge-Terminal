"""GAP02-MC-16 — Control-plane publisher transport.

Transport-agnostic reliable publisher: bounded offline buffer (drop-oldest with
a counted loss, never drop-newest), idempotency key = envelope generation,
exponential backoff with full jitter, cancellation, and delivery only counted
on a positive acknowledgement carrying the same idempotency key.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import random
import threading
from typing import Callable, Protocol

from .errors import Code, Gap02Error


class Transport(Protocol):
    def send(self, idempotency_key: str, payload: dict, timeout: float) -> dict: ...


@dataclass
class PublishStats:
    delivered: int = 0
    retries: int = 0
    dropped: int = 0
    failures: int = 0


class Publisher:
    def __init__(self, transport: Transport, *, buffer_size: int = 64, max_attempts: int = 6,
                 base_delay: float = 0.5, max_delay: float = 30.0, timeout: float = 5.0,
                 sleep: Callable[[float], None] | None = None, rng: random.Random | None = None):
        if buffer_size < 1:
            raise Gap02Error(Code.CONFIG_INVALID, "buffer_size")
        self.t = transport
        self.buf: deque[tuple[str, dict]] = deque()
        self.buffer_size, self.max_attempts = buffer_size, max_attempts
        self.base, self.cap, self.timeout = base_delay, max_delay, timeout
        self._cancel = threading.Event()
        self._sleep = sleep or (lambda s: self._cancel.wait(s))
        self.rng = rng or random.Random()
        self.stats = PublishStats()
        self._acked: set[str] = set()
        self._lock = threading.Lock()

    def enqueue(self, key: str, payload: dict) -> None:
        with self._lock:
            if key in self._acked or any(k == key for k, _ in self.buf):
                return  # idempotent
            if len(self.buf) >= self.buffer_size:  # backpressure: drop oldest, count it
                self.buf.popleft()
                self.stats.dropped += 1
            self.buf.append((key, payload))

    def cancel(self) -> None:
        self._cancel.set()

    def flush(self) -> int:
        """Deliver in order; stop at the first undeliverable item (keeps order)."""
        n = 0
        while self.buf and not self._cancel.is_set():
            key, payload = self.buf[0]
            if not self._deliver(key, payload):
                break
            with self._lock:
                self.buf.popleft()
                self._acked.add(key)
                if len(self._acked) > 4 * self.buffer_size:
                    self._acked = set(list(self._acked)[-2 * self.buffer_size:])
            n += 1
        return n

    def _deliver(self, key: str, payload: dict) -> bool:
        for attempt in range(self.max_attempts):
            if self._cancel.is_set():
                return False
            try:
                ack = self.t.send(key, payload, self.timeout)
                if isinstance(ack, dict) and ack.get("ack") is True and ack.get("key") == key:
                    self.stats.delivered += 1
                    return True
                if isinstance(ack, dict) and ack.get("permanent"):
                    self.stats.failures += 1
                    return False
            except Gap02Error as e:
                if not e.retryable:
                    self.stats.failures += 1
                    return False
            except (OSError, TimeoutError):
                pass
            self.stats.retries += 1
            self._sleep(self.rng.uniform(0, min(self.cap, self.base * 2 ** attempt)))
        self.stats.failures += 1
        return False
