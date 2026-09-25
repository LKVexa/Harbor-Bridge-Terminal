"""M12/M22/M54 - quotas, rate/concurrency limits, payload and resource bounds.

Token buckets (burst + refill) and concurrency semaphores keyed by scope
(tenant, component, provider). Configuration bounds reject unsafe/unbounded
values. Enforcement happens before allocation/deserialization.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from .errors import FabricError

# hard ceilings an operator cannot exceed (M22 configuration bounds)
BOUNDS = {
    "max_payload_bytes": (1, 16 * 1024 * 1024),
    "max_artifact_bytes": (1, 256 * 1024 * 1024),
    "max_components_per_tenant": (1, 10_000),
    "max_links_per_component": (1, 256),
    "max_inflight_per_tenant": (1, 10_000),
    "max_inflight_global": (1, 100_000),
    "rate_per_tenant": (0.1, 100_000.0),
    "burst_per_tenant": (1, 100_000),
    "max_registry_entries": (1, 1_000_000),
    "max_hosts": (1, 10_000),
    "max_decisions_retained": (100, 1_000_000),
}
DEFAULTS = {
    "max_payload_bytes": 1024 * 1024, "max_artifact_bytes": 32 * 1024 * 1024,
    "max_components_per_tenant": 256, "max_links_per_component": 16,
    "max_inflight_per_tenant": 64, "max_inflight_global": 1024,
    "rate_per_tenant": 500.0, "burst_per_tenant": 100, "max_registry_entries": 4096,
    "max_hosts": 512, "max_decisions_retained": 10_000,
}


def validate_limits(values: dict) -> dict:
    out = dict(DEFAULTS)
    for k, v in values.items():
        if k not in BOUNDS:
            raise FabricError("INVALID_ARGUMENT", f"unknown limit {k!r}")
        lo, hi = BOUNDS[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (lo <= v <= hi):
            raise FabricError("INVALID_ARGUMENT", f"limit {k}={v!r} outside [{lo}, {hi}]")
        out[k] = v
    return out


@dataclass
class TokenBucket:
    rate: float
    burst: float
    clock: object = time.monotonic
    tokens: float = -1.0
    last: float = 0.0

    def __post_init__(self):
        self.tokens = self.burst if self.tokens < 0 else self.tokens
        self.last = self.clock()

    def take(self, n: float = 1.0) -> float:
        """Return 0 on success, else seconds until enough tokens."""
        now = self.clock()
        self.tokens = min(self.burst, self.tokens + (now - self.last) * self.rate)
        self.last = now
        if self.tokens >= n:
            self.tokens -= n
            return 0.0
        return (n - self.tokens) / self.rate


class Limiter:
    def __init__(self, limits: dict | None = None, *, clock=time.monotonic) -> None:
        self.limits = validate_limits(limits or {})
        self.clock = clock
        self._buckets: dict[str, TokenBucket] = {}
        self._inflight: dict[str, int] = {}
        self._global = 0
        self._lock = threading.Lock()
        self.rejections: dict[str, int] = {}

    def _reject(self, code: str, msg: str, retry_after: float | None = None):
        self.rejections[code] = self.rejections.get(code, 0) + 1
        raise FabricError(code, msg, retry_after_s=retry_after)

    def check_payload(self, size: int, *, kind: str = "payload") -> None:
        key = "max_artifact_bytes" if kind == "artifact" else "max_payload_bytes"
        if size > self.limits[key]:
            self._reject("PAYLOAD_TOO_LARGE", f"{kind} {size} bytes > {self.limits[key]}")

    def check_count(self, name: str, current: int) -> None:
        if current >= self.limits[name]:
            self._reject("QUOTA_EXCEEDED", f"{name} reached ({self.limits[name]})", 1.0)

    def rate(self, tenant: str) -> None:
        with self._lock:
            b = self._buckets.get(tenant)
            if b is None:
                b = self._buckets[tenant] = TokenBucket(self.limits["rate_per_tenant"],
                                                        self.limits["burst_per_tenant"], self.clock)
            wait = b.take()
        if wait:
            self._reject("RATE_LIMITED", f"tenant rate exceeded", round(wait, 3))

    def acquire(self, tenant: str) -> None:
        with self._lock:
            if self._global >= self.limits["max_inflight_global"]:
                self.rejections["OVERLOADED"] = self.rejections.get("OVERLOADED", 0) + 1
                raise FabricError("OVERLOADED", "global in-flight limit", retry_after_s=0.05)
            if self._inflight.get(tenant, 0) >= self.limits["max_inflight_per_tenant"]:
                self.rejections["QUOTA_EXCEEDED"] = self.rejections.get("QUOTA_EXCEEDED", 0) + 1
                raise FabricError("QUOTA_EXCEEDED", "tenant in-flight limit", retry_after_s=0.05)
            self._inflight[tenant] = self._inflight.get(tenant, 0) + 1
            self._global += 1

    def release(self, tenant: str) -> None:
        with self._lock:
            self._inflight[tenant] = max(0, self._inflight.get(tenant, 0) - 1)
            self._global = max(0, self._global - 1)

    def usage(self) -> dict:
        with self._lock:
            return {"inflight_global": self._global, "inflight_tenants": len(self._inflight),
                    "rejections": dict(self.rejections)}
