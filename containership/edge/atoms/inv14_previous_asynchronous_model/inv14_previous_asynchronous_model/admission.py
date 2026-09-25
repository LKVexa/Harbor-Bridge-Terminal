"""Admission / backpressure for legacy polls (component P1-06; C017, C025, C054, C067).

Policy (normative):
  ADM-1 MUST cap concurrently executing polls globally and per tenant.
  ADM-2 MUST shed load deterministically with ``PK_POLL_OVERLOADED`` (global) or
        ``PK_POLL_TENANT_QUOTA`` (tenant) before any waiter is registered.
  ADM-3 queue_depth = 0 (default) means no queueing: overload is refused at once so
        a blocked queue cannot itself become an unbounded wait.  queue_depth > 0
        admits up to N waiting callers, FIFO across tenants, bounded by the caller's
        own admission timeout (never longer than the poll's own deadline).
  ADM-4 MUST release a slot on every exit path (context manager).
  ADM-5 Fairness: a tenant can never hold more than its own quota, so one tenant
        cannot starve others of the global pool beyond global - tenant_quota.
"""
from __future__ import annotations

import collections
import threading
import time

try:
    from .errors import Inv14Error
except ImportError:
    from errors import Inv14Error


class AdmissionRefused(Inv14Error):
    default_code = "PK_POLL_OVERLOADED"


class AdmissionController:
    def __init__(self, *, max_concurrent: int, tenant_max: int, queue_depth: int = 0):
        for n, v in (("max_concurrent", max_concurrent), ("tenant_max", tenant_max), ("queue_depth", queue_depth)):
            if not isinstance(v, int) or isinstance(v, bool) or v < (0 if n == "queue_depth" else 1):
                raise AdmissionRefused(f"invalid {n}", code="PK_POLL_INVALID_LIMIT")
        if tenant_max > max_concurrent:
            raise AdmissionRefused("tenant quota exceeds global ceiling", code="PK_POLL_INVALID_LIMIT")
        self.max_concurrent, self.tenant_max, self.queue_depth = max_concurrent, tenant_max, queue_depth
        self._cv = threading.Condition()
        self._active = 0
        self._per_tenant: dict[str, int] = collections.Counter()
        self._queue: collections.deque = collections.deque()
        self.shed = {"global": 0, "tenant": 0, "queue_full": 0, "queue_timeout": 0}
        self.peak = 0

    def _can_run(self, tenant: str, ticket) -> bool:
        return (self._active < self.max_concurrent and self._per_tenant[tenant] < self.tenant_max
                and (not self._queue or self._queue[0] is ticket))

    def acquire(self, tenant: str, *, wait_seconds: float = 0.0) -> None:
        if not isinstance(tenant, str) or not tenant:
            raise AdmissionRefused("tenant required", code="PK_POLL_INVALID_PRINCIPAL")
        with self._cv:
            if self._per_tenant[tenant] >= self.tenant_max and self.queue_depth == 0:
                self.shed["tenant"] += 1
                raise AdmissionRefused("tenant concurrent-poll quota exhausted", code="PK_POLL_TENANT_QUOTA",
                                       details={"tenant_max": self.tenant_max})
            if self._can_run(tenant, None) and not self._queue:
                self._take(tenant)
                return
            if self.queue_depth == 0 or wait_seconds <= 0:
                self.shed["global" if self._active >= self.max_concurrent else "tenant"] += 1
                code = "PK_POLL_OVERLOADED" if self._active >= self.max_concurrent else "PK_POLL_TENANT_QUOTA"
                raise AdmissionRefused("legacy poll admission refused", code=code,
                                       details={"active": self._active, "max_concurrent": self.max_concurrent})
            if len(self._queue) >= self.queue_depth:
                self.shed["queue_full"] += 1
                raise AdmissionRefused("admission queue full", code="PK_POLL_OVERLOADED",
                                       details={"queue_depth": self.queue_depth})
            ticket = object()
            self._queue.append(ticket)
            deadline = time.monotonic() + wait_seconds
            try:
                while not self._can_run(tenant, ticket):
                    rem = deadline - time.monotonic()
                    if rem <= 0:
                        self.shed["queue_timeout"] += 1
                        raise AdmissionRefused("admission wait expired", code="PK_POLL_OVERLOADED")
                    self._cv.wait(rem)
                self._take(tenant)
            finally:
                try:
                    self._queue.remove(ticket)
                except ValueError:
                    pass
                self._cv.notify_all()

    def _take(self, tenant: str) -> None:
        self._active += 1
        self._per_tenant[tenant] += 1
        self.peak = max(self.peak, self._active)

    def release(self, tenant: str) -> None:
        with self._cv:
            if self._per_tenant[tenant] <= 0:
                raise AdmissionRefused("release without acquire", code="PK_POLL_ADMISSION_STATE")
            self._active -= 1
            self._per_tenant[tenant] -= 1
            if not self._per_tenant[tenant]:
                del self._per_tenant[tenant]
            self._cv.notify_all()

    def snapshot(self) -> dict:
        with self._cv:
            return {"active": self._active, "queued": len(self._queue), "tenants_active": len(self._per_tenant),
                    "peak": self.peak, "shed": dict(self.shed), "max_concurrent": self.max_concurrent,
                    "tenant_max": self.tenant_max, "queue_depth": self.queue_depth}

    class _Slot:
        def __init__(self, ctl, tenant):
            self.ctl, self.tenant = ctl, tenant

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            self.ctl.release(self.tenant)
            return False

    def slot(self, tenant: str, *, wait_seconds: float = 0.0):
        self.acquire(tenant, wait_seconds=wait_seconds)
        return self._Slot(self, tenant)
