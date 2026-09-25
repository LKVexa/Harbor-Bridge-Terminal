"""Bounded distributed-interaction semantics (MC-09; C025, C027, C053).

Everything here takes an injectable clock so tests are deterministic.

* :class:`Deadline` — absolute end-to-end deadline. Propagated as an absolute
  epoch-ms value, never re-derived per hop, so an exhausted budget stays exhausted.
* :class:`CancelToken` — cooperative cancellation checked at stage boundaries.
* :class:`RetryPolicy` — capped exponential backoff with full jitter, a per-call
  attempt/elapsed bound and a shared token-bucket retry budget (prevents storms).
* :class:`IdempotencyStore` — tenant-scoped keys, bounded capacity, TTL; a
  duplicate returns the first response, a key reused with a different request
  digest is ``idempotency.conflict``.
* :class:`AdmissionController` — bounded in-flight work with a per-tenant share;
  overflow is rejected with a retry hint, never buffered.
* :func:`negotiate` — highest mutually supported protocol version; refuses to
  choose a version lacking a feature the local side marks as required.
"""
from __future__ import annotations

import hashlib
import random
import re
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Iterable, Mapping

from .errors import Inv64Error

DEFAULT_DEADLINE_MS = 2_000
MAX_DEADLINE_MS = 30_000
IDEMPOTENCY_KEY_RE = re.compile(r"^[A-Za-z0-9_-]{16,128}$")

# Operation semantics matrix (INTERFACES.md §3 mirrors this table; tests pin it).
OPERATIONS: dict[str, dict] = {
    "validate":     {"state_changing": False, "auto_retry_safe": True,  "idempotency_key": "none",     "default_ms": 1_000, "max_ms": 5_000},
    "canonicalize": {"state_changing": False, "auto_retry_safe": True,  "idempotency_key": "none",     "default_ms": 1_000, "max_ms": 5_000},
    "submit":       {"state_changing": True,  "auto_retry_safe": False, "idempotency_key": "required", "default_ms": 2_000, "max_ms": 10_000},
    "activate":     {"state_changing": True,  "auto_retry_safe": False, "idempotency_key": "required", "default_ms": 10_000, "max_ms": 30_000},
    "rollback":     {"state_changing": True,  "auto_retry_safe": True,  "idempotency_key": "required", "default_ms": 10_000, "max_ms": 30_000},
    "status":       {"state_changing": False, "auto_retry_safe": True,  "idempotency_key": "none",     "default_ms": 500,   "max_ms": 2_000},
    "explain":      {"state_changing": False, "auto_retry_safe": True,  "idempotency_key": "none",     "default_ms": 1_000, "max_ms": 5_000},
}


class Deadline:
    def __init__(self, expires_at_ms: float, clock: Callable[[], float] = time.time):
        self.expires_at_ms = float(expires_at_ms)
        self._clock = clock

    @classmethod
    def for_operation(cls, op: str, requested_ms: float | None = None, *, clock=time.time,
                      inbound_expires_at_ms: float | None = None) -> "Deadline":
        spec = OPERATIONS[op]
        budget = spec["default_ms"] if requested_ms is None else requested_ms
        if not isinstance(budget, (int, float)) or budget <= 0 or budget > spec["max_ms"]:
            raise Inv64Error("deadline.invalid", details={"operation": op, "max_ms": spec["max_ms"]})
        mine = clock() * 1000 + budget
        if inbound_expires_at_ms is not None:  # never extend a propagated deadline
            mine = min(mine, float(inbound_expires_at_ms))
        return cls(mine, clock)

    def remaining_ms(self) -> float:
        return self.expires_at_ms - self._clock() * 1000

    def check(self) -> None:
        if self.remaining_ms() <= 0:
            raise Inv64Error("deadline.exceeded")

    def header(self) -> str:
        return str(int(self.expires_at_ms))


class CancelToken:
    def __init__(self):
        self._ev = threading.Event()
        self.reason: str | None = None

    def cancel(self, reason: str = "caller") -> None:
        self.reason = reason
        self._ev.set()

    @property
    def cancelled(self) -> bool:
        return self._ev.is_set()

    def check(self) -> None:
        if self._ev.is_set():
            raise Inv64Error("request.cancelled", details={"reason": self.reason})


@dataclass
class RetryPolicy:
    max_attempts: int = 4
    base_ms: float = 50.0
    cap_ms: float = 2_000.0
    max_elapsed_ms: float = 10_000.0
    budget_tokens: float = 10.0       # shared retry budget
    budget_refill_per_success: float = 0.1

    def __post_init__(self):
        self._tokens = self.budget_tokens
        self._lock = threading.Lock()

    def backoff_ms(self, attempt: int, rng: random.Random) -> float:
        return rng.uniform(0, min(self.cap_ms, self.base_ms * (2 ** attempt)))

    def _take(self) -> bool:
        with self._lock:
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False

    def _refill(self) -> None:
        with self._lock:
            self._tokens = min(self.budget_tokens, self._tokens + self.budget_refill_per_success)

    def run(self, fn: Callable[[], object], *, operation: str, deadline: Deadline | None = None,
            cancel: CancelToken | None = None, sleep: Callable[[float], None] = time.sleep,
            rng: random.Random | None = None, clock: Callable[[], float] = time.time, metrics=None):
        """Call ``fn`` with bounded retries. Non-retryable errors propagate at once."""
        if not OPERATIONS[operation]["auto_retry_safe"]:
            raise ValueError(f"{operation} is not auto-retry safe; the caller must retry with its idempotency key")
        rng = rng or random.Random()
        start = clock()
        attempt = 0
        while True:
            if cancel:
                cancel.check()
            if deadline:
                deadline.check()
            try:
                out = fn()
                self._refill()
                return out
            except Inv64Error as exc:
                attempt += 1
                if not exc.retryable or attempt >= self.max_attempts:
                    raise
                wait = self.backoff_ms(attempt, rng)
                elapsed = (clock() - start) * 1000
                if elapsed + wait > self.max_elapsed_ms or (deadline and deadline.remaining_ms() <= wait):
                    raise
                if not self._take():
                    if metrics:
                        metrics.inc("inv64_retry_budget_exhausted_total")
                    raise
                if metrics:
                    metrics.inc("inv64_retries_total", operation=operation)
                sleep(wait / 1000)


