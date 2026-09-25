"""Production configuration subsystem (MC-016).

* Declarative config validated against ``PLN01_CONFIG/1``.
* Immutable artifact defaults (``DEFAULTS``) are separate from mutable,
  layered overlays: base -> environment -> site.  Later layers win key by key.
* Every activated configuration carries provenance: author, source of each
  layer, activation timestamp, and a content digest.  Activated configs are
  frozen (``types.MappingProxyType``) and never mutated in place.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from hashlib import sha256
from types import MappingProxyType
from typing import Any, Mapping

from .errors import ConfigError
from .validation import errors as schema_errors

DEFAULTS: dict[str, Any] = {
    "schema": "PLN01_CONFIG/1",
    "limits": {"max_nodes": 10_000, "max_dependencies_per_node": 256, "max_spec_bytes": 1_048_576,
               "max_history": 64, "replay_window": 4096, "max_audit_events": 8192},
    "quotas": {"tenant_rate_per_second": 50.0, "tenant_burst": 100, "tenant_max_nodes": 5_000,
               "max_concurrent_requests": 64, "max_queue_depth": 256},
    "timeouts": {"request_deadline_seconds": 5.0, "retry_max_attempts": 4, "retry_base_seconds": 0.05,
                 "retry_cap_seconds": 2.0, "circuit_failure_threshold": 5, "circuit_reset_seconds": 30.0},
    "security": {"require_authentication": True, "require_artifact_verification": True, "reject_secrets": True},
    "sites": {},
    "telemetry": {"log_level": "INFO", "audit_retention_days": 400, "trace_sample_ratio": 0.1},
    "storage": {"fsync": True, "snapshot_every": 256},
}
DEFAULT_STALENESS = {"cloud": 60.0, "datacenter": 120.0, "near-edge": 600.0, "far-edge": 3600.0}


def _merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    out = json.loads(json.dumps(base))
    for key, value in overlay.items():
        if isinstance(value, Mapping) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = json.loads(json.dumps(value))
    return out


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({k: _freeze(v) for k, v in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(v) for v in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: _thaw(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return [_thaw(v) for v in value]
    return value


@dataclass(frozen=True)
class ActiveConfig:
    values: Mapping[str, Any]
    digest: str
    author: str
    activated_at: float
    layers: tuple[str, ...]
    previous_digest: str | None = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    def get(self, section: str, key: str) -> Any:
        return self.values[section][key]

    def provenance(self) -> dict[str, Any]:
        return {"digest": self.digest, "author": self.author, "activated_at": self.activated_at,
                "layers": list(self.layers), "previous_digest": self.previous_digest}

    def as_dict(self) -> dict[str, Any]:
        return _thaw(self.values)

    def staleness_for(self, site: str) -> float:
        entry = self.values["sites"].get(site)
        if entry is None:
            return DEFAULT_STALENESS["cloud"]
        return entry.get("staleness_seconds", DEFAULT_STALENESS[entry["context"]])

    def context_for(self, site: str) -> str:
        entry = self.values["sites"].get(site)
        return "cloud" if entry is None else entry["context"]


def build_config(
    layers: list[tuple[str, Mapping[str, Any]]] | None = None,
    *,
    author: str,
    previous: ActiveConfig | None = None,
    now: float | None = None,
) -> ActiveConfig:
    """Merge named overlay layers over immutable defaults, validate, and freeze."""
    if not isinstance(author, str) or not author.strip():
        raise ConfigError("config activation requires a non-empty author")
    merged: dict[str, Any] = _merge(DEFAULTS, {})
    names = ["defaults"]
    for name, overlay in layers or []:
        if not isinstance(overlay, Mapping):
            raise ConfigError(f"config layer {name!r} must be a mapping")
        merged = _merge(merged, overlay)
        names.append(name)
    problems = schema_errors(merged, "PLN01_CONFIG/1")
    if problems:
        raise ConfigError("invalid configuration: " + "; ".join(problems[:10]))
    q, t = merged["quotas"], merged["timeouts"]
    if q["tenant_max_nodes"] > merged["limits"]["max_nodes"]:
        raise ConfigError("quotas.tenant_max_nodes may not exceed limits.max_nodes")
    if t["retry_base_seconds"] > t["retry_cap_seconds"]:
        raise ConfigError("timeouts.retry_base_seconds may not exceed retry_cap_seconds")
    digest = sha256(json.dumps(merged, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return ActiveConfig(values=_freeze(merged), digest=digest, author=author.strip(),
                        activated_at=time.time() if now is None else now, layers=tuple(names),
                        previous_digest=previous.digest if previous else None)


def load_layer(path: str) -> tuple[str, dict[str, Any]]:
    with open(path, encoding="utf-8") as handle:
        return path, json.load(handle)
