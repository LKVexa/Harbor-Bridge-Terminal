"""Interface/resource limits and rate controls (MC-020, MC-021-04, MC-015-05).

All limits are explicit, typed and enforced server-side.  Exceeding a size or
count limit raises ``LimitExceeded`` (non-retryable); exceeding a rate or
concurrency budget raises ``Overloaded``/``QuotaExceeded`` with a
``retry_after_s`` hint so well-behaved clients back off (MC-026-06).
"""
from __future__ import annotations

import json
import threading
import time
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any, Callable

from .errors import InvalidArgument, LimitExceeded, Overloaded, QuotaExceeded


@dataclass(frozen=True)
class Limits:
    max_key_bytes: int = 1536                 # MC-020-01
    max_value_bytes: int = 1_572_864          # 1.5 MiB (MC-020-02)
    max_request_bytes: int = 4_194_304        # 4 MiB
    max_response_bytes: int = 8_388_608
    max_txn_ops: int = 128                    # MC-020-03 (success + failure branches each)
    max_txn_compares: int = 128
    max_page_size: int = 1000                 # MC-008-06
    default_page_size: int = 500
    max_watches_per_identity: int = 64        # MC-020-04
    max_watches_total: int = 10_000
    max_watch_queue_events: int = 10_000      # MC-015-02
    max_history_events: int = 1_000_000       # MC-020-05 hard ceiling; compaction controller keeps below
    max_leases_per_identity: int = 1000
    max_lease_ttl_s: int = 3600
    min_lease_ttl_s: int = 2
    max_inflight_requests: int = 512          # MC-020-06
    rate_per_identity_rps: float = 1000.0
    burst_per_identity: int = 2000
    max_idempotency_entries: int = 100_000

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_json(value: Any) -> bytes:
    """Canonical byte form used for size checks and value comparison (MC-011-04)."""
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                          allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InvalidArgument(f"value is not canonical-JSON encodable: {type(value).__name__}",
                              field="value") from exc


def validate_key(key: object, limits: Limits) -> str:
    """Key policy: non-empty NFC UTF-8 str, no NUL/control chars, bounded length."""
    if not isinstance(key, str) or not key:
        raise InvalidArgument("key must be a non-empty string", field="key")
    if unicodedata.normalize("NFC", key) != key:
        raise InvalidArgument("key must be NFC-normalised", field="key")
    if any(ord(c) < 0x20 or ord(c) == 0x7F for c in key):
        raise InvalidArgument("key must not contain control characters", field="key")
    try:
        size = len(key.encode("utf-8"))
    except UnicodeEncodeError as exc:  # lone surrogates
        raise InvalidArgument("key must be valid UTF-8", field="key") from exc
    if size > limits.max_key_bytes:
        raise LimitExceeded("key too long", limit="max_key_bytes", limit_value=limits.max_key_bytes)
    return key


def validate_value(value: Any, limits: Limits) -> bytes:
    raw = canonical_json(value)
    if len(raw) > limits.max_value_bytes:
        raise LimitExceeded("value too large", limit="max_value_bytes", limit_value=limits.max_value_bytes)
    return raw


def validate_revision(rev: object, field: str = "revision") -> int:
    if isinstance(rev, bool) or not isinstance(rev, int) or rev < 0 or rev > 2**63 - 1:
        raise InvalidArgument(f"{field} must be an int in [0, 2^63-1]", field=field)
    return rev


class TokenBucket:
    """Thread-safe token bucket keyed by identity; bounded key set."""

    def __init__(self, rate: float, burst: int, clock: Callable[[], float] = time.monotonic,
                 max_keys: int = 100_000) -> None:
        self.rate, self.burst, self.clock, self.max_keys = rate, burst, clock, max_keys
        self._buckets: dict[str, tuple[float, float]] = {}
        self._lock = threading.Lock()

    def take(self, key: str, cost: float = 1.0) -> None:
        now = self.clock()
        with self._lock:
            tokens, last = self._buckets.get(key, (float(self.burst), now))
            tokens = min(float(self.burst), tokens + (now - last) * self.rate)
            if tokens < cost:
                self._buckets[key] = (tokens, now)
                wait = (cost - tokens) / self.rate if self.rate > 0 else 60.0
                raise QuotaExceeded("rate limit exceeded", retry_after_s=round(wait, 3), limit="rate_per_identity_rps")
            if key not in self._buckets and len(self._buckets) >= self.max_keys:
                # evict the fullest (idle) bucket to stay bounded
                victim = max(self._buckets, key=lambda k: self._buckets[k][0])
                del self._buckets[victim]
            self._buckets[key] = (tokens - cost, now)


class ConcurrencyGate:
    """Bounded in-flight request counter raising ``Overloaded`` when saturated."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._n = 0
        self._lock = threading.Lock()

    @property
    def inflight(self) -> int:
        return self._n

    def __enter__(self) -> "ConcurrencyGate":
        with self._lock:
            if self._n >= self.limit:
                raise Overloaded("too many in-flight requests", retry_after_s=0.05, limit="max_inflight_requests")
            self._n += 1
        return self

    def __exit__(self, *exc: object) -> None:
        with self._lock:
            self._n -= 1
