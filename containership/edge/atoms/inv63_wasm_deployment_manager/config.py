"""Declarative configuration with secure defaults, overlays, validation,
provenance, atomic activation and rollback (INV-63-C033..C039).

Configuration is data (``PK_DEPLOY_CONFIG/1``) layered as
``defaults <- base file <- environment overlay <- site overlay``; the immutable
package is never rebuilt per site (C035).  Activation is all-or-nothing: the
candidate is fully merged and validated, then swapped in with one reference
assignment and recorded with digest/author/time/previous (C036/C037).
"""
from __future__ import annotations

import copy
import hashlib
import json
import pathlib
import time
from dataclasses import dataclass
from typing import Any, Callable

from . import schema
from .errors import DeploymentError, ErrorCode
from .security import looks_secret

SECURE_DEFAULTS: dict[str, Any] = {
    "schema": "PK_DEPLOY_CONFIG/1",
    "environment": "prod",           # the strictest profile is the default
    "site": "default",
    "tier": "cloud",
    "max_unavailable_default": 1,
    "reconcile_interval_s": 30,
    "request_timeout_ms": 5000,
    "max_inflight": 64,
    "queue_depth": 1024,
    "offline_autonomy_s": 3600,
    "max_clock_skew_s": 30,
    "require_signed_artifacts": True,
    "require_encryption_at_rest": True,
    "allow_unauthenticated": False,
    "telemetry_sampling": 0.1,
    "tenant_quotas": {},
    "residency_labels": {},
    "stall_threshold_s": 120,
    "retry_max_attempts": 4,
    "circuit_failure_threshold": 5,
    "secret_refs": {},
    "trusted_key_ids": [],
}

# settings whose weakening is security-critical: fail closed in prod (C034)
SECURITY_CRITICAL = {"require_signed_artifacts": True, "require_encryption_at_rest": True,
                     "allow_unauthenticated": False}


def _merge(base: dict[str, Any], over: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def _scan_secrets(obj: Any, path: str = "") -> list[str]:
    hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{path}.{k}" if path else k
            if path.startswith("secret_refs"):
                if not (isinstance(v, str) and v.startswith(("env:", "file:"))):
                    hits.append(p)
                continue
            if looks_secret(str(k), v):
                hits.append(p)
            hits += _scan_secrets(v, p)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            hits += _scan_secrets(v, f"{path}[{i}]")
    elif isinstance(obj, str) and looks_secret("", obj):
        hits.append(path)
    return hits


def validate(cfg: dict[str, Any]) -> dict[str, Any]:
    # secret scan first: a leaked secret is always classified as such and is
    # never echoed back inside a schema error message
    hits = _scan_secrets(cfg)
    if hits:
        raise DeploymentError(ErrorCode.SECRET_IN_CONFIG, "secret material must be a secret ref (env:/file:)",
                              {"paths": hits})
    try:
        schema.validate(cfg, "PK_DEPLOY_CONFIG/1")
    except DeploymentError as exc:
        raise DeploymentError(ErrorCode.CONFIG_INVALID, exc.message, exc.details) from None
    if cfg["environment"] == "prod":
        for k, required in SECURITY_CRITICAL.items():
            if cfg.get(k) != required:
                raise DeploymentError(ErrorCode.CONFIG_INVALID, f"{k} must be {required} in prod", {"key": k})
    if cfg["tier"] == "far-edge" and cfg["offline_autonomy_s"] < 300:
        raise DeploymentError(ErrorCode.CONFIG_INVALID, "far-edge requires offline_autonomy_s >= 300")
    for tenant, q in cfg.get("tenant_quotas", {}).items():
        if not isinstance(q, dict) or not isinstance(q.get("max_instances"), int) or q["max_instances"] < 0:
            raise DeploymentError(ErrorCode.CONFIG_INVALID, f"tenant_quotas.{tenant}.max_instances invalid")
    return cfg


def config_digest(cfg: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compose(*layers: dict[str, Any]) -> dict[str, Any]:
    cfg = copy.deepcopy(SECURE_DEFAULTS)
    for layer in layers:
        if not isinstance(layer, dict):
            raise DeploymentError(ErrorCode.CONFIG_INVALID, "config layer must be an object")
        cfg = _merge(cfg, layer)
    return validate(cfg)


def load_layers(config_dir: str | pathlib.Path, environment: str, site: str) -> list[dict[str, Any]]:
    d = pathlib.Path(config_dir)
    layers = []
    for rel in ("base.json", f"env/{environment}.json", f"site/{site}.json"):
        p = d / rel
        if p.is_file():
            layers.append(json.loads(p.read_text()))
    return layers


@dataclass(frozen=True)
class Activation:
    version: int
    digest: str
    author: str
    activated_at: float
    reason: str
    previous_digest: str | None


class ConfigStore:
    def __init__(self, clock: Callable[[], float] = time.time, journal: Any = None):
        self.clock = clock
        self.journal = journal
        self.history: list[tuple[Activation, dict[str, Any]]] = []
        self.active: dict[str, Any] | None = None

    def activate(self, cfg_layers: list[dict[str, Any]], author: str, reason: str) -> Activation:
        if not author or not isinstance(author, str):
            raise DeploymentError(ErrorCode.CONFIG_INVALID, "activation requires an author")
        candidate = compose(*cfg_layers)            # full validation BEFORE any swap
        act = Activation(len(self.history) + 1, config_digest(candidate), author, self.clock(), reason,
                         self.history[-1][0].digest if self.history else None)
        if self.journal is not None:
            self.journal.append("config_activated", {"version": act.version, "digest": act.digest,
                                                     "author": author, "reason": reason,
                                                     "previous": act.previous_digest})
        self.history.append((act, candidate))
        self.active = candidate                     # single reference swap: atomic
        return act

    def rollback(self, author: str, reason: str = "rollback") -> Activation:
        if len(self.history) < 2:
            raise DeploymentError(ErrorCode.PRECONDITION_FAILED, "no previous configuration to roll back to")
        previous = self.history[-2][1]
        return self.activate([previous], author, reason)

    @property
    def current(self) -> Activation | None:
        return self.history[-1][0] if self.history else None
