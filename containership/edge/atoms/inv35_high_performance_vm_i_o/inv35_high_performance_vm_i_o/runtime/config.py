"""Declarative, fail-closed, transactional configuration for INV-35.

Covers INV-35-C012 (deployment profiles), C018 (offline behaviour knobs), C032
(immutable artifact vs mutable config/state), C033 (schema with secure defaults),
C034 (pre-activation validation), C035 (environment/site overrides without a
rebuild), C036 (provenance), C037 (atomic update), C038 (rollback) and C039
(secrets are never accepted in plain configuration).

Layout contract (C032): code and schemas are immutable release artifacts; the
only mutable inputs are JSON documents under ``config/`` (or an operator path)
layered ``defaults -> profile -> environment -> site``, and runtime state that
lives only in memory (see docs/operations/STATELESSNESS_DECISION.md).
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
from threading import RLock
import time
from typing import Any

from ..io_model import MAX_CHAIN, QUEUE_DEPTH
from .errors import Inv35Error
from .security import canonical, is_secret_key

CONFIG_SCHEMA_ID = "INV35_CONFIG/1"

# field -> (type, min, max, secure default)
FIELDS: dict[str, tuple[type, float | None, float | None, Any]] = {
    "queue_depth": (int, 1, QUEUE_DEPTH, QUEUE_DEPTH),
    "max_chain": (int, 1, MAX_CHAIN, MAX_CHAIN),
    "max_chain_bytes": (int, 1, 1 << 30, 1 << 20),
    "max_queues_per_tenant": (int, 1, 1024, 16),
    "host_descriptor_capacity": (int, 1, 1 << 24, 4096),
    "tenant_share": (float, 0.001, 1.0, 0.25),
    "submit_rate_per_s": (float, 1.0, 1e9, 200000.0),
    "submit_burst": (float, 1.0, 1e9, 4096.0),
    "notification_suppression": (bool, None, None, True),
    "require_capability": (bool, None, None, True),
    "single_use_capabilities": (bool, None, None, False),
    "stall_threshold_s": (float, 0.001, 600.0, 0.5),
    "breaker_threshold": (int, 1, 1000, 8),
    "breaker_cooldown_s": (float, 0.01, 600.0, 1.0),
    "offline_grace_s": (float, 0.0, 86400.0, 300.0),
    "offline_policy": (str, None, None, "serve_last_good"),
    "profile": (str, None, None, "datacenter"),
    "vhost_offload": (bool, None, None, False),
    "telemetry_sample_rate": (float, 0.0, 1.0, 1.0),
}
ENUMS = {
    "offline_policy": {"serve_last_good", "freeze", "quarantine"},
    "profile": {"cloud", "datacenter", "near_edge", "far_edge"},
}
# Security-critical fields may be tightened but never relaxed by an override layer.
TIGHTEN_ONLY = {"require_capability": True, "max_chain": "min", "queue_depth": "min", "max_chain_bytes": "min"}

PROFILES: dict[str, dict[str, Any]] = {
    "cloud": {"host_descriptor_capacity": 65536, "tenant_share": 0.05, "vhost_offload": True},
    "datacenter": {"host_descriptor_capacity": 16384, "tenant_share": 0.10, "vhost_offload": True},
    "near_edge": {"host_descriptor_capacity": 4096, "tenant_share": 0.25, "offline_grace_s": 1800.0},
    "far_edge": {
        "host_descriptor_capacity": 1024, "tenant_share": 0.5, "queue_depth": 32,
        "offline_grace_s": 86400.0, "telemetry_sample_rate": 0.1, "submit_rate_per_s": 20000.0,
    },
}


def defaults() -> dict[str, Any]:
    return {name: spec[3] for name, spec in FIELDS.items()}


def validate(doc: object) -> dict[str, Any]:
    """Validate a *complete* effective configuration; raise INV35-E500/E504 on any defect."""
    if not isinstance(doc, dict):
        raise Inv35Error("INV35-E500", "configuration must be an object")
    for key in doc:
        if is_secret_key(key):
            raise Inv35Error("INV35-E504", f"field {key!r} looks like secret material")
        if key not in FIELDS:
            raise Inv35Error("INV35-E500", f"unknown field {key!r}")
    missing = set(FIELDS) - set(doc)
    if missing:
        raise Inv35Error("INV35-E500", f"missing fields {sorted(missing)}")
    for key, (typ, lo, hi, _default) in FIELDS.items():
        value = doc[key]
        if typ is float and isinstance(value, int) and not isinstance(value, bool):
            value = float(value)
            doc[key] = value
        if type(value) is not typ:
            raise Inv35Error("INV35-E500", f"{key} must be {typ.__name__}")
        if lo is not None and not (lo <= value <= hi):
            raise Inv35Error("INV35-E500", f"{key}={value} outside [{lo}, {hi}]")
        if key in ENUMS and value not in ENUMS[key]:
            raise Inv35Error("INV35-E500", f"{key}={value!r} not in {sorted(ENUMS[key])}")
    if doc["submit_burst"] > doc["submit_rate_per_s"]:
        raise Inv35Error("INV35-E500", "submit_burst must not exceed one second of rate")
    return doc


def merge(layers: list[tuple[str, dict[str, Any]]]) -> dict[str, Any]:
    """Merge override layers onto defaults; security fields may only tighten."""
    effective = defaults()
    for name, layer in layers:
        if not isinstance(layer, dict):
            raise Inv35Error("INV35-E500", f"layer {name} must be an object")
        for key, value in layer.items():
            if is_secret_key(key):
                raise Inv35Error("INV35-E504", f"layer {name}: {key!r}")
            rule = TIGHTEN_ONLY.get(key)
            if rule is True and value is not True:
                raise Inv35Error("INV35-E500", f"layer {name} may not relax {key}")
            if rule == "min" and isinstance(value, (int, float)) and key in effective and value > effective[key]:
                raise Inv35Error("INV35-E500", f"layer {name} may not raise {key} above {effective[key]}")
            effective[key] = value
    return effective


@dataclass(frozen=True)
class ConfigSnapshot:
    generation: int
    values: dict[str, Any]
    digest: str
    provenance: dict[str, Any]


def digest_of(values: dict[str, Any]) -> str:
    return hashlib.sha256(canonical(values)).hexdigest()


def build(*, profile: str = "datacenter", environment: dict[str, Any] | None = None,
          site: dict[str, Any] | None = None, source: str = "inline", author: str = "unknown") -> tuple[dict[str, Any], dict[str, Any]]:
    if profile not in PROFILES:
        raise Inv35Error("INV35-E500", f"unknown profile {profile!r}")
    layers = [("profile", {**PROFILES[profile], "profile": profile}),
              ("environment", environment or {}), ("site", site or {})]
    values = validate(merge(layers))
    provenance = {
        "schema": CONFIG_SCHEMA_ID, "source": source, "author": author, "profile": profile,
        "layers": [{"name": n, "digest": hashlib.sha256(canonical(l)).hexdigest()} for n, l in layers],
        "digest": digest_of(values), "built_at": time.time(),
    }
    return values, provenance


@dataclass
class ConfigStore:
    """Holds the active snapshot plus a bounded last-known-good history."""

    history_limit: int = 8
    history: list[ConfigSnapshot] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def __post_init__(self) -> None:
        values, prov = build(source="secure-defaults", author="release")
        self.history.append(ConfigSnapshot(1, values, prov["digest"], prov))

    @property
    def active(self) -> ConfigSnapshot:
        return self.history[-1]

    def apply(self, values: dict[str, Any], provenance: dict[str, Any], *,
              expected_digest: str | None = None, expected_generation: int | None = None) -> ConfigSnapshot:
        """Validate fully, then swap atomically; any failure leaves the active snapshot untouched."""
        candidate = validate(copy.deepcopy(values))
        digest = digest_of(candidate)
        if provenance.get("digest") != digest or (expected_digest is not None and expected_digest != digest):
            raise Inv35Error("INV35-E501", "provenance digest does not match candidate")
        with self._lock:
            if expected_generation is not None and expected_generation != self.active.generation:
                raise Inv35Error("INV35-E500", "concurrent update: generation moved")
            snap = ConfigSnapshot(self.active.generation + 1, candidate, digest, dict(provenance))
            self.history.append(snap)
            del self.history[:-self.history_limit]
            return snap

    def rollback(self, *, to_generation: int | None = None) -> ConfigSnapshot:
        with self._lock:
            if len(self.history) < 2:
                raise Inv35Error("INV35-E500", "no previous configuration to roll back to")
            if to_generation is None:
                target = self.history[-2]
            else:
                matches = [s for s in self.history if s.generation == to_generation]
                if not matches:
                    raise Inv35Error("INV35-E500", f"generation {to_generation} not retained")
                target = matches[0]
            prov = {**target.provenance, "rollback_of": self.active.generation, "rolled_back_at": time.time()}
            snap = ConfigSnapshot(self.active.generation + 1, dict(target.values), target.digest, prov)
            self.history.append(snap)
            del self.history[:-self.history_limit]
            return snap


def load_file(path: str | Path, *, profile: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load an operator override document ``{"profile":..,"environment":{..},"site":{..}}``."""
    raw = Path(path).read_bytes()
    try:
        doc = json.loads(raw)
    except ValueError as exc:
        raise Inv35Error("INV35-E500", f"{path}: not JSON") from exc
    if not isinstance(doc, dict) or set(doc) - {"profile", "environment", "site", "author"}:
        raise Inv35Error("INV35-E500", f"{path}: unexpected top-level keys")
    return build(profile=profile or doc.get("profile", "datacenter"), environment=doc.get("environment"),
                 site=doc.get("site"), source=f"{Path(path).name}#sha256:{hashlib.sha256(raw).hexdigest()}",
                 author=str(doc.get("author", "unknown")))


def json_schema() -> dict[str, Any]:
    props: dict[str, Any] = {}
    for key, (typ, lo, hi, default) in FIELDS.items():
        entry: dict[str, Any] = {"type": {int: "integer", float: "number", bool: "boolean", str: "string"}[typ],
                                 "default": default}
        if lo is not None:
            entry.update(minimum=lo, maximum=hi)
        if key in ENUMS:
            entry["enum"] = sorted(ENUMS[key])
        props[key] = entry
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": CONFIG_SCHEMA_ID,
            "type": "object", "additionalProperties": False, "required": sorted(FIELDS), "properties": props}
