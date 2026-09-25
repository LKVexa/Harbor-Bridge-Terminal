"""Declarative configuration with overlays, provenance, atomic activation and
rollback (MC-17 .. MC-20).

A configuration is a JSON document validated against ``SCHEMA`` (a small,
stdlib-checked subset of JSON Schema).  ``ConfigStore`` layers
base -> environment -> site overlays, stamps provenance (author, version,
digest, activated_at), activates atomically (write temp + fsync + rename),
keeps a bounded history and rolls back automatically when a post-activation
health probe fails.  ``describe()`` output is redacted for diagnostics.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .grants import MAX_DELEGATION_DEPTH, SecurityPlaneError
from .observability import redact

SECURE_DEFAULTS: dict[str, Any] = {
    "require_signatures": True,
    "require_v2": False,
    "clock_skew_seconds": 5,
    "max_ttl_seconds": 3600,
    "max_delegation_depth": MAX_DELEGATION_DEPTH,
    "revocation_horizon_seconds": 300,
    "admission": {"rate_per_second": 500, "burst": 1000},
    "breaker": {"failure_threshold": 5, "reset_seconds": 30},
    "allowed_algorithms": ["Ed25519"],
    "tenant_quota_default": 1000,
}

# key -> (type, validator)
SCHEMA: dict[str, tuple[type | tuple, Callable[[Any], bool]]] = {
    "require_signatures": (bool, lambda v: True),
    "require_v2": (bool, lambda v: True),
    "clock_skew_seconds": (int, lambda v: 0 <= v <= 300),
    "max_ttl_seconds": (int, lambda v: 1 <= v <= 30 * 86400),
    "max_delegation_depth": (int, lambda v: 0 <= v <= MAX_DELEGATION_DEPTH),
    "revocation_horizon_seconds": (int, lambda v: 0 <= v <= 86400),
    "admission": (dict, lambda v: v.get("rate_per_second", 0) > 0 and v.get("burst", 0) > 0),
    "breaker": (dict, lambda v: v.get("failure_threshold", 0) > 0 and v.get("reset_seconds", 0) > 0),
    "allowed_algorithms": (list, lambda v: bool(v) and set(v) <= {"Ed25519", "HMAC-SHA256"}),
    "tenant_quota_default": (int, lambda v: v > 0),
    "signing_secret": (str, lambda v: len(v) >= 32),
}
# Keys that may only be tightened by overlays (never relaxed).
SECURITY_MONOTONIC = {"require_signatures": "true-sticky", "require_v2": "true-sticky"}


class ConfigInvalid(SecurityPlaneError):
    code = "config.invalid"


def validate(cfg: dict) -> dict:
    unknown = set(cfg) - set(SCHEMA)
    if unknown:
        raise ConfigInvalid("unknown configuration keys", details={"keys": sorted(unknown)})
    for key, value in cfg.items():
        typ, ok = SCHEMA[key]
        if isinstance(value, bool) and typ is int:
            raise ConfigInvalid(f"{key} must be an integer")
        if not isinstance(value, typ) or not ok(value):
            raise ConfigInvalid(f"{key} is out of range or wrong type", details={"key": key})
    return cfg


def merge(base: dict, *overlays: dict) -> dict:
    out = copy.deepcopy(base)
    for layer in overlays:
        for k, v in layer.items():
            if SECURITY_MONOTONIC.get(k) == "true-sticky" and out.get(k) is True and v is False:
                raise ConfigInvalid(f"overlay may not relax {k}", details={"key": k})
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = {**out[k], **v}
            else:
                out[k] = v
    return validate(out)


def digest(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode()).hexdigest()


@dataclass
class ConfigStore:
    path: Path | None = None
    history_limit: int = 20
    active: dict = field(default_factory=lambda: {"config": copy.deepcopy(SECURE_DEFAULTS),
                                                  "provenance": {"version": 0, "author": "defaults",
                                                                 "digest": digest(SECURE_DEFAULTS)}})
    history: list[dict] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        if self.path is not None:
            self.path = Path(self.path)
            if self.path.exists():
                doc = json.loads(self.path.read_text())
                validate(doc["config"])
                if digest(doc["config"]) != doc["provenance"]["digest"]:
                    raise ConfigInvalid("persisted configuration digest mismatch")
                self.active = doc

    def _persist(self, doc: dict) -> None:
        if self.path is None:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".cfg-")
        with os.fdopen(fd, "w") as fh:
            json.dump(doc, fh, sort_keys=True)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)  # atomic on POSIX and Windows

    def activate(self, *overlays: dict, author: str, change_id: str,
                 health_probe: Callable[[dict], bool] | None = None) -> dict:
        with self._lock:
            new_cfg = merge(SECURE_DEFAULTS, *overlays)
            prev = self.active
            doc = {"config": new_cfg, "provenance": {
                "version": prev["provenance"]["version"] + 1, "author": author,
                "change_id": change_id, "digest": digest(new_cfg),
                "previous_digest": prev["provenance"]["digest"], "activated_at": int(time.time())}}
            self._persist(doc)
            self.history.append(prev)
            del self.history[: max(0, len(self.history) - self.history_limit)]
            self.active = doc
        if health_probe is not None:
            ok = False
            try:
                ok = bool(health_probe(new_cfg))
            except Exception:
                ok = False
            if not ok:
                self.rollback(author="auto-rollback", reason="health probe failed")
                raise ConfigInvalid("activation failed health probe; rolled back",
                                    details={"digest": doc["provenance"]["digest"]})
        return doc

    def rollback(self, *, author: str, reason: str = "") -> dict:
        with self._lock:
            if not self.history:
                raise ConfigInvalid("no previous configuration to roll back to")
            prev = self.history.pop()
            doc = {"config": prev["config"], "provenance": {
                **prev["provenance"], "rolled_back_by": author, "rollback_reason": reason,
                "version": self.active["provenance"]["version"] + 1}}
            self._persist(doc)
            self.active = doc
            return doc

    @property
    def config(self) -> dict:
        return self.active["config"]

    def describe(self) -> dict:
        return redact(self.active)
