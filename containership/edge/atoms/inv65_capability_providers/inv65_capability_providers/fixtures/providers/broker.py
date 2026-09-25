"""wasmcloud:messaging fixture: subjects are namespaced by the link's bucket
so two links can never read each other's messages."""
from __future__ import annotations

import collections
import threading

from ...errors.mapping import ProviderFault
from .base import FaultyMixin


class BrokerBackend(FaultyMixin):
    operations = ("publish", "pull")

    def __init__(self, max_depth: int = 10_000):
        self._q = collections.defaultdict(collections.deque)
        self._lock = threading.Lock()
        self.max_depth = max_depth

    def invoke(self, op, config, secret, payload):
        self._faults()
        subj = f"{config['bucket']}::{payload.get('subject', '')}"
        with self._lock:
            if op == "publish":
                if len(self._q[subj]) >= self.max_depth:
                    raise ProviderFault("PK_PROVIDER_OVERLOADED", "subject queue full", retry_after_ms=100)
                self._q[subj].append(payload.get("body"))
                return {"subject": payload.get("subject"), "depth": len(self._q[subj])}
            if op == "pull":
                return {"subject": payload.get("subject"), "body": self._q[subj].popleft() if self._q[subj] else None}
        raise ProviderFault("PK_PROVIDER_INVALID_LINK", "unsupported broker op")
