"""M09 - validation cache with safe invalidation.

Key = every verdict-affecting input: module digest, profile, bundle revision,
epoch, host-contract revision, engine, validator version, limits revision, and
the declared-capability digest.  Only *deterministic* outcomes are cached
(ACCEPT, or a reject whose code is in ``DETERMINISTIC_REJECTS``); deadlines,
internal errors and configuration problems are never cached.  ``bump_epoch``
invalidates everything atomically (revocation / config change).  Bounded LRU,
thread-safe.  Entries are MAC'd with a per-process random key, so a
corrupted or tampered entry is discarded and the module re-validated rather
than served (fault-injection finding F-01).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from collections import OrderedDict
from typing import Any, Hashable


class ValidationCache:
    def __init__(self, capacity: int = 10_000):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._d: "OrderedDict[Hashable, Any]" = OrderedDict()
        self._lock = threading.Lock()
        self._epoch = 0
        self.hits = self.misses = self.evictions = self.integrity_failures = 0
        self._mac_key = os.urandom(32)

    def _mac(self, key: tuple, value: Any) -> bytes:
        blob = json.dumps([repr(key), value], sort_keys=True, default=repr).encode()
        return hmac.new(self._mac_key, blob, hashlib.sha256).digest()

    @property
    def epoch(self) -> int:
        return self._epoch

    def key(self, **parts: Any) -> tuple:
        return (self._epoch,) + tuple(sorted(parts.items()))

    def get(self, key: tuple):
        with self._lock:
            if key[0] != self._epoch or key not in self._d:
                self.misses += 1
                return None
            value, mac = self._d[key]
            if not hmac.compare_digest(mac, self._mac(key, value)):
                del self._d[key]
                self.integrity_failures += 1
                self.misses += 1
                return None
            self._d.move_to_end(key)
            self.hits += 1
            return json.loads(json.dumps(value))  # defensive copy: callers cannot mutate the entry

    def put(self, key: tuple, value: Any) -> None:
        with self._lock:
            if key[0] != self._epoch:
                return  # computed under a superseded epoch: discard
            self._d[key] = (value, self._mac(key, value))
            self._d.move_to_end(key)
            while len(self._d) > self.capacity:
                self._d.popitem(last=False)
                self.evictions += 1

    def bump_epoch(self) -> int:
        with self._lock:
            self._epoch += 1
            self._d.clear()
            return self._epoch

    def __len__(self) -> int:
        return len(self._d)
