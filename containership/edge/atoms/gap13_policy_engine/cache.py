"""G13-MC-012 persistent last-known-good bundle cache.

Only *signed envelopes* are cached, never parsed rules: on restart every
cached envelope is re-verified against the current trust store and anti-replay
floor before it can become active again.  Age metadata is persisted so a
restart cannot reset bundle age.
"""
from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

from .storage import Corrupt, read_record, write_record

KIND = "PK_POLICY_CACHE/1"


class BundleCache:
    def __init__(self, path: str | Path | None, *, keep: int = 5) -> None:
        self.path = Path(path) if path else None
        self.keep = keep
        self._mem: dict[str, Any] = {"entries": []}

    def load(self) -> dict[str, Any]:
        if self.path is None:
            return self._mem
        body = read_record(self.path, kind=KIND)       # raises Corrupt on tamper/partial
        self._mem = body or {"entries": []}
        return self._mem

    def entries(self) -> list[dict[str, Any]]:
        return list(self._mem["entries"])

    def record_activation(self, envelope: bytes, meta: dict[str, Any], *, fault: Any = None) -> None:
        entry = {"envelope_b64": base64.b64encode(envelope).decode(), **meta}
        entries = [e for e in self._mem["entries"] if e["digest"] != meta["digest"]]
        entries.insert(0, entry)
        body = {"entries": entries[: self.keep]}
        if self.path is not None:
            write_record(self.path, body, kind=KIND, fault=fault)
        self._mem = body

    @staticmethod
    def envelope(entry: dict[str, Any]) -> bytes:
        return base64.b64decode(entry["envelope_b64"], validate=True)


__all__ = ["BundleCache", "Corrupt"]
