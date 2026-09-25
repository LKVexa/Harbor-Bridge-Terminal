"""Idempotency keys (M14): same key + same request fingerprint => cached result;
same key + different request => PK_PROVIDER_IDEMPOTENCY_CONFLICT.  Keys are
scoped to the caller identity and link, bounded in count and TTL."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict

from ..errors.mapping import ProviderFault


class IdempotencyCache:
    def __init__(self, capacity: int = 10_000, ttl_s: float = 600.0):
        self._d: OrderedDict = OrderedDict()
        self._cap, self._ttl = capacity, ttl_s
        self._lock = threading.Lock()

    @staticmethod
    def fingerprint(req: dict) -> str:
        return hashlib.sha256(json.dumps(req, sort_keys=True, default=str).encode()).hexdigest()

    def lookup(self, scope: tuple, key: str, req: dict):
        fp = self.fingerprint(req)
        now = time.monotonic()
        with self._lock:
            hit = self._d.get((scope, key))
            if hit is None or hit[2] < now:
                self._d.pop((scope, key), None)
                return None
            if hit[0] != fp:
                raise ProviderFault("PK_PROVIDER_IDEMPOTENCY_CONFLICT", "idempotency key reused with a different request")
            return hit[1]

    def store(self, scope: tuple, key: str, req: dict, result) -> None:
        with self._lock:
            self._d[(scope, key)] = (self.fingerprint(req), result, time.monotonic() + self._ttl)
            self._d.move_to_end((scope, key))
            while len(self._d) > self._cap:
                self._d.popitem(last=False)
