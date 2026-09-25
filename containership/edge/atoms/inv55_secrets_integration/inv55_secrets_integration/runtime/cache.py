"""Lease cache and disconnected-operation policy (checklist #10, #66).

Policy (normative, see docs/requirements/REQUIREMENTS.md R-CACHE-*):
* A cached entry is served fresh until ``fresh_s``.
* When the provider is UNAVAILABLE, an entry may be served stale until
  ``max_stale_s`` ONLY if ``allow_stale`` is configured, the response is marked
  ``DEGRADED`` and audited; revoked/retired versions are never served.
* With ``allow_stale=False`` (default) an outage denies (offline-deny).
* Authorization is always re-evaluated before a cached value is served: the
  cache holds values, never decisions.
"""
from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass

from .provider import ProviderSecret


@dataclass
class Entry:
    secret: ProviderSecret
    fetched_at: float


class LeaseCache:
    def __init__(self, *, fresh_s: float, max_stale_s: float, allow_stale: bool, max_entries: int = 10_000):
        if max_stale_s < fresh_s:
            raise ValueError("max_stale_s must be >= fresh_s")
        self.fresh_s, self.max_stale_s, self.allow_stale = fresh_s, max_stale_s, allow_stale
        self.max_entries = max_entries
        self._d: "OrderedDict[str, Entry]" = OrderedDict()
        self._lock = threading.Lock()
        self.hits = self.misses = self.stale_served = 0

    def get_fresh(self, name, now):
        with self._lock:
            e = self._d.get(name)
            if e and now - e.fetched_at < self.fresh_s:
                self._d.move_to_end(name)
                self.hits += 1
                return e.secret
            self.misses += 1
            return None

    def get_stale(self, name, now):
        if not self.allow_stale:
            return None
        with self._lock:
            e = self._d.get(name)
            if e and now - e.fetched_at < self.max_stale_s:
                self.stale_served += 1
                return e.secret
            return None

    def put(self, secret: ProviderSecret, now):
        with self._lock:
            self._d[secret.name] = Entry(secret, now)
            self._d.move_to_end(secret.name)
            while len(self._d) > self.max_entries:
                self._d.popitem(last=False)

    def invalidate(self, name=None):
        with self._lock:
            if name is None:
                self._d.clear()
            else:
                self._d.pop(name, None)

    def __len__(self):
        return len(self._d)
