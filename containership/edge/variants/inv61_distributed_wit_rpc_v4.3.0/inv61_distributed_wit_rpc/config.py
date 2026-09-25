"""M12 - declarative configuration: schema validation, overlays, secret
separation, provenance and atomic activation/rollback.

Layering order (later wins): defaults -> base file -> environment overlay ->
site overlay.  Unknown keys are rejected.  Secret-bearing settings accept only
``file:`` or ``env:`` references, never literal values.  Every activation
produces a provenance record (source digests, merged digest, actor, time).
Immutable keys cannot change without a restart.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import threading
import time
from typing import Any, Callable

SCHEMA_VERSION = "inv61-config/1"

# key: (type, min, max, mutable_at_runtime, secret_ref)
SCHEMA: dict[str, tuple[type, Any, Any, bool, bool]] = {
    "listen_host": (str, None, None, False, False),
    "listen_port": (int, 0, 65535, False, False),
    "node_id": (str, None, None, False, False),
    "max_frame_bytes": (int, 1024, 16 << 20, True, False),
    "max_connections": (int, 1, 100_000, False, False),
    "max_inflight": (int, 1, 100_000, True, False),
    "per_tenant_inflight": (int, 1, 100_000, True, False),
    "tenant_rate": (float, 0.001, 1e7, True, False),
    "tenant_burst": (float, 1.0, 1e7, True, False),
    "replay_window_ms": (int, 1000, 600_000, True, False),
    "idempotency_ttl_s": (float, 1.0, 86_400.0, True, False),
    "handshake_timeout_s": (float, 0.1, 60.0, True, False),
    "idle_timeout_s": (float, 1.0, 3600.0, True, False),
    "require_tls": (bool, None, None, False, False),
    "tls_cert": (str, None, None, False, True),
    "tls_key": (str, None, None, False, True),
    "tls_ca": (str, None, None, False, True),
    "keyring": (str, None, None, True, True),
    "audit_key": (str, None, None, False, True),
    "audit_path": (str, None, None, False, False),
    "state_path": (str, None, None, False, False),
    "log_level": (str, None, None, True, False),
    "trace_sample_rate": (float, 0.0, 1.0, True, False),
    "telemetry_export_allowlist": (list, None, None, True, False),
}

DEFAULTS: dict[str, Any] = {
    "listen_host": "127.0.0.1", "listen_port": 0, "node_id": "inv61-node",
    "max_frame_bytes": 1 << 20, "max_connections": 512, "max_inflight": 256,
    "per_tenant_inflight": 64, "tenant_rate": 500.0, "tenant_burst": 1000.0,
    "replay_window_ms": 30_000, "idempotency_ttl_s": 600.0,
    "handshake_timeout_s": 5.0, "idle_timeout_s": 120.0, "require_tls": True,
    "tls_cert": None, "tls_key": None, "tls_ca": None, "keyring": None,
    "audit_key": None, "audit_path": "audit.jsonl", "state_path": "state.json",
    "log_level": "INFO", "trace_sample_rate": 0.1, "telemetry_export_allowlist": [],
}
LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR"}


class ConfigError(ValueError):
    pass


def validate(cfg: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    for k in cfg:
        if k not in SCHEMA:
            errs.append(f"unknown key: {k}")
    for k, (typ, lo, hi, _mut, secret) in SCHEMA.items():
        v = cfg.get(k)
        if v is None:
            if secret or k in ("audit_path", "state_path"):
                continue
            errs.append(f"missing: {k}")
            continue
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if typ is int and isinstance(v, bool) or not isinstance(v, typ):
            errs.append(f"type: {k} must be {typ.__name__}")
            continue
        if lo is not None and not (lo <= v <= hi):
            errs.append(f"range: {k} must be in [{lo}, {hi}]")
        if secret and not (v.startswith("file:") or v.startswith("env:")):
            errs.append(f"secret-literal: {k} must be a file: or env: reference")
    if cfg.get("log_level") not in LOG_LEVELS:
        errs.append("range: log_level")
    if cfg.get("require_tls") and not all(cfg.get(k) for k in ("tls_cert", "tls_key", "tls_ca")):
        errs.append("require_tls needs tls_cert, tls_key and tls_ca references")
    if isinstance(cfg.get("tenant_burst"), (int, float)) and isinstance(cfg.get("tenant_rate"), (int, float)):
        if cfg["tenant_burst"] < 1:
            errs.append("range: tenant_burst")
    return errs


def resolve_secret(ref: str, base: Path | None = None) -> bytes:
    """Resolve a ``file:`` / ``env:`` reference. Values never enter config dumps."""
    if ref.startswith("env:"):
        val = os.environ.get(ref[4:])
        if val is None:
            raise ConfigError(f"secret env var not set: {ref[4:]}")
        return val.encode()
    if ref.startswith("file:"):
        p = Path(ref[5:])
        if base is not None and not p.is_absolute():
            p = base / p
        return p.read_bytes().strip()
    raise ConfigError("secret must be a reference")


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Provenance:
    schema: str
    sources: tuple[tuple[str, str], ...]   # (path/label, sha256)
    merged_digest: str
    actor: str
    activated_at: float
    generation: int

    def as_dict(self) -> dict[str, Any]:
        return {"schema": self.schema, "sources": [list(s) for s in self.sources],
                "merged_digest": self.merged_digest, "actor": self.actor,
                "activated_at": self.activated_at, "generation": self.generation}


def load_layers(*paths: str | os.PathLike) -> tuple[dict[str, Any], list[tuple[str, str]]]:
    merged = copy.deepcopy(DEFAULTS)
    sources = [("defaults", _digest(DEFAULTS))]
    for p in paths:
        raw = Path(p).read_bytes()
        doc = json.loads(raw)
        if not isinstance(doc, dict):
            raise ConfigError(f"{p}: top level must be an object")
        merged.update(doc)
        sources.append((str(p), hashlib.sha256(raw).hexdigest()))
    return merged, sources


class ConfigStore:
    """Holds the active config; activation is atomic and reversible."""

    def __init__(self, on_change: Callable[[dict[str, Any], dict[str, Any]], None] | None = None):
        self._lock = threading.Lock()
        self.active: dict[str, Any] | None = None
        self.provenance: Provenance | None = None
        self._history: list[tuple[dict[str, Any], Provenance]] = []
        self._on_change = on_change

    def activate(self, cfg: dict[str, Any], sources: list[tuple[str, str]], actor: str) -> Provenance:
        errs = validate(cfg)
        if errs:
            raise ConfigError("; ".join(errs))
        with self._lock:
            if self.active is not None:
                for k, (_t, _lo, _hi, mutable, _s) in SCHEMA.items():
                    if not mutable and self.active.get(k) != cfg.get(k):
                        raise ConfigError(f"immutable key changed at runtime: {k}")
            prov = Provenance(SCHEMA_VERSION, tuple(sources), _digest(cfg), actor, time.time(),
                              (self.provenance.generation + 1) if self.provenance else 1)
            new = copy.deepcopy(cfg)
            old = self.active
            if self._on_change is not None and old is not None:
                self._on_change(old, new)  # may raise -> activation aborted, nothing swapped
            if old is not None:
                self._history.append((old, self.provenance))
            self.active, self.provenance = new, prov
            return prov

    def rollback(self, actor: str) -> Provenance:
        with self._lock:
            if not self._history:
                raise ConfigError("no previous configuration")
            cfg, prev = self._history.pop()
            if self._on_change is not None:
                self._on_change(self.active, cfg)
            self.active = cfg
            self.provenance = Provenance(prev.schema, prev.sources, prev.merged_digest, actor,
                                         time.time(), self.provenance.generation + 1)
            return self.provenance

    def redacted(self) -> dict[str, Any]:
        out = dict(self.active or {})
        for k, spec in SCHEMA.items():
            if spec[4] and out.get(k):
                out[k] = out[k].split(":", 1)[0] + ":<redacted>"
        return out
