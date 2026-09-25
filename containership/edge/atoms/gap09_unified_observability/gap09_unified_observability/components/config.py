"""Production configuration subsystem (15) -- typed, versioned, auditable.

A config document is validated against ``SCHEMA`` (unknown keys refused,
dangerous settings refused), receives a sha256 digest over its CSP/1 bytes,
and is activated atomically.  The previous N versions are kept for rollback.
Overlays (base <- environment <- site) merge shallowly and the *merged*
result is what is validated and digested.
"""
from __future__ import annotations

import hashlib
import threading
from typing import Any

from .canonical import canonicalize
from .errors import ConfigRejected

SCHEMA: dict[str, tuple[type, Any, Any]] = {
    # key: (type, min, max)
    "staleness_bound": (int, 1, 86_400),
    "max_batch_size": (int, 1, 10_000),
    "replay_window": (int, 60, 30 * 86_400),
    "max_clock_skew": (int, 0, 300),
    "tenant_rate": (float, 0.001, 1e7),
    "tenant_burst": (float, 1, 1e8),
    "reporter_rate": (float, 0.001, 1e7),
    "reporter_burst": (float, 1, 1e8),
    "tenant_series_limit": (int, 1, 10_000_000),
    "retention_seconds": (int, 60, 400 * 86_400),
    "allow_legacy_trust": (bool, None, None),
    "log_level": (str, None, None),
}
REQUIRED = frozenset(SCHEMA) - {"log_level"}
DANGEROUS = {"allow_legacy_trust": True}
LOG_LEVELS = frozenset({"error", "warn", "info", "debug"})


def validate(doc: dict) -> dict:
    if not isinstance(doc, dict):
        raise ConfigRejected("config must be an object")
    unknown = set(doc) - set(SCHEMA)
    if unknown:
        raise ConfigRejected("unknown config keys", keys=sorted(unknown))
    missing = REQUIRED - set(doc)
    if missing:
        raise ConfigRejected("missing config keys", keys=sorted(missing))
    for k, v in doc.items():
        typ, lo, hi = SCHEMA[k]
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if typ is not bool and isinstance(v, bool) or not isinstance(v, typ):
            raise ConfigRejected("wrong type", key=k)
        if lo is not None and not (lo <= v <= hi):
            raise ConfigRejected("out of range", key=k)
        if k in DANGEROUS and v == DANGEROUS[k]:
            raise ConfigRejected("dangerous setting refused in production config", key=k)
        if k == "log_level" and v not in LOG_LEVELS:
            raise ConfigRejected("invalid log level")
    if doc["tenant_burst"] < doc["tenant_rate"] or doc["reporter_burst"] < doc["reporter_rate"]:
        raise ConfigRejected("burst must be >= rate")
    return doc


def digest(doc: dict) -> str:
    return hashlib.sha256(canonicalize(doc).encode()).hexdigest()


class ConfigManager:
    def __init__(self, initial: dict, *, author: str, audit=None, keep: int = 10, at: int = 0) -> None:
        self._lock = threading.Lock()
        self._audit = audit
        self._keep = keep
        self._history: list[dict] = []
        self._activate(initial, author=author, at=at, reason="initial")

    def _activate(self, doc: dict, *, author: str, at: int, reason: str) -> dict:
        validate(doc)
        rec = {"version": (self._history[-1]["version"] + 1) if self._history else 1, "digest": digest(doc),
               "author": author, "activated_at": at, "reason": reason, "config": dict(doc)}
        self._history.append(rec)
        del self._history[:-self._keep]
        if self._audit:
            self._audit.append("config", {"version": rec["version"], "digest": rec["digest"], "reason": reason}, actor=author)
        return rec

    @staticmethod
    def merge(*layers: dict) -> dict:
        out: dict = {}
        for layer in layers:
            out.update(layer)
        return out

    def apply(self, doc: dict, *, author: str, at: int, reason: str) -> dict:
        with self._lock:
            return self._activate(doc, author=author, at=at, reason=reason)  # validate() raises before any change

    def rollback(self, *, author: str, at: int) -> dict:
        with self._lock:
            if len(self._history) < 2:
                raise ConfigRejected("no previous version to roll back to")
            prev = self._history[-2]["config"]
            return self._activate(prev, author=author, at=at, reason=f"rollback-to-v{self._history[-2]['version']}")

    @property
    def active(self) -> dict:
        with self._lock:
            return dict(self._history[-1])

    def active_digest(self) -> str:
        return self.active["digest"]
