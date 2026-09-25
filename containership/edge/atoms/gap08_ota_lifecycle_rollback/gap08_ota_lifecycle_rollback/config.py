"""Configuration provenance system (component 26).

Configuration is code: every revision is a signed ``PK_CONFIG/1`` document with
author, a *distinct* approver, activation time, environment/site overlays and
the digest of its parent.  Activation is atomic (the active pointer moves in
one step) and configuration can be rolled back to any earlier approved revision.
Validation runs before signing; unknown keys are rejected.
"""
from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field
from typing import Any, Mapping

from .common import Clock, KeyRing, SystemClock, digest_of, sign_envelope, verify_envelope
from .errors import IntegrityFailure, Unauthorized, ValidationFailed

CONFIG_SCHEMA = "PK_CONFIG/1"
DEFAULTS: dict[str, Any] = {
    "gate": {"max_age_s": 300, "settle_s": 60, "min_coverage": 0.9, "min_healthy_ratio": 0.99},
    "blast_radius": {"max_fraction_per_domain": 0.34, "min_survivors_per_domain": 1, "max_fraction_per_site": 0.5},
    "admission": {"max_active_rollouts": 8, "max_wave_fanout": 500},
    "lease": {"ttl_s": 30},
    "deferred": {"max_attempts": 10, "expiry_s": 604800},
}


def _deep_merge(base: dict, over: Mapping) -> dict:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if k not in out:
            raise ValidationFailed(f"unknown config key {k}")
        out[k] = _deep_merge(out[k], v) if isinstance(out[k], dict) and isinstance(v, Mapping) else v
    return out


def validate(cfg: Mapping[str, Any]) -> None:
    g = cfg["gate"]
    if not (0 < g["min_coverage"] <= 1 and 0 < g["min_healthy_ratio"] <= 1 and g["max_age_s"] > 0):
        raise ValidationFailed("gate thresholds out of range")
    b = cfg["blast_radius"]
    if not (0 < b["max_fraction_per_domain"] <= 1 and b["min_survivors_per_domain"] >= 0):
        raise ValidationFailed("blast radius out of range")


@dataclass
class ConfigStore:
    keyring: KeyRing
    key_id: str
    clock: Clock = field(default_factory=SystemClock)
    _revs: list[dict[str, Any]] = field(default_factory=list)
    _active: int | None = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def propose(self, *, author: str, approver: str, base: Mapping[str, Any] | None = None,
                overlays: Mapping[str, Mapping[str, Any]] | None = None, note: str = "") -> dict[str, Any]:
        if not author or not approver or author == approver:
            raise Unauthorized("config requires a distinct author and approver")
        cfg = _deep_merge(DEFAULTS, base or {})
        validate(cfg)
        overlays = dict(overlays or {})
        for scope, ov in overlays.items():
            validate(_deep_merge(cfg, ov))
        with self._lock:
            parent = self._revs[-1]["body"]["digest"] if self._revs else None
            body = {"schema": CONFIG_SCHEMA, "revision": len(self._revs) + 1, "parent": parent, "author": author,
                    "approver": approver, "created_at": self.clock.now(), "base": cfg, "overlays": overlays,
                    "note": note}
            body["digest"] = digest_of(body)
            env = sign_envelope(self.keyring, self.key_id, body)
            self._revs.append(env)
            return env

    def activate(self, revision: int) -> dict[str, Any]:
        with self._lock:
            env = self._revs[revision - 1]
            if verify_envelope(self.keyring, env) is None:
                raise IntegrityFailure("config revision signature invalid")
            self._active = revision
            return {"event": "config_activated", "revision": revision, "digest": env["body"]["digest"],
                    "at": self.clock.now()}

    def rollback(self) -> dict[str, Any]:
        with self._lock:
            if not self._active or self._active <= 1:
                raise ValidationFailed("no earlier config revision")
            target = self._active - 1
        return self.activate(target)

    def effective(self, *, environment: str | None = None, site: str | None = None) -> dict[str, Any]:
        with self._lock:
            if self._active is None:
                raise ValidationFailed("no active configuration")
            body = self._revs[self._active - 1]["body"]
        cfg = copy.deepcopy(body["base"])
        for scope in (f"env:{environment}", f"site:{site}"):
            if scope in body["overlays"]:
                cfg = _deep_merge(cfg, body["overlays"][scope])
        cfg["_provenance"] = {"revision": body["revision"], "digest": body["digest"]}
        return cfg
