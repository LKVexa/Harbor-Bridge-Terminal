"""Per-tenant quotas and weighted fair admission (INV-37-C017, C028, C064, C067).

Hard ceilings (global active transfers, global bytes in flight, pending queue
depth) are safety limits and cannot be exceeded.  Per-tenant limits are soft
operational quotas set by configuration.  Waiting transfers are admitted by
weighted fair selection: among tenants with waiters and headroom, pick the one
with the lowest ``active / weight``; ties break by arrival order.  A tenant with
headroom therefore cannot be starved by a busier tenant, and no tenant can hold
more than its quota of slots.

Accounting is keyed by the *authenticated* tenant passed in by the service
layer; callers cannot choose a tenant label.
"""
from __future__ import annotations

import itertools
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import CodedError


@dataclass
class TenantQuota:
    weight: int = 1
    max_active_transfers: int = 2
    max_bytes_in_flight: int = 2 << 30


@dataclass
class _Usage:
    active: int = 0
    bytes: int = 0
    admitted: int = 0
    rejected: int = 0
    waited_s: float = 0.0


@dataclass
class Grant:
    tenant: str
    nbytes: int
    released: bool = False


class FairAdmission:
    def __init__(self, *, max_active: int, max_bytes: int, max_pending: int,
                 default: TenantQuota | None = None, tenants: Mapping[str, TenantQuota] | None = None) -> None:
        if min(max_active, max_bytes, max_pending) < 0 or max_active == 0:
            raise CodedError("invalid_config", "admission limits must be positive")
        self.max_active = max_active
        self.max_bytes = max_bytes
        self.max_pending = max_pending
        self.default = default or TenantQuota()
        self.tenants = dict(tenants or {})
        self._cv = threading.Condition()
        self._usage: dict[str, _Usage] = {}
        self._waiting: list[tuple[int, str, int]] = []  # (seq, tenant, nbytes)
        self._seq = itertools.count()
        self._active = 0
        self._bytes = 0
        self.frozen = False
        self.throttle_reasons: dict[str, int] = {}

    def quota(self, tenant: str) -> TenantQuota:
        return self.tenants.get(tenant, self.default)

    def _u(self, tenant: str) -> _Usage:
        return self._usage.setdefault(tenant, _Usage())

    def _fits(self, tenant: str, nbytes: int) -> str | None:
        q, u = self.quota(tenant), self._u(tenant)
        if self._active >= self.max_active:
            return "global_active"
        if self._bytes + nbytes > self.max_bytes:
            return "global_bytes"
        if u.active >= q.max_active_transfers:
            return "tenant_active"
        if u.bytes + nbytes > q.max_bytes_in_flight:
            return "tenant_bytes"
        return None

    def _next_eligible(self) -> tuple[int, str, int] | None:
        best = None
        for item in self._waiting:
            _, t, n = item
            if self._fits(t, n) is not None:
                continue
            key = (self._u(t).active / self.quota(t).weight, item[0])
            if best is None or key < best[0]:
                best = (key, item)
        return best[1] if best else None

    def acquire(self, tenant: str, nbytes: int, *, timeout: float = 0.0) -> Grant:
        if nbytes > self.quota(tenant).max_bytes_in_flight or nbytes > self.max_bytes:
            self._reject(tenant, "request_exceeds_quota")
            raise CodedError("quota_exceeded", "request larger than quota", tenant_limit=self.quota(tenant).max_bytes_in_flight)
        start = time.monotonic()
        with self._cv:
            if self.frozen:
                raise CodedError("admission_frozen", "admission is frozen by operator")
            if not self._waiting and self._fits(tenant, nbytes) is None:
                return self._grant(tenant, nbytes, start)
            if len(self._waiting) >= self.max_pending:
                self._reject(tenant, "pending_queue_full")
                raise CodedError("admission_rejected", "pending queue full", limit=self.max_pending)
            me = (next(self._seq), tenant, nbytes)
            self._waiting.append(me)
            deadline = start + timeout
            try:
                while True:
                    if self.frozen:
                        raise CodedError("admission_frozen", "admission is frozen by operator")
                    if self._next_eligible() == me:
                        break
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        reason = self._fits(tenant, nbytes) or "fairness_wait"
                        self._reject(tenant, reason)
                        code = "quota_exceeded" if reason.startswith("tenant") else "admission_rejected"
                        raise CodedError(code, "admission not granted before timeout", reason=reason)
                    self._cv.wait(remaining)
            finally:
                self._waiting.remove(me)
                self._cv.notify_all()
            return self._grant(tenant, nbytes, start)

    def _grant(self, tenant: str, nbytes: int, start: float) -> Grant:
        u = self._u(tenant)
        u.active += 1
        u.bytes += nbytes
        u.admitted += 1
        u.waited_s += time.monotonic() - start
        self._active += 1
        self._bytes += nbytes
        return Grant(tenant, nbytes)

    def release(self, g: Grant) -> None:
        with self._cv:
            if g.released:
                return
            g.released = True
            u = self._u(g.tenant)
            u.active -= 1
            u.bytes -= g.nbytes
            self._active -= 1
            self._bytes -= g.nbytes
            self._cv.notify_all()

    def freeze(self, on: bool = True) -> None:
        with self._cv:
            self.frozen = on
            self._cv.notify_all()

    def _reject(self, tenant: str, reason: str) -> None:
        self._u(tenant).rejected += 1
        self.throttle_reasons[reason] = self.throttle_reasons.get(reason, 0) + 1

    def metrics(self) -> dict[str, Any]:
        with self._cv:
            return {
                "active": self._active, "bytes_in_flight": self._bytes, "pending": len(self._waiting),
                "limits": {"max_active": self.max_active, "max_bytes": self.max_bytes, "max_pending": self.max_pending},
                "saturation": round(max(self._active / self.max_active, self._bytes / max(self.max_bytes, 1)), 4),
                "throttle_reasons": dict(self.throttle_reasons),
                "tenants": {t: vars(u).copy() for t, u in self._usage.items()},
                "frozen": self.frozen,
            }
