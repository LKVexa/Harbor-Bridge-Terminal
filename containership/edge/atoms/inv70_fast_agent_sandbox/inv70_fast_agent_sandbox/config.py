"""Configuration for INV-70.

C035  base -> environment -> site overlays with a closed, typed schema
C036  provenance/activation record (who, what digest, from which sources, when, why)
C037  atomic validate-then-swap activation with last-known-good rollback
"""
from __future__ import annotations

import copy
import threading
import time

from .security import canonical, sha256_hex

# Closed schema: key -> (type, min, max).  Unknown keys are rejected.
SCHEMA = {
    "fuel": (int, 1, 10_000_000),
    "max_stack": (int, 1, 4096),
    "max_memory_bytes": (int, 1024, 256 * 1024 * 1024),
    "max_value_bytes": (int, 16, 64 * 1024 * 1024),
    "max_program_instructions": (int, 1, 1_000_000),
    "wall_clock_ms": (int, 1, 300_000),
    "host_call_timeout_ms": (int, 1, 60_000),
    "max_concurrent": (int, 1, 100_000),
    "per_tenant_concurrent": (int, 1, 10_000),
    "rate_per_s": (int, 1, 1_000_000),
    "warm_workers": (int, 0, 256),
    "isolation": (str, None, None),       # "process" | "inline-dev"
    "backend": (str, None, None),         # "reference-vm" | "wasm"
    "residency": (list, None, None),
}
ENUMS = {"isolation": {"process", "inline-dev"}, "backend": {"reference-vm", "wasm"}}

BASE = {
    "fuel": 1_000, "max_stack": 64, "max_memory_bytes": 64 * 1024, "max_value_bytes": 16 * 1024,
    "max_program_instructions": 4_096, "wall_clock_ms": 2_000, "host_call_timeout_ms": 500,
    "max_concurrent": 64, "per_tenant_concurrent": 16, "rate_per_s": 1_000, "warm_workers": 4,
    "isolation": "process", "backend": "reference-vm", "residency": ["local"],
}

# Environment overlays may only tighten security-relevant settings in prod.
ENVIRONMENTS = {
    "dev": {"isolation": "inline-dev", "wall_clock_ms": 10_000, "warm_workers": 0},
    "staging": {},
    "prod": {"wall_clock_ms": 1_000},
    "edge": {"max_concurrent": 8, "per_tenant_concurrent": 4, "max_memory_bytes": 32 * 1024,
             "max_value_bytes": 8 * 1024, "rate_per_s": 100, "warm_workers": 1},
}
PROD_LIKE = {"prod", "edge"}


class ConfigError(ValueError):
    pass


def validate(cfg: dict, environment: str) -> None:
    unknown = set(cfg) - set(SCHEMA)
    if unknown:
        raise ConfigError(f"unknown key: {sorted(unknown)[0]}")
    missing = set(SCHEMA) - set(cfg)
    if missing:
        raise ConfigError(f"missing key: {sorted(missing)[0]}")
    for k, (t, lo, hi) in SCHEMA.items():
        v = cfg[k]
        if type(v) is not t:
            raise ConfigError(f"{k}: wrong type")
        if lo is not None and not lo <= v <= hi:
            raise ConfigError(f"{k}: out of range")
        if k in ENUMS and v not in ENUMS[k]:
            raise ConfigError(f"{k}: not an allowed value")
    if cfg["max_value_bytes"] > cfg["max_memory_bytes"]:
        raise ConfigError("max_value_bytes > max_memory_bytes")
    if cfg["per_tenant_concurrent"] > cfg["max_concurrent"]:
        raise ConfigError("per_tenant_concurrent > max_concurrent")
    if cfg["host_call_timeout_ms"] > cfg["wall_clock_ms"]:
        raise ConfigError("host_call_timeout_ms > wall_clock_ms")
    if environment in PROD_LIKE and cfg["isolation"] != "process":
        raise ConfigError("prod-like environments require process isolation")
    if not cfg["residency"] or not all(type(r) is str for r in cfg["residency"]):
        raise ConfigError("residency must be a non-empty list of region names")


def resolve(environment: str, site_overlay: dict | None = None) -> tuple[dict, list[str]]:
    """Return (effective config, ordered layer list)."""
    if environment not in ENVIRONMENTS:
        raise ConfigError(f"unknown environment: {environment}")
    cfg = copy.deepcopy(BASE)
    layers = ["base"]
    cfg.update(copy.deepcopy(ENVIRONMENTS[environment]))
    layers.append(f"env:{environment}")
    if site_overlay:
        site_overlay = dict(site_overlay)
        name = site_overlay.pop("_site", "unnamed")
        if environment in PROD_LIKE and site_overlay.get("isolation", "process") != "process":
            raise ConfigError("site overlay may not weaken isolation in prod-like environments")
        cfg.update(copy.deepcopy(site_overlay))
        layers.append(f"site:{name}")
    validate(cfg, environment)
    return cfg, layers


def digest(cfg: dict) -> str:
    return "sha256:" + sha256_hex(canonical(cfg))


class ConfigStore:
    """Holds the active config; activation is all-or-nothing under a lock."""

    def __init__(self, environment: str, audit=None, clock=time.time):
        self.environment, self.audit, self.clock = environment, audit, clock
        self._lock = threading.Lock()
        cfg, layers = resolve(environment)
        self.active = cfg
        self.history: list[dict] = []
        self.frozen = False     # set by degraded control-plane mode (C056)
        self._record(cfg, layers, actor="bootstrap", reason="initial", previous=None, overlay=None)

    def _record(self, cfg, layers, *, actor, reason, previous, overlay):
        rec = {"digest": digest(cfg), "previous": previous, "layers": layers, "environment": self.environment,
               "actor": actor, "reason": reason, "activated_at": self.clock(),
               "overlay": copy.deepcopy(overlay)}
        if self.audit is not None:   # audit first: a failed audit write aborts activation
            self.audit.append("config.activated", digest=rec["digest"], previous=previous, actor=actor,
                              layers=layers, reason=reason)
        self.history.append(rec)
        return rec

    @property
    def active_digest(self) -> str:
        return self.history[-1]["digest"]

    def activate(self, site_overlay: dict | None, *, actor: str, reason: str, precheck=None) -> dict:
        """Validate fully, run optional precheck on the candidate, then swap atomically.
        Any failure leaves the active configuration untouched."""
        if self.frozen:
            raise ConfigError("configuration changes frozen (degraded control plane)")
        if not actor or not reason:
            raise ConfigError("actor and reason are required")
        cand, layers = resolve(self.environment, site_overlay)
        if precheck is not None and not precheck(cand):
            raise ConfigError("candidate failed precheck")
        with self._lock:
            prev = self.active_digest
            rec = self._record(cand, layers, actor=actor, reason=reason, previous=prev, overlay=site_overlay)
            self.active = cand
            return rec

    def rollback(self, *, actor: str, reason: str) -> dict:
        """Re-activate the previous configuration (last known good) from its stored overlay."""
        if len(self.history) < 2:
            raise ConfigError("no previous configuration")
        overlay = self.history[-2]["overlay"]
        cand, layers = resolve(self.environment, overlay)
        with self._lock:
            prev = self.active_digest
            rec = self._record(cand, layers, actor=actor, reason="rollback: " + reason, previous=prev,
                               overlay=overlay)
            self.active = cand
            return rec
