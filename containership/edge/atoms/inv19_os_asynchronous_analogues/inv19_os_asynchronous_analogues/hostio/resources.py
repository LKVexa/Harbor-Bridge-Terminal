"""MC-21 - Resource accounting, quotas and fairness.

Reserve-before-allocate with rollback, exactly-once release, no negative
counts, no overflow, soft-warning and hard-refusal thresholds at the global,
per-tenant, per-workload and per-backend scopes, plus an optional
administrative reserve that ordinary tenants cannot consume.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager
from dataclasses import dataclass, field

RESOURCES = (
    "armed_descriptors", "native_handles", "inflight_ops", "pending_completions",
    "sq_entries", "cq_entries", "registered_buffers", "io_buffer_bytes",
    "metadata_bytes", "worker_threads", "wakeup_objects", "retry_backlog",
    "audit_backlog", "telemetry_backlog", "stream_credits",
)
MAX_COUNTER = 2**62


class QuotaExceeded(RuntimeError):
    def __init__(self, resource: str, scope: str, used: int, limit: int) -> None:
        super().__init__(f"{resource} quota exceeded at {scope}: {used}/{limit}")
        self.resource, self.scope, self.used, self.limit = resource, scope, used, limit
        self.reason = f"QUOTA_{scope.split(':')[0].upper()}"


class AccountingError(RuntimeError):
    pass


@dataclass
class Limits:
    global_limit: int
    per_tenant: int
    per_workload: int
    per_backend: int | None = None
    soft_ratio: float = 0.8
    admin_reserve: int = 0

    def __post_init__(self) -> None:
        for n in ("global_limit", "per_tenant", "per_workload"):
            v = getattr(self, n)
            if isinstance(v, bool) or not isinstance(v, int) or v <= 0 or v > MAX_COUNTER:
                raise ValueError(f"{n} must be a positive bounded int")
        if not (0 < self.soft_ratio <= 1):
            raise ValueError("soft_ratio must be in (0, 1]")
        if not (0 <= self.admin_reserve < self.global_limit):
            raise ValueError("admin_reserve must be < global_limit")


@dataclass
class Reservation:
    resource: str
    tenant: str
    workload: str
    backend: str
    amount: int
    released: bool = False
    rid: int = 0


@dataclass
class Accountant:
    limits: dict[str, Limits]
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _used: dict[tuple, int] = field(default_factory=dict, init=False)
    _live: dict[int, Reservation] = field(default_factory=dict, init=False)
    _next: int = field(default=1, init=False)
    warnings: list[tuple[str, str]] = field(default_factory=list, init=False)
    refusals: int = field(default=0, init=False)

    def _get(self, key: tuple) -> int:
        return self._used.get(key, 0)

    def reserve(self, resource: str, amount: int, *, tenant: str, workload: str,
                backend: str = "*", admin: bool = False) -> Reservation:
        if resource not in self.limits:
            raise AccountingError(f"resource {resource!r} has no configured limit")
        if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0 or amount > MAX_COUNTER:
            raise AccountingError("amount must be a positive bounded int")
        lim = self.limits[resource]
        keys = [
            (("global", resource), lim.global_limit - (0 if admin else lim.admin_reserve), "global"),
            (("tenant", resource, tenant), lim.per_tenant, f"tenant:{tenant}"),
            (("workload", resource, tenant, workload), lim.per_workload, f"workload:{workload}"),
        ]
        if lim.per_backend is not None:
            keys.append((("backend", resource, backend), lim.per_backend, f"backend:{backend}"))
        with self._lock:
            for key, limit, scope in keys:
                used = self._get(key)
                if used + amount > limit:
                    self.refusals += 1
                    raise QuotaExceeded(resource, scope, used + amount, limit)
            for key, limit, scope in keys:
                new = self._get(key) + amount
                self._used[key] = new
                if new >= limit * lim.soft_ratio:
                    self.warnings.append((resource, scope))
                    del self.warnings[:-256]
            r = Reservation(resource, tenant, workload, backend, amount, rid=self._next)
            self._next += 1
            self._live[r.rid] = r
            return r

    def release(self, r: Reservation) -> None:
        lim = self.limits[r.resource]
        with self._lock:
            if r.released or r.rid not in self._live:
                raise AccountingError(f"double release of reservation {r.rid}")
            keys = [("global", r.resource), ("tenant", r.resource, r.tenant),
                    ("workload", r.resource, r.tenant, r.workload)]
            if lim.per_backend is not None:
                keys.append(("backend", r.resource, r.backend))
            for key in keys:
                new = self._get(key) - r.amount
                if new < 0:
                    raise AccountingError(f"negative accounting on {key}")
                self._used[key] = new
            r.released = True
            del self._live[r.rid]

    @contextmanager
    def reserved(self, resource: str, amount: int, **kw):
        """Reserve, yield, and roll back if the guarded allocation raises."""
        r = self.reserve(resource, amount, **kw)
        try:
            yield r
        except BaseException:
            self.release(r)
            raise

    def used(self, resource: str, scope: str = "global", *parts: str) -> int:
        with self._lock:
            return self._get((scope, resource, *parts))

    def leaked(self) -> list[Reservation]:
        with self._lock:
            return list(self._live.values())

    def at_baseline(self) -> bool:
        with self._lock:
            return not self._live and all(v == 0 for v in self._used.values())

    def utilisation(self) -> dict[str, float]:
        with self._lock:
            return {r: self._get(("global", r)) / l.global_limit for r, l in self.limits.items()}


def default_limits(scale: int = 1024) -> dict[str, Limits]:
    return {r: Limits(scale, max(1, scale // 4), max(1, scale // 16), soft_ratio=0.8)
            for r in RESOURCES}
