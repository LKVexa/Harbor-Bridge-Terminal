"""Controller lease and fencing service (component 2).

One controller at a time owns a rollout.  Ownership is a time-bounded lease;
every acquisition mints a strictly larger **fencing token** for that resource
(never reused, persisted across restarts).  Downstream writers — the state
store, command transport and node supervisor — reject any token lower than the
highest they have seen, so a paused/partitioned stale controller that wakes up
cannot mutate anything even if it still *believes* it holds the lease.

Clock rule: leases are evaluated on the service's monotonic clock; holders must
renew before ``expires_at - safety_margin`` and must stop issuing commands once
``renew`` fails.
"""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import Clock, SystemClock, canonical_json
from .errors import Conflict, StaleFence, ValidationFailed

LEASE_SCHEMA = "PK_LEASE/1"


@dataclass(frozen=True)
class Lease:
    resource: str
    holder: str
    token: int
    expires_at: float

    def to_dict(self) -> dict[str, Any]:
        return {"schema": LEASE_SCHEMA, "resource": self.resource, "holder": self.holder,
                "token": self.token, "expires_at": self.expires_at}


class LeaseService:
    def __init__(self, *, clock: Clock | None = None, persist_path: str | os.PathLike[str] | None = None,
                 max_ttl: float = 120.0) -> None:
        self.clock = clock or SystemClock()
        self.max_ttl = max_ttl
        self._lock = threading.Lock()
        self._path = Path(persist_path) if persist_path else None
        self._current: dict[str, Lease] = {}
        self._high: dict[str, int] = {}
        if self._path and self._path.exists():
            raw = json.loads(self._path.read_text())
            self._high = {k: int(v) for k, v in raw.get("high_water", {}).items()}
            # Leases do not survive a service restart: every holder must re-acquire,
            # which mints a higher token and fences any pre-restart holder.

    def _persist(self) -> None:
        if not self._path:
            return
        tmp = self._path.with_suffix(".tmp")
        data = canonical_json({"schema": "PK_LEASE_STATE/1", "high_water": self._high})
        fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
        try:
            os.write(fd, data)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(tmp, self._path)

    def acquire(self, resource: str, holder: str, ttl: float = 30.0) -> Lease:
        if not resource or not holder:
            raise ValidationFailed("resource and holder are required")
        if not (0 < ttl <= self.max_ttl):
            raise ValidationFailed(f"ttl must be in (0, {self.max_ttl}]")
        with self._lock:
            now = self.clock.monotonic()
            cur = self._current.get(resource)
            if cur is not None and cur.expires_at > now and cur.holder != holder:
                raise Conflict(f"{resource} is leased by {cur.holder} until {cur.expires_at:.3f}",
                               resource=resource)
            token = self._high.get(resource, 0) + 1
            self._high[resource] = token
            self._persist()  # token is durable before it is handed out
            lease = Lease(resource, holder, token, now + ttl)
            self._current[resource] = lease
            return lease

    def renew(self, lease: Lease, ttl: float = 30.0) -> Lease:
        with self._lock:
            now = self.clock.monotonic()
            cur = self._current.get(lease.resource)
            if cur is None or cur.token != lease.token or cur.expires_at <= now:
                raise StaleFence(f"lease {lease.token} on {lease.resource} is no longer current",
                                 resource=lease.resource)
            new = Lease(lease.resource, lease.holder, lease.token, now + min(ttl, self.max_ttl))
            self._current[lease.resource] = new
            return new

    def release(self, lease: Lease) -> None:
        with self._lock:
            cur = self._current.get(lease.resource)
            if cur is not None and cur.token == lease.token:
                del self._current[lease.resource]

    def check(self, resource: str, token: int) -> None:
        """Raise ``StaleFence`` unless ``token`` is the live lease for ``resource``."""
        with self._lock:
            now = self.clock.monotonic()
            cur = self._current.get(resource)
            if cur is None or cur.token != token or cur.expires_at <= now:
                raise StaleFence(f"fence {token} is not the live lease for {resource}", resource=resource)

    def high_water(self, resource: str) -> int:
        with self._lock:
            return self._high.get(resource, 0)