class IdempotencyStore:
    def __init__(self, *, ttl_s: float = 86_400, capacity: int = 100_000, clock=time.time):
        self._ttl = ttl_s
        self._cap = capacity
        self._clock = clock
        self._data: OrderedDict[tuple[str, str], tuple[float, str, object]] = OrderedDict()
        self._inflight: dict[tuple[str, str], threading.Event] = {}
        self._lock = threading.Lock()

    @staticmethod
    def request_digest(payload: bytes) -> str:
        return hashlib.sha256(payload).hexdigest()

    def _evict(self, now: float) -> None:
        while self._data:
            k, (t, _, _) = next(iter(self._data.items()))
            if now - t <= self._ttl:
                break
            self._data.popitem(last=False)

    @contextmanager
    def claim(self, tenant: str, key: str | None, request_digest: str):
        """Yield ``(replayed, response_holder)``; set ``holder['response']`` to record."""
        if key is None or not IDEMPOTENCY_KEY_RE.fullmatch(key):
            raise Inv64Error("idempotency.invalid")
        k = (tenant, key)  # tenant scope: equal keys in different tenants never collide
        replay, replayed = None, False
        while True:
            with self._lock:
                now = self._clock()
                self._evict(now)
                if k in self._data:
                    _, dig, resp = self._data[k]
                    if dig != request_digest:
                        raise Inv64Error("idempotency.conflict")
                    replay, replayed = resp, True
                    break
                ev = self._inflight.get(k)
                if ev is None:
                    if len(self._data) + len(self._inflight) >= self._cap:
                        raise Inv64Error("admission.overloaded", details={"reason": "idempotency store full"})
                    self._inflight[k] = threading.Event()
                    break
            if not ev.wait(timeout=5):  # a concurrent duplicate waits (bounded) for the first
                raise Inv64Error("admission.overloaded", details={"reason": "duplicate still in flight"})
        if replayed:
            yield True, {"response": replay}
            return
        holder: dict = {}
        try:
            yield False, holder
        finally:
            with self._lock:
                ev = self._inflight.pop(k)
                if "response" in holder:
                    self._data[k] = (self._clock(), request_digest, holder["response"])
                ev.set()


class AdmissionController:
    def __init__(self, *, max_inflight: int = 256, per_tenant_max: int = 32, metrics=None):
        self.max_inflight = max_inflight
        self.per_tenant_max = per_tenant_max
        self._inflight = 0
        self._by_tenant: dict[str, int] = {}
        self._lock = threading.Lock()
        self._metrics = metrics
        self.rejected = 0

    @contextmanager
    def admit(self, tenant: str):
        with self._lock:
            if self._inflight >= self.max_inflight:
                self.rejected += 1
                if self._metrics:
                    self._metrics.inc("inv64_admission_rejected_total", reason="global")
                raise Inv64Error("admission.overloaded", details={"retry_after_ms": 100})
            if self._by_tenant.get(tenant, 0) >= self.per_tenant_max:
                self.rejected += 1
                if self._metrics:
                    self._metrics.inc("inv64_admission_rejected_total", reason="tenant")
                raise Inv64Error("admission.tenant_quota", details={"retry_after_ms": 100})
            self._inflight += 1
            self._by_tenant[tenant] = self._by_tenant.get(tenant, 0) + 1
            if self._metrics:
                self._metrics.set("inv64_inflight", self._inflight)
        try:
            yield
        finally:
            with self._lock:
                self._inflight -= 1
                self._by_tenant[tenant] -= 1
                if not self._by_tenant[tenant]:
                    del self._by_tenant[tenant]
                if self._metrics:
                    self._metrics.set("inv64_inflight", self._inflight)

    @property
    def inflight(self) -> int:
        return self._inflight


# Protocol versions this build speaks, with the security features each carries.
PROTOCOLS: Mapping[str, frozenset] = {
    "PK_APP_SUBMIT/1": frozenset({"authn", "authz", "idempotency"}),
    "PK_APP_SUBMIT/2": frozenset({"authn", "authz", "idempotency", "channel-binding", "trace-context"}),
}


def negotiate(offered: Iterable[str], *, local: Mapping[str, frozenset] = PROTOCOLS,
              required_features: frozenset = frozenset({"authn", "authz"})) -> str:
    common = [v for v in offered if v in local]
    if not common:
        raise Inv64Error("version.unsupported", details={"supported": sorted(local)})
    best = max(common, key=lambda v: int(v.rsplit("/", 1)[1]))
    if not required_features <= local[best]:
        raise Inv64Error("version.downgrade_refused", details={"missing": sorted(required_features - local[best])})
    return best
