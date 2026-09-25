"""wasi:keyvalue fixture: buckets are per link config; secret must be present
if the link declares a secret_ref (proves the resolved value reaches the
backend without being stored in the link)."""
from __future__ import annotations

import threading

from ...errors.mapping import ProviderFault
from .base import FaultyMixin


class KeyValueBackend(FaultyMixin):
    operations = ("get", "set", "delete", "exists", "list")

    def __init__(self):
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()
        self.seen_secret_versions: list[int] = []

    def invoke(self, op, config, secret, payload):
        self._faults()
        if secret is not None:
            self.seen_secret_versions.append(secret.version)
            secret.reveal()  # would authenticate to the real store
        b = config["bucket"]
        with self._lock:
            bucket = self._data.setdefault(b, {})
            if op == "get":
                return {"bucket": b, "as": config["user"], "value": bucket.get(payload.get("key"))}
            if op == "set":
                bucket[str(payload["key"])] = payload.get("value")
                return {"bucket": b, "ok": True}
            if op == "delete":
                return {"bucket": b, "deleted": bucket.pop(payload.get("key"), None) is not None}
            if op == "exists":
                return {"bucket": b, "exists": payload.get("key") in bucket}
            if op == "list":
                return {"bucket": b, "keys": sorted(bucket)[:1000]}
        raise ProviderFault("PK_PROVIDER_INVALID_LINK", f"unsupported keyvalue op {op!r}")
