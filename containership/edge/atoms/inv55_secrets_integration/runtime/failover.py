"""Failover controller (checklist #55).

Reads go to the primary; on a RETRYABLE failure they fail over to the
secondary (a performance/DR replica) and the controller records the switch.
Writes are NEVER failed over: a replica accepting a rotation while the primary
is partitioned is exactly the split-brain the checklist (#58) forbids, so
``write``/``destroy_version``/``revoke_lease`` go to the primary only and fail
RETRYABLE when it is down.  Failback happens after ``failback_after_s`` of the
primary answering health probes.
"""
from __future__ import annotations

import threading
import time

from .errors import INV55Error, Outcome
from .provider import ProviderHealth, SecretProvider


class FailoverProvider(SecretProvider):
    name = "failover"

    def __init__(self, primary: SecretProvider, secondary: SecretProvider, *, failback_after_s=30.0, clock=time.monotonic):
        self.primary, self.secondary = primary, secondary
        self.failback_after_s, self.clock = failback_after_s, clock
        self.active = "primary"
        self.events: list[tuple[float, str]] = []
        self._healthy_since = None
        self._lock = threading.Lock()

    def _switch(self, to):
        if self.active != to:
            self.active = to
            self.events.append((self.clock(), to))

    def read(self, name, version=None, *, timeout_s):
        if self.active == "secondary":
            self._maybe_failback(timeout_s)
        if self.active == "primary":
            try:
                return self.primary.read(name, version, timeout_s=timeout_s)
            except INV55Error as e:
                if e.outcome is not Outcome.RETRYABLE:
                    raise
                with self._lock:
                    self._switch("secondary")
        return self.secondary.read(name, version, timeout_s=timeout_s)

    def _maybe_failback(self, timeout_s):
        h = self.primary.health(timeout_s=timeout_s)
        now = self.clock()
        with self._lock:
            if not h.healthy:
                self._healthy_since = None
                return
            if self._healthy_since is None:
                self._healthy_since = now
            if now - self._healthy_since >= self.failback_after_s:
                self._switch("primary")
                self._healthy_since = None

    def write(self, name, value, *, cas, timeout_s):
        return self.primary.write(name, value, cas=cas, timeout_s=timeout_s)

    def metadata(self, name, *, timeout_s):
        return self.primary.metadata(name, timeout_s=timeout_s)

    def destroy_version(self, name, version, *, timeout_s):
        return self.primary.destroy_version(name, version, timeout_s=timeout_s)

    def revoke_lease(self, provider_lease_id, *, timeout_s):
        return self.primary.revoke_lease(provider_lease_id, timeout_s=timeout_s)

    def health(self, *, timeout_s):
        p, s = self.primary.health(timeout_s=timeout_s), self.secondary.health(timeout_s=timeout_s)
        return ProviderHealth(p.healthy or s.healthy, p.sealed, f"active={self.active} primary={p.detail} secondary={s.detail}", p.version)
