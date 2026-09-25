"""Checklist 14: declarative configuration with secure defaults, layered
overrides, provenance, transactional activation and rollback.

Layering: ``defaults < site < environment``.  An override may only tighten
security-relevant keys (``TIGHTEN_ONLY``); a looser value is refused with
``config_loosening_refused``.  Every activation is a transaction: the
candidate is merged, validated against ``schemas/INV43_CONFIG_1.schema.json``
rules (implemented here without third-party code) and only then swapped in
atomically.  History is kept so ``rollback()`` restores the previous active
revision.  Every revision carries a provenance record (digest, source
labels, author, time, parent digest).
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
import time

from .defense import MitigationMissing

CONFIG_SCHEMA = "INV43_CONFIG/1"

SECURE_DEFAULTS: dict = {
    "schema": CONFIG_SCHEMA,
    "posture_ttl_s": 300.0,
    "require_attestation": True,
    "unknown_smt_is_enabled": True,
    "max_request_bytes": 65536,
    "max_inflight": 64,
    "rate_per_s": 500.0,
    "request_timeout_s": 2.0,
    "cross_tenant_placement_enabled": True,
    "log_redact_tenants": True,
    "policy_path": "policy/default_policy.json",
}

# key -> (type, min, max)
_TYPES = {
    "posture_ttl_s": (float, 1.0, 3600.0),
    "require_attestation": (bool, None, None),
    "unknown_smt_is_enabled": (bool, None, None),
    "max_request_bytes": (int, 256, 1_048_576),
    "max_inflight": (int, 1, 4096),
    "rate_per_s": (float, 0.1, 100000.0),
    "request_timeout_s": (float, 0.05, 30.0),
    "cross_tenant_placement_enabled": (bool, None, None),
    "log_redact_tenants": (bool, None, None),
    "policy_path": (str, None, None),
}

# Overrides may move these only in the stricter direction.
TIGHTEN_ONLY = {
    "posture_ttl_s": "lower",
    "require_attestation": "true",
    "unknown_smt_is_enabled": "true",
    "log_redact_tenants": "true",
}


class ConfigError(MitigationMissing):
    def __init__(self, message: str, code: str, **details):
        super().__init__(message, code=code, details=details)


def digest(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def validate(cfg: dict) -> None:
    if not isinstance(cfg, dict) or cfg.get("schema") != CONFIG_SCHEMA:
        raise ConfigError("config schema must be INV43_CONFIG/1", "config_schema")
    extra = set(cfg) - set(_TYPES) - {"schema"}
    if extra:
        raise ConfigError(f"unknown config keys {sorted(extra)}", "config_unknown_key", keys=sorted(extra))
    for key, (typ, lo, hi) in _TYPES.items():
        if key not in cfg:
            raise ConfigError(f"missing {key}", "config_missing_key", key=key)
        v = cfg[key]
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if isinstance(v, bool) != (typ is bool) or not isinstance(v, typ):
            raise ConfigError(f"{key} must be {typ.__name__}", "config_type", key=key)
        if lo is not None and not (lo <= v <= hi):
            raise ConfigError(f"{key} out of range [{lo}, {hi}]", "config_range", key=key)
    if cfg["require_attestation"] is not True:
        raise ConfigError("require_attestation may not be disabled", "config_insecure", key="require_attestation")


def _check_tighten(base: dict, override: dict, layer: str) -> None:
    for k, rule in TIGHTEN_ONLY.items():
        if k not in override:
            continue
        old, new = base.get(k), override[k]
        if rule == "lower" and isinstance(new, (int, float)) and new > old:
            raise ConfigError(f"{layer} may not raise {k}", "config_loosening_refused", key=k, layer=layer)
        if rule == "true" and new is not True:
            raise ConfigError(f"{layer} may not disable {k}", "config_loosening_refused", key=k, layer=layer)


def merge(site: dict | None = None, environment: dict | None = None) -> dict:
    cfg = copy.deepcopy(SECURE_DEFAULTS)
    for layer, ov in (("site", site), ("environment", environment)):
        if not ov:
            continue
        if not isinstance(ov, dict):
            raise ConfigError(f"{layer} override must be an object", "config_type")
        _check_tighten(cfg, ov, layer)
        cfg.update(ov)
    validate(cfg)
    return cfg


class ConfigStore:
    """Transactional activation with rollback history."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        base = merge()
        self._history: list[dict] = [self._rev(base, "secure-defaults", None, "system")]

    def _rev(self, cfg: dict, source: str, parent: str | None, author: str) -> dict:
        return {"config": cfg, "provenance": {"digest": digest(cfg), "source": source, "parent": parent,
                                              "author": author, "activated_at": time.time()}}

    @property
    def active(self) -> dict:
        with self._lock:
            return copy.deepcopy(self._history[-1]["config"])

    @property
    def provenance(self) -> dict:
        with self._lock:
            return dict(self._history[-1]["provenance"])

    def activate(self, *, site: dict | None = None, environment: dict | None = None,
                 source: str, author: str, precheck=None) -> dict:
        cand = merge(site, environment)  # raises before anything changes
        if precheck is not None and not precheck(cand):
            raise ConfigError("activation precheck refused candidate", "config_precheck_failed")
        with self._lock:
            parent = self._history[-1]["provenance"]["digest"]
            self._history.append(self._rev(cand, source, parent, author))
            return dict(self._history[-1]["provenance"])

    def rollback(self, author: str) -> dict:
        with self._lock:
            if len(self._history) < 2:
                raise ConfigError("no previous revision", "config_no_previous")
            bad = self._history.pop()
            self._history[-1] = dict(self._history[-1])
            self._history[-1]["provenance"] = dict(self._history[-1]["provenance"],
                                                   rolled_back_from=bad["provenance"]["digest"],
                                                   rolled_back_by=author)
            return dict(self._history[-1]["provenance"])

    def history(self) -> list[dict]:
        with self._lock:
            return [dict(h["provenance"]) for h in self._history]
