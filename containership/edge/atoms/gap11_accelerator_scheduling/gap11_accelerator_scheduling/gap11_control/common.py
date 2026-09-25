"""Shared primitives for the GAP-11 v4.3.0 control plane (stdlib only).

* Clocks are injected. Correctness never reads the wall clock directly: TTLs use a
  monotonic source, wall time is recorded only as provenance (UTC).
* Every refusal is a ``ControlError`` with a stable ``code`` from ``REASON_CODES``.
* ``Telemetry`` is an in-process structured event sink with a bounded buffer and a
  fixed label cardinality budget.
"""
from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import json
import threading
import time
from typing import Any, Callable

REASON_CODES = {
    # correctness / ownership
    "STALE_REVISION": "compare-and-swap precondition failed",
    "STALE_FENCE": "fencing token older than the resource's current token",
    "NOT_LEADER": "caller does not hold current controller authority",
    "LEASE_EXPIRED": "lease TTL elapsed",
    "LEASE_NOT_FOUND": "no such lease",
    "ILLEGAL_TRANSITION": "state machine forbids this transition",
    "AMBIGUOUS_EVIDENCE": "observed state is ambiguous; no destructive action taken",
    "IDEMPOTENCY_CONFLICT": "request id reused with a different payload",
    "DUPLICATE_REQUEST": "request replayed; original result returned",
    # capacity / policy
    "CAPACITY_EXHAUSTED": "no capacity satisfies the request",
    "QUOTA_EXCEEDED": "tenant quota exceeded",
    "POLICY_DENIED": "authorization policy denied the request",
    "CONSTRAINT_UNSATISFIED": "a hard constraint could not be met",
    "THERMAL_UNAVAILABLE": "power/thermal budget excludes the device",
    # security
    "UNAUTHENTICATED": "credential missing, malformed, expired or unverifiable",
    "REPLAY_DETECTED": "nonce already seen inside the freshness window",
    "ATTESTATION_INVALID": "device attestation evidence does not verify",
    "DEPENDENCY_UNAVAILABLE": "a security-critical dependency is unavailable; failing closed",
    # hardware
    "HARDWARE_FAULT": "device reported a fault",
    "SCRUB_FAILED": "scrub/reset did not verify; device quarantined",
    "SCRUB_TIMEOUT": "scrub/reset exceeded its deadline; device quarantined",
    "DEVICE_QUARANTINED": "device quarantined",
    "DEVICE_MISSING": "device disappeared from inventory",
    # transport
    "SCHEMA_INVALID": "message failed schema validation",
    "MESSAGE_TOO_LARGE": "message exceeds size/depth limits",
    "DEADLINE_EXCEEDED": "request cannot complete within its deadline",
    "OVERLOADED": "admission queue full; retry later",
    "MAINTENANCE_MODE": "mutations are frozen by operator",
    "CONFIG_INVALID": "configuration rejected",
    "STORE_CORRUPT": "durable store failed integrity verification",
    "STORE_UNAVAILABLE": "durable store unavailable",
}


class ControlError(RuntimeError):
    def __init__(self, code: str, message: str = "", **details: Any) -> None:
        if code not in REASON_CODES:
            raise ValueError(f"unregistered reason code {code!r}")
        super().__init__(message or REASON_CODES[code])
        self.code = code
        self.details = details

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), "details": dict(self.details)}


class ManualClock:
    """Deterministic clock for tests: monotonic and wall time advance together."""

    def __init__(self, start: float = 1_000.0, wall: float = 1_790_000_000.0) -> None:
        self._t = start
        self._wall = wall
        self._lock = threading.Lock()

    def monotonic(self) -> float:
        with self._lock:
            return self._t

    def wall(self) -> float:
        with self._lock:
            return self._wall

    def advance(self, seconds: float) -> None:
        if seconds < 0:
            raise ValueError("monotonic clocks never go backwards")
        with self._lock:
            self._t += seconds
            self._wall += seconds

    def skew_wall(self, seconds: float) -> None:
        """Move only wall time (either direction) — correctness must not care."""
        with self._lock:
            self._wall += seconds


class SystemClock:
    def monotonic(self) -> float:
        return time.monotonic()

    def wall(self) -> float:
        return time.time()


def utc_iso(ts: float) -> str:
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


class Telemetry:
    """Bounded structured-event sink. Labels outside the budget are refused."""

    ALLOWED_LABELS = frozenset({
        "component", "event", "code", "outcome", "device", "lease_id", "tenant_hash",
        "request_id", "operation_id", "trace_id", "span_id", "controller_epoch",
        "severity", "kind", "partition", "detail",
    })

    def __init__(self, clock: Any | None = None, capacity: int = 10_000) -> None:
        self.clock = clock or SystemClock()
        self.events: collections.deque[dict[str, Any]] = collections.deque(maxlen=capacity)
        self.dropped = 0
        self.counters: collections.Counter[tuple[str, str, str]] = collections.Counter()
        self._lock = threading.Lock()
        self.subscribers: list[Callable[[dict[str, Any]], None]] = []

    def emit(self, component: str, event: str, *, code: str = "OK", severity: str = "INFO", **labels: Any) -> dict[str, Any]:
        bad = set(labels) - self.ALLOWED_LABELS
        if bad:
            raise ValueError(f"telemetry labels outside cardinality budget: {sorted(bad)}")
        if code != "OK" and code not in REASON_CODES:
            raise ValueError(f"unregistered reason code {code!r}")
        rec = {"ts": utc_iso(self.clock.wall()), "component": component, "event": event,
               "code": code, "severity": severity, **labels}
        with self._lock:
            if len(self.events) == self.events.maxlen:
                self.dropped += 1
            self.events.append(rec)
            self.counters[(component, event, code)] += 1
        for sub in list(self.subscribers):
            try:
                sub(rec)
            except Exception:  # a broken subscriber must never break the control path
                with self._lock:
                    self.dropped += 1
        return rec

    def find(self, **match: Any) -> list[dict[str, Any]]:
        with self._lock:
            return [e for e in self.events if all(e.get(k) == v for k, v in match.items())]


def tenant_hash(tenant: str) -> str:
    """Pseudonymous tenant label for telemetry (never the raw tenant id)."""
    return hashlib.sha256(("gap11-tenant:" + tenant).encode()).hexdigest()[:16]
