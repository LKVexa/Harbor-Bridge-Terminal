"""Residency authority with leases, epochs, provenance and reconciliation (PK_RESIDENCY/1).

GAP-010 (freshness/lease/watch), GAP-031 (unhealthy placement suppression),
GAP-032 (crash consistency / reconstruction).

Rules
-----
* Every placement carries ``epoch`` (owner generation), ``source`` (who asserted
  it) and ``lease_expires`` (monotonic). An expired lease is *not* resident: the
  call goes to the network path and ``stale_hits`` is incremented -- a stale
  entry must never be served locally.
* Duplicate owner arbitration: a placement for an existing name is accepted only
  from the same tenant, and only if ``epoch`` >= the current epoch. A lower epoch
  is a stale writer and is refused.
* After :meth:`restore`, entries are ``verified=False`` and are not served until
  :meth:`reconcile` confirms them against the authoritative source (INV-10).
* Watchers receive ``(event, name, placement)`` synchronously, outside the lock.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from threading import RLock
from typing import Any, Callable, Iterable, Mapping, Optional

from .errors import CrossTenantChain, ResidencyStale, ValidationFailed
from .context import check_id

RESIDENCY_SCHEMA = "PK_RESIDENCY/1"
DEFAULT_LEASE_S = 30.0
MAX_LEASE_S = 3600.0
MAX_PLACEMENTS = 10000
MAX_WATCHERS = 64


@dataclass(frozen=True)
class Placement:
    tenant: str
    handler: Callable[..., Any]
    revision: int
    placed_at: float
    epoch: int = 0
    source: str = "local"
    lease_expires: float = float("inf")
    verified: bool = True
    healthy: bool = True
    abi: str = "legacy"   # "legacy": handler(chainer, req, path, tenant, trace) ; "hop": handler(hop, req)

    @property
    def fresh(self) -> bool:
        return time.monotonic() < self.lease_expires

    @property
    def servable(self) -> bool:
        return self.fresh and self.verified and self.healthy


@dataclass
class Residency:
    host: str
    default_lease_s: Optional[float] = None  # None = no expiry (compat); production config sets one
    max_placements: int = MAX_PLACEMENTS
    _table: dict = field(default_factory=dict, init=False, repr=False)
    _revision: int = field(default=0, init=False, repr=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)
    _watchers: list = field(default_factory=list, init=False, repr=False)
    stale_hits: int = field(default=0, init=False)
    suppressed_hits: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.host, str) or not self.host.strip():
            raise ValueError("host must be a non-empty string")
        if self.default_lease_s is not None and not 0 < self.default_lease_s <= MAX_LEASE_S:
            raise ValueError("default_lease_s out of range")

    # -- read side -------------------------------------------------------
    @property
    def revision(self) -> int:
        with self._lock:
            return self._revision

    @property
    def table(self) -> Mapping[str, tuple]:
        with self._lock:
            return {n: (p.tenant, p.handler) for n, p in self._table.items()}

    def resolve(self, name: str) -> Optional[Placement]:
        """Servable placement or None (stale/unverified/unhealthy never served)."""
        with self._lock:
            p = self._table.get(name)
            if p is None:
                return None
            if not p.fresh or not p.verified:
                self.stale_hits += 1
                return None
            if not p.healthy:
                self.suppressed_hits += 1
                return None
            return p

    def inspect(self, name: str) -> Optional[Placement]:
        with self._lock:
            return self._table.get(name)

    def is_local(self, name: str) -> bool:
        return self.resolve(name) is not None

    def __len__(self) -> int:
        with self._lock:
            return len(self._table)

    # -- write side ------------------------------------------------------
    def watch(self, fn: Callable[[str, str, Optional[Placement]], None]) -> None:
        if not callable(fn):
            raise TypeError("watcher must be callable")
        with self._lock:
            if len(self._watchers) >= MAX_WATCHERS:
                raise ValidationFailed("too many watchers", limit=MAX_WATCHERS)
            self._watchers.append(fn)

    def _emit(self, event: str, name: str, p: Optional[Placement]) -> None:
        for fn in list(self._watchers):
            try:
                fn(event, name, p)
            except Exception:  # a broken watcher must not corrupt authority
                pass

    def place(self, name: str, tenant: str, handler: Callable[..., Any], *,
              epoch: int = 0, source: str = "local", lease_s: Optional[float] = None,
              abi: str = "legacy") -> int:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("placement name must be a non-empty string")
        if not isinstance(tenant, str) or not tenant.strip():
            raise ValueError("placement tenant must be a non-empty string")
        if not callable(handler):
            raise ValueError("placement handler must be callable")
        if not isinstance(epoch, int) or isinstance(epoch, bool) or epoch < 0:
            raise ValueError("epoch must be a non-negative int")
        if abi not in ("legacy", "hop"):
            raise ValueError("abi must be 'legacy' or 'hop'")
        name, tenant = name.strip(), tenant.strip()
        check_id(name, "callee"); check_id(tenant, "tenant"); check_id(source, "source")
        lease = lease_s if lease_s is not None else self.default_lease_s
        if lease is not None and not 0 < lease <= MAX_LEASE_S:
            raise ValueError("lease_s out of range")
        with self._lock:
            prior = self._table.get(name)
            if prior is not None and prior.tenant != tenant:
                raise CrossTenantChain(f"{name} is already placed for another tenant",
                                       callee=name, existing_tenant=prior.tenant, requested_tenant=tenant)
            if prior is not None and epoch < prior.epoch:
                raise ResidencyStale("stale placement epoch refused", callee=name, epoch=epoch)
            if prior is None and len(self._table) >= self.max_placements:
                raise ValidationFailed("residency table full", limit=self.max_placements)
            self._revision += 1
            expires = float("inf") if lease is None else time.monotonic() + lease
            p = Placement(tenant, handler, self._revision, time.time(), epoch, source, expires, abi=abi)
            self._table[name] = p
            rev = self._revision
        self._emit("placed", name, p)
        return rev

    def renew(self, name: str, *, epoch: int, lease_s: Optional[float] = None) -> bool:
        with self._lock:
            p = self._table.get(name)
            if p is None or epoch != p.epoch:
                return False
            lease = lease_s if lease_s is not None else (self.default_lease_s or DEFAULT_LEASE_S)
            self._table[name] = replace(p, lease_expires=time.monotonic() + lease)
            return True

    def set_health(self, name: str, healthy: bool) -> bool:
        with self._lock:
            p = self._table.get(name)
            if p is None:
                return False
            self._revision += 1
            self._table[name] = replace(p, healthy=bool(healthy), revision=self._revision)
            p2 = self._table[name]
        self._emit("health", name, p2)
        return True

    def unplace(self, name: str, *, tenant: Optional[str] = None) -> bool:
        with self._lock:
            prior = self._table.get(name)
            if prior is None:
                return False
            if tenant is not None and prior.tenant != tenant:
                raise CrossTenantChain(f"{name} belongs to another tenant", callee=name,
                                       existing_tenant=prior.tenant, requested_tenant=tenant)
            del self._table[name]
            self._revision += 1
        self._emit("unplaced", name, None)
        return True

    def expire(self) -> list:
        """Drop expired leases; returns names removed."""
        with self._lock:
            gone = [n for n, p in self._table.items() if not p.fresh]
            for n in gone:
                del self._table[n]
            if gone:
                self._revision += 1
        for n in gone:
            self._emit("expired", n, None)
        return gone

    # -- crash consistency ------------------------------------------------
    def snapshot(self) -> dict:
        """Serializable snapshot (handlers are not serialized; names are)."""
        with self._lock:
            return {"schema": RESIDENCY_SCHEMA, "host": self.host, "revision": self._revision,
                    "placements": [{"callee": n, "tenant": p.tenant, "epoch": p.epoch, "source": p.source}
                                   for n, p in sorted(self._table.items())]}

    def restore(self, snap: Mapping, handlers: Mapping[str, Callable[..., Any]]) -> int:
        """Rebuild after restart; entries stay unverified until reconcile()."""
        if snap.get("schema") != RESIDENCY_SCHEMA or snap.get("host") != self.host:
            raise ValidationFailed("snapshot schema/host mismatch", schema=str(snap.get("schema")))
        with self._lock:
            self._table.clear()
            for rec in snap.get("placements", [])[: self.max_placements]:
                h = handlers.get(rec["callee"])
                if h is None:
                    continue
                self._revision += 1
                lease = self.default_lease_s
                expires = float("inf") if lease is None else time.monotonic() + lease
                self._table[rec["callee"]] = Placement(rec["tenant"], h, self._revision, time.time(),
                                                       int(rec["epoch"]), rec["source"], expires,
                                                       verified=False, abi=getattr(h, "__inv21_abi__", "legacy"))
            self._revision = max(self._revision, int(snap.get("revision", 0)) + 1)
            return len(self._table)

    def reconcile(self, authoritative: Iterable[Mapping]) -> dict:
        """Confirm/evict entries against the authoritative placement feed."""
        truth = {r["callee"]: r for r in authoritative}
        confirmed, evicted = [], []
        with self._lock:
            for name, p in list(self._table.items()):
                t = truth.get(name)
                if t is None or t["tenant"] != p.tenant or int(t.get("epoch", 0)) != p.epoch:
                    del self._table[name]; evicted.append(name)
                else:
                    lease = self.default_lease_s
                    expires = float("inf") if lease is None else time.monotonic() + lease
                    self._table[name] = replace(p, verified=True, lease_expires=expires); confirmed.append(name)
            self._revision += 1
        for n in evicted:
            self._emit("evicted", n, None)
        return {"confirmed": sorted(confirmed), "evicted": sorted(evicted)}
