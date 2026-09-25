"""Declarative runtime configuration: schema validation, provenance/activation
records, atomic rollout and rollback (items 18, 19, 20).

Unknown keys are refused; every activated config carries a digest, source and
activator; activation is all-or-nothing and the previous config is retained for
one-step rollback. Secrets are never inline — only ``secretRef`` names.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
from dataclasses import dataclass
from typing import Any

CONFIG_SCHEMA = "INV67_CONFIG/1"

DEFAULTS: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "watchNamespaces": [],             # empty = all namespaces permitted by RBAC
    "maxInflight": 256,
    "tenantInflight": {},
    "defaultTenantInflight": 16,
    "tenantRatePerSec": 20.0,
    "tenantBurst": 40.0,
    "retry": {"base": 0.2, "cap": 30.0, "maxAttempts": 8},
    "circuit": {"threshold": 5, "resetAfter": 30.0},
    "leaseDurationSec": 15.0,
    "staleObservationSec": 120.0,
    "allowedRegistries": [],
    "requireImageDigest": True,
    "requireSignature": True,
    "certifiedFeatures": ["cpu", "memory", "labels", "annotations", "multiContainer"],
    "downstream": {"endpoint": "", "tokenSecretRef": ""},
    "telemetry": {"logLevel": "info", "metricsPort": 9090, "healthPort": 8081},
}

_TYPES: dict[str, Any] = {
    "schema": str, "watchNamespaces": list, "maxInflight": int, "tenantInflight": dict,
    "defaultTenantInflight": int, "tenantRatePerSec": (int, float), "tenantBurst": (int, float),
    "retry": dict, "circuit": dict, "leaseDurationSec": (int, float), "staleObservationSec": (int, float),
    "allowedRegistries": list, "requireImageDigest": bool, "requireSignature": bool,
    "certifiedFeatures": list, "downstream": dict, "telemetry": dict,
}
_NESTED = {"retry": {"base", "cap", "maxAttempts"}, "circuit": {"threshold", "resetAfter"},
           "downstream": {"endpoint", "tokenSecretRef"}, "telemetry": {"logLevel", "metricsPort", "healthPort"}}


class ConfigError(ValueError):
    pass


def digest(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(raw: dict) -> dict:
    if not isinstance(raw, dict):
        raise ConfigError("config must be an object")
    unknown = sorted(set(raw) - set(_TYPES))
    if unknown:
        raise ConfigError(f"unknown config keys: {unknown}")
    cfg: dict[str, Any] = copy.deepcopy(DEFAULTS)
    for k, v in raw.items():
        if not isinstance(v, _TYPES[k]) or (isinstance(v, bool) and _TYPES[k] in (int, (int, float))):
            raise ConfigError(f"{k}: wrong type")
        if k in _NESTED:
            bad = sorted(set(v) - _NESTED[k])
            if bad:
                raise ConfigError(f"{k}: unknown keys {bad}")
            cfg[k].update(v)
        else:
            cfg[k] = v
    if cfg["schema"] != CONFIG_SCHEMA:
        raise ConfigError("unsupported config schema")
    for k in ("maxInflight", "defaultTenantInflight"):
        if cfg[k] < 1:
            raise ConfigError(f"{k} must be >= 1")
    if any(not isinstance(v, int) or v < 0 for v in cfg["tenantInflight"].values()):
        raise ConfigError("tenantInflight values must be non-negative ints")
    if not 0 < cfg["retry"]["base"] <= cfg["retry"]["cap"] or not 1 <= cfg["retry"]["maxAttempts"] <= 20:
        raise ConfigError("retry bounds invalid")
    if cfg["leaseDurationSec"] < 2:
        raise ConfigError("leaseDurationSec too small")
    ep = cfg["downstream"]["endpoint"]
    if ep and not ep.startswith("https://"):
        raise ConfigError("downstream endpoint must use https")
    for k, v in cfg["downstream"].items():
        if "token" in k.lower() and v and not str(v).startswith("secretRef:"):
            raise ConfigError("credentials must be secretRef:<name>, never inline")
    if cfg["telemetry"]["logLevel"] not in ("debug", "info", "warning", "error"):
        raise ConfigError("invalid logLevel")
    return cfg


@dataclass(frozen=True)
class Activation:
    digest: str
    previous: str | None
    source: str
    activator: str
    ts: float
    result: str


class ConfigStore:
    """Holds the active config; activation is atomic (swap after full validation
    and the optional pre-activation probe) and the prior config is retained."""

    def __init__(self, initial: dict | None = None, audit=None, clock=time.time):
        self._lock = threading.Lock()
        self.audit, self.clock = audit, clock
        self.active = validate(initial or {})
        self.previous: dict | None = None
        self.history: list[Activation] = [Activation(digest(self.active), None, "defaults", "system", clock(), "activated")]

    def activate(self, raw: dict, *, source: str, activator: str, probe=None) -> Activation:
        try:
            cfg = validate(raw)
            if probe is not None and not probe(cfg):
                raise ConfigError("pre-activation probe failed")
        except ConfigError as exc:
            rec = Activation(digest(raw) if isinstance(raw, dict) else "invalid", digest(self.active), source, activator,
                             self.clock(), f"rejected: {exc}")
            self.history.append(rec)
            if self.audit:
                self.audit.append(activator, "config.activate", source, "rejected", error=str(exc))
            raise
        with self._lock:
            prev = self.active
            self.previous, self.active = prev, cfg
            rec = Activation(digest(cfg), digest(prev), source, activator, self.clock(), "activated")
            self.history.append(rec)
        if self.audit:
            self.audit.append(activator, "config.activate", source, "activated", digest=rec.digest, previous=rec.previous)
        return rec

    def rollback(self, *, activator: str) -> Activation:
        with self._lock:
            if self.previous is None:
                raise ConfigError("no previous config to roll back to")
            cur = self.active
            self.active, self.previous = self.previous, cur
            rec = Activation(digest(self.active), digest(cur), "rollback", activator, self.clock(), "rolled-back")
            self.history.append(rec)
        if self.audit:
            self.audit.append(activator, "config.rollback", "config", "rolled-back", digest=rec.digest)
        return rec
