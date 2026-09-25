"""Declarative configuration for INV-53 (components 22-26, 28).

* ``SCHEMA`` is the single declarative schema: type, bounds and the secure default
  for every key.  Unknown keys are rejected (no silent typos).
* ``layer()`` resolves base -> environment -> site overrides deterministically and
  records which layer supplied each key (provenance).
* ``ConfigStore`` applies updates atomically (validate fully, compare-and-swap on
  the version, write via temp file + ``os.replace``) and keeps a bounded history
  so ``rollback()`` restores the previous validated revision.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from threading import RLock
from typing import Any, Mapping

CONFIG_SCHEMA_VERSION = "inv53.config/1"

# key: (type, min, max, secure default, description)
SCHEMA: dict[str, tuple[type, float | None, float | None, Any, str]] = {
    "visibility_seconds": (float, 0.001, 43_200, 30.0, "Lease visibility timeout."),
    "max_attempts": (int, 1, 100, 5, "Delivery attempts before dead-lettering."),
    "max_ready": (int, 1, 10_000_000, 100_000, "Hard cap on ready messages per queue."),
    "max_in_flight": (int, 1, 1_000_000, 10_000, "Hard cap on leased messages per queue."),
    "max_dead_letters": (int, 1, 10_000_000, 100_000, "Hard cap on dead letters per queue."),
    "max_message_bytes": (int, 64, 16_777_216, 262_144, "Largest accepted serialized message."),
    "max_lease_extension_seconds": (float, 0.001, 43_200, 300.0, "Largest single visibility extension."),
    "tenant_rate_per_second": (float, 0.001, 1_000_000, 500.0, "Token-bucket refill per tenant."),
    "tenant_burst": (int, 1, 1_000_000, 1_000, "Token-bucket depth per tenant."),
    "shed_ready_ratio": (float, 0.01, 1.0, 0.9, "Shed new puts when ready depth exceeds this share of max_ready."),
    "breaker_failure_threshold": (int, 1, 1000, 5, "Consecutive storage failures that open the breaker."),
    "breaker_reset_seconds": (float, 0.001, 3600, 30.0, "Open-breaker cool-down before a half-open probe."),
    "stall_seconds": (float, 0.001, 86_400, 120.0, "No progress while work is ready for this long => stalled."),
    "require_authentication": (bool, None, None, True, "Refuse unauthenticated calls (secure default)."),
    "fsync": (bool, None, None, True, "fsync each journal record before acknowledging the caller."),
    "audit_required": (bool, None, None, True, "Fail closed when the audit sink cannot record."),
}


class ConfigError(ValueError):
    pass


class ConfigConflict(ConfigError):
    """The expected version did not match (another writer won)."""


def _check(key: str, value: Any) -> Any:
    if key not in SCHEMA:
        raise ConfigError(f"unknown configuration key {key!r}")
    typ, lo, hi, _, _ = SCHEMA[key]
    if typ is bool:
        if not isinstance(value, bool):
            raise ConfigError(f"{key} must be a boolean")
        return value
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{key} must be numeric")
    if typ is int and (not isinstance(value, int) or isinstance(value, bool)):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        else:
            raise ConfigError(f"{key} must be an integer")
    value = typ(value)
    if not isfinite(float(value)):
        raise ConfigError(f"{key} must be finite")
    if lo is not None and value < lo or hi is not None and value > hi:
        raise ConfigError(f"{key}={value} outside [{lo}, {hi}]")
    return value


def defaults() -> dict[str, Any]:
    return {k: v[3] for k, v in SCHEMA.items()}


def validate(values: Mapping[str, Any]) -> dict[str, Any]:
    out = defaults()
    for k, v in values.items():
        out[k] = _check(k, v)
    if out["max_in_flight"] > out["max_ready"]:
        raise ConfigError("max_in_flight must not exceed max_ready")
    return out


def digest(values: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(values), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Effective:
    values: dict[str, Any]
    provenance: dict[str, str]      # key -> layer name that supplied it
    digest: str

    def record(self) -> dict[str, Any]:
        return {"schema": CONFIG_SCHEMA_VERSION, "digest": self.digest,
                "values": self.values, "provenance": self.provenance}


def layer(*layers: tuple[str, Mapping[str, Any]]) -> Effective:
    """Resolve ``("base", {...}), ("env:prod", {...}), ("site:edge-7", {...})`` in order."""
    merged: dict[str, Any] = {}
    prov = {k: "default" for k in SCHEMA}
    for name, values in layers:
        for k, v in values.items():
            merged[k] = _check(k, v)
            prov[k] = name
    values = validate(merged)
    return Effective(values, prov, digest(values))


class ConfigStore:
    """Versioned, atomic, rollback-capable configuration file."""

    def __init__(self, path: str | os.PathLike, *, history: int = 20) -> None:
        self.path = Path(path)
        self.history = history
        self._lock = RLock()
        if not self.path.exists():
            self._write({"version": 1, "current": defaults(), "previous": []})

    def _read(self) -> dict[str, Any]:
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _write(self, doc: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".cfg-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, sort_keys=True, indent=1)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)

    def current(self) -> tuple[int, dict[str, Any]]:
        with self._lock:
            doc = self._read()
            return doc["version"], validate(doc["current"])

    def update(self, changes: Mapping[str, Any], *, expected_version: int) -> int:
        with self._lock:
            doc = self._read()
            if doc["version"] != expected_version:
                raise ConfigConflict(f"expected version {expected_version}, store is {doc['version']}")
            new = validate({**doc["current"], **changes})     # raises before anything is written
            prev = ([{"version": doc["version"], "values": doc["current"]}] + doc["previous"])[: self.history]
            self._write({"version": doc["version"] + 1, "current": new, "previous": prev})
            return doc["version"] + 1

    def rollback(self) -> int:
        with self._lock:
            doc = self._read()
            if not doc["previous"]:
                raise ConfigError("no previous revision to roll back to")
            target, rest = doc["previous"][0], doc["previous"][1:]
            validate(target["values"])
            self._write({"version": doc["version"] + 1, "current": target["values"], "previous": rest,
                         "rolled_back_from": doc["version"]})
            return doc["version"] + 1
