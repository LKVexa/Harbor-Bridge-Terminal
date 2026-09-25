"""Governed configuration for INV-14 (component P2-30, C033-C038).

A config document (``PK_POLL_CONFIG/1``) carries provenance -- version, author,
activation time, reason -- and is layered base -> environment -> site overlay.
Updates are atomic: a candidate is fully validated before it replaces the active
document; a rejected candidate leaves the active config untouched (fail closed).
Every applied document has a content digest recorded in its history.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading

try:
    from .errors import Inv14Error
    from .clock import validate_clock_config, CLOCK_SCHEMA
    from .polling import DEFAULT_MAX_POLLABLES
except ImportError:
    from errors import Inv14Error
    from clock import validate_clock_config, CLOCK_SCHEMA
    from polling import DEFAULT_MAX_POLLABLES

CONFIG_SCHEMA = "PK_POLL_CONFIG/1"
LIMIT_KEYS = {"max_pollables": (1, 65_536), "max_concurrent_polls": (1, 100_000),
              "tenant_max_concurrent_polls": (1, 100_000), "queue_depth": (0, 100_000)}
MAX_HISTORY = 64
_MAX_DOC_BYTES = 65_536


class ConfigError(Inv14Error):
    default_code = "PK_CONFIG_INVALID"


def canonical(doc: dict) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()


def digest(doc: dict) -> str:
    return hashlib.sha256(canonical(doc)).hexdigest()


def validate_config(doc: object) -> dict:
    if not isinstance(doc, dict):
        raise ConfigError("config must be an object")
    try:
        size = len(canonical(doc))
    except (TypeError, ValueError):  # defect D-02: non-JSON values crashed validation
        raise ConfigError("config contains non-JSON values", code="PK_CONFIG_INVALID") from None
    if size > _MAX_DOC_BYTES:
        raise ConfigError("config document too large", code="PK_CONFIG_TOO_LARGE")
    if doc.get("schema") != CONFIG_SCHEMA:
        raise ConfigError("wrong config schema", code="PK_CONFIG_SCHEMA_MISMATCH")
    prov = doc.get("provenance")
    if not isinstance(prov, dict):
        raise ConfigError("provenance block required", code="PK_CONFIG_NO_PROVENANCE")
    if set(prov) != {"version", "author", "activated_at", "reason"}:  # defect D-03: code accepted keys the schema refuses
        raise ConfigError("provenance must contain exactly version/author/activated_at/reason",
                          code="PK_CONFIG_NO_PROVENANCE")
    for k in ("version", "author", "activated_at", "reason"):
        if not isinstance(prov.get(k), str) or not prov[k].strip() or len(prov[k]) > 256:
            raise ConfigError(f"provenance.{k} required", code="PK_CONFIG_NO_PROVENANCE", details={"field": k})
    limits = doc.get("limits")
    if not isinstance(limits, dict) or set(limits) != set(LIMIT_KEYS):
        raise ConfigError("limits must contain exactly the governed keys", details={"expected": sorted(LIMIT_KEYS)})
    for k, (lo, hi) in LIMIT_KEYS.items():
        v = limits[k]
        if not isinstance(v, int) or isinstance(v, bool) or not lo <= v <= hi:
            raise ConfigError(f"limits.{k} out of range", code="PK_CONFIG_LIMIT_RANGE", details={k: repr(v)})
    if limits["tenant_max_concurrent_polls"] > limits["max_concurrent_polls"]:
        raise ConfigError("tenant ceiling exceeds global ceiling", code="PK_CONFIG_LIMIT_RANGE")
    validate_clock_config(doc.get("clock"))
    extra = set(doc) - {"schema", "provenance", "limits", "clock", "legacy_polls_enabled"}
    if extra:
        raise ConfigError("unknown config keys", details={"keys": sorted(extra)})
    if not isinstance(doc.get("legacy_polls_enabled", True), bool):
        raise ConfigError("legacy_polls_enabled must be boolean")
    return doc


def merge(base: dict, *overlays: dict) -> dict:
    out = copy.deepcopy(base)
    for ov in overlays:
        if not isinstance(ov, dict):
            raise ConfigError("overlay must be an object", code="PK_CONFIG_OVERLAY")
        for k, v in ov.items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = merge(out[k], v)
            else:
                out[k] = copy.deepcopy(v)
    return out


class ConfigStore:
    """Atomic, validated, history-keeping holder for the active config."""

    def __init__(self, initial: dict):
        validate_config(initial)
        self._lock = threading.Lock()
        self._active = copy.deepcopy(initial)
        self._history = [{"version": initial["provenance"]["version"], "digest": digest(initial)}]

    @property
    def active(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._active)

    def update(self, candidate: dict) -> dict:
        validate_config(candidate)  # raises before any mutation
        with self._lock:
            if candidate["provenance"]["version"] == self._active["provenance"]["version"] \
                    and digest(candidate) != digest(self._active):
                raise ConfigError("same version with different content", code="PK_CONFIG_VERSION_REUSE")
            self._active = copy.deepcopy(candidate)
            self._history.append({"version": candidate["provenance"]["version"], "digest": digest(candidate)})
            del self._history[:-MAX_HISTORY]
            return {"version": candidate["provenance"]["version"], "digest": self._history[-1]["digest"]}

    def history(self) -> list:
        with self._lock:
            return list(self._history)


BASE_CONFIG = {
    "schema": CONFIG_SCHEMA,
    "provenance": {"version": "4.3.0-base", "author": "inv14-release-build",
                   "activated_at": "2026-09-22T00:00:00Z", "reason": "v4.3.0 defaults"},
    "limits": {"max_pollables": DEFAULT_MAX_POLLABLES, "max_concurrent_polls": 1024,
               "tenant_max_concurrent_polls": 64, "queue_depth": 0},
    "clock": {"schema": CLOCK_SCHEMA, "tick_nanoseconds": 1_000_000, "max_timeout_ticks": 60_000,
              "clock_source": "monotonic"},
    "legacy_polls_enabled": True,
}
