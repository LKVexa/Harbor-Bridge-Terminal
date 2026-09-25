"""Component 25 - interface resource limits and enforcement.

``LIMITS`` (PK_DYN_LIMITS/1) are the defaults per controller endpoint:
max_payload_bytes 1 MiB (TERMINAL when exceeded - resending cannot help),
max_connections 1024, max_streams_per_connection 64, rate 100 req/s with a
burst of 200 (token bucket), max_concurrency 256, max_queue_depth 1000,
memory_budget_bytes 256 MiB.  Every other breach is RETRYABLE with a
``retry_after`` hint.  Every enforcement point is O(1) and never allocates in
proportion to the offending input (payload size is checked from its length
before parsing).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

from .errors_catalog import error


@dataclass(frozen=True)
class Limits:
    max_payload_bytes: int = 1 << 20
    max_connections: int = 1024
    max_streams_per_connection: int = 64
    rate_per_s: float = 100.0
    burst: int = 200
    max_concurrency: int = 256
    max_queue_depth: int = 1000
    memory_budget_bytes: int = 256 << 20

    def __post_init__(self) -> None:
        for k, v in asdict(self).items():
            if isinstance(v, bool) or not isinstance(v, (int, float)) or v <= 0:
                raise ValueError(f"{k} must be > 0")


LIMITS = {"version": "PK_DYN_LIMITS/1", **asdict(Limits())}


class TokenBucket:
    def __init__(self, rate: float, burst: int, clock) -> None:
        self.rate, self.burst, self.clock = rate, burst, clock
        self.tokens, self.t = float(burst), clock()

    def take(self, n: int = 1) -> float:
        """Return 0 if granted else seconds until n tokens are available."""
        now = self.clock()
        self.tokens = min(self.burst, self.tokens + (now - self.t) * self.rate)
        self.t = now
        if n > self.burst:
            return float("inf")
        if self.tokens >= n:
            self.tokens -= n
            return 0.0
        return (n - self.tokens) / self.rate


class Enforcer:
    def __init__(self, limits: Limits, *, clock) -> None:
        self.l = limits
        self.bucket = TokenBucket(limits.rate_per_s, limits.burst, clock)
        self.conns: dict[str, int] = {}
        self.inflight = 0
        self.queue = 0
        self.mem = 0
        self.rejections: dict[str, int] = {}

    def _reject(self, code: str, msg: str, **details):
        self.rejections[code] = self.rejections.get(code, 0) + 1
        raise error(code, msg, details=details)

    def check_payload(self, size: int) -> None:
        if size > self.l.max_payload_bytes:
            self._reject("INV08.LIMIT.PAYLOAD_TOO_LARGE", f"{size} > {self.l.max_payload_bytes}",
                         size=size, limit=self.l.max_payload_bytes)

    def open_connection(self, cid: str) -> None:
        if cid in self.conns:
            raise ValueError(f"duplicate connection {cid}")
        if len(self.conns) >= self.l.max_connections:
            self._reject("INV08.LIMIT.CONNECTIONS", "too many connections", retry_after=1.0)
        self.conns[cid] = 0

    def close_connection(self, cid: str) -> None:
        self.conns.pop(cid, None)

    def open_stream(self, cid: str) -> None:
        if cid not in self.conns:
            raise KeyError(cid)
        if self.conns[cid] >= self.l.max_streams_per_connection:
            self._reject("INV08.LIMIT.STREAMS", f"{cid} stream limit", retry_after=0.5)
        self.conns[cid] += 1

    def close_stream(self, cid: str) -> None:
        if self.conns.get(cid, 0) > 0:
            self.conns[cid] -= 1

    def begin_request(self, payload_size: int, mem_bytes: int = 0) -> None:
        """Admit one request; all checks precede any accounting (atomic)."""
        self.check_payload(payload_size)
        if self.inflight >= self.l.max_concurrency:
            self._reject("INV08.LIMIT.CONCURRENCY", "concurrency limit", retry_after=0.1)
        if self.mem + mem_bytes > self.l.memory_budget_bytes:
            self._reject("INV08.LIMIT.MEMORY", "memory budget", retry_after=1.0)
        wait = self.bucket.take()
        if wait:
            self._reject("INV08.LIMIT.RATE", "rate limited", retry_after=wait)
        self.inflight += 1
        self.mem += mem_bytes

    def end_request(self, mem_bytes: int = 0) -> None:
        self.inflight = max(0, self.inflight - 1)
        self.mem = max(0, self.mem - mem_bytes)

    def enqueue(self) -> None:
        if self.queue >= self.l.max_queue_depth:
            self._reject("INV08.LIMIT.QUEUE_DEPTH", "queue full", retry_after=1.0)
        self.queue += 1

    def dequeue(self) -> None:
        self.queue = max(0, self.queue - 1)
