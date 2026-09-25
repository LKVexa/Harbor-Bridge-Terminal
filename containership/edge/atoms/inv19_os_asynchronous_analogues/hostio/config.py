"""MC-14 - Production configuration system (PK_ASYNC_CONFIG/1).

Precedence (lowest -> highest, deterministic):
  compiled defaults < site file < environment (INV19_*) < tenant/workload overrides < command line

Values are parsed into an immutable candidate, validated as a whole (types,
min/max, unknown critical fields rejected, secrets refused), then activated by
an atomic reference swap.  The prior known-good config is kept for rollback.
Provenance records source, version, sha256 digest, activation time and actor,
never secret values.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

SCHEMA = "PK_ASYNC_CONFIG/1"

# field: (type, default, min, max, dynamic, critical)
FIELDS: dict[str, tuple[type, Any, Any, Any, bool, bool]] = {
    "backends.enabled": (list, ["io_uring", "iocp", "epoll", "kqueue", "portable"], None, None, False, True),
    "backends.disabled": (list, [], None, None, True, True),
    "backends.diagnostic_override": (str, "", None, None, False, True),
    "ring.sq_entries": (int, 256, 1, 32768, False, True),
    "ring.cq_entries": (int, 512, 2, 65536, False, True),
    "ring.sqpoll": (bool, False, None, None, False, False),
    "ring.registered_buffers": (bool, False, None, None, False, False),
    "ring.registered_files": (bool, False, None, None, False, False),
    "quota.global_descriptors": (int, 4096, 1, 1 << 20, True, True),
    "quota.per_tenant_descriptors": (int, 1024, 1, 1 << 20, True, True),
    "quota.per_workload_descriptors": (int, 256, 1, 1 << 20, True, True),
    "quota.max_inflight": (int, 4096, 1, 1 << 20, True, True),
    "quota.max_event_batch": (int, 256, 1, 65536, True, True),
    "quota.buffer_bytes_global": (int, 256 << 20, 4096, 1 << 40, True, True),
    "quota.buffer_bytes_per_tenant": (int, 64 << 20, 4096, 1 << 40, True, True),
    "quota.buffer_bytes_per_workload": (int, 32 << 20, 4096, 1 << 40, True, True),
    "timeout.default_s": (float, 30.0, 0.001, 86400.0, True, True),
    "retry.max_attempts": (int, 5, 0, 32, True, True),
    "retry.budget_s": (float, 10.0, 0.0, 3600.0, True, True),
    "retry.base_s": (float, 0.005, 0.0001, 10.0, True, False),
    "retry.cap_s": (float, 1.0, 0.001, 60.0, True, False),
    "breaker.failure_threshold": (int, 20, 1, 100000, True, False),
    "breaker.open_s": (float, 5.0, 0.01, 3600.0, True, False),
    "observability.log_level": (str, "INFO", None, None, True, False),
    "observability.trace_sample": (float, 0.01, 0.0, 1.0, True, False),
    "security.require_capabilities": (bool, True, None, None, False, True),
    "security.key_ref": (str, "kms://inv19/capability-mac", None, None, False, True),
    "audit.max_buffer": (int, 4096, 16, 1 << 20, False, True),
    "audit.checkpoint_every": (int, 64, 1, 100000, False, False),
    "health.stall_s": (float, 2.0, 0.01, 600.0, True, False),
    "health.max_recoveries": (int, 3, 0, 100, True, True),
}
_ENUMS = {"observability.log_level": {"DEBUG", "INFO", "WARNING", "ERROR"}}
_BACKENDS = {"io_uring", "iocp", "epoll", "kqueue", "portable"}
_SECRETY = ("password", "secret", "token", "private_key")


class ConfigError(ValueError):
    def __init__(self, errors: list[str]) -> None:
        super().__init__("; ".join(errors))
        self.errors = errors


@dataclass(frozen=True)
class Config:
    values: Mapping[str, Any]
    version: int
    digest: str
    source: tuple[str, ...]
    actor: str
    activated_at: float

    def __getitem__(self, k: str) -> Any:
        return self.values[k]

    def provenance(self) -> dict:
        return {"schema": SCHEMA, "version": self.version, "digest": self.digest,
                "source": list(self.source), "actor": self.actor, "activated_at": self.activated_at}


def defaults() -> dict[str, Any]:
    return {k: (list(v[1]) if isinstance(v[1], list) else v[1]) for k, v in FIELDS.items()}


def _coerce(key: str, raw: Any) -> Any:
    typ = FIELDS[key][0]
    if typ is bool:
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str) and raw.lower() in ("1", "true", "yes", "0", "false", "no"):
            return raw.lower() in ("1", "true", "yes")
        raise TypeError
    if typ is int:
        if isinstance(raw, bool):
            raise TypeError
        if isinstance(raw, float):
            if raw != raw or raw in (float("inf"), float("-inf")) or not raw.is_integer():
                raise ValueError("non-integral number")  # never truncate silently
            return int(raw)
        if isinstance(raw, str):
            return int(raw.strip(), 10)
        if not isinstance(raw, int):
            raise TypeError
        return raw
    if typ is float:
        if isinstance(raw, bool) or not isinstance(raw, (int, float, str)):
            raise TypeError
        v = float(raw)
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("non-finite")
        return v
    if typ is list:
        if isinstance(raw, str):
            return [s.strip() for s in raw.split(",") if s.strip()]
        if not isinstance(raw, list):
            raise TypeError
        return list(raw)
    if not isinstance(raw, str):
        raise TypeError
    return raw


def validate(values: dict[str, Any]) -> list[str]:
    errs = []
    for k, v in values.items():
        if k not in FIELDS:
            errs.append(f"unknown field {k}")
            continue
        typ, _, lo, hi, _, _ = FIELDS[k]
        if typ is float and isinstance(v, float) and v != v:
            errs.append(f"{k}: NaN")
        if lo is not None and v < lo:
            errs.append(f"{k}: {v} < {lo}")
        if hi is not None and v > hi:
            errs.append(f"{k}: {v} > {hi}")
        if k in _ENUMS and v not in _ENUMS[k]:
            errs.append(f"{k}: {v!r} not in {sorted(_ENUMS[k])}")
    for k in ("backends.enabled", "backends.disabled"):
        bad = set(values.get(k, [])) - _BACKENDS
        if bad:
            errs.append(f"{k}: unknown backends {sorted(bad)}")
    if "portable" in values.get("backends.disabled", []):
        errs.append("backends.disabled: the portable fallback cannot be disabled")
    if values.get("ring.cq_entries", 2) < values.get("ring.sq_entries", 1):
        errs.append("ring.cq_entries must be >= ring.sq_entries")
    q = values
    if not (q.get("quota.per_workload_descriptors", 1) <= q.get("quota.per_tenant_descriptors", 1)
            <= q.get("quota.global_descriptors", 1)):
        errs.append("quota: per_workload <= per_tenant <= global violated")
    if not (q.get("quota.buffer_bytes_per_workload", 1) <= q.get("quota.buffer_bytes_per_tenant", 1)
            <= q.get("quota.buffer_bytes_global", 1)):
        errs.append("quota: buffer bytes per_workload <= per_tenant <= global violated")
    if values.get("retry.cap_s", 1) < values.get("retry.base_s", 0):
        errs.append("retry.cap_s < retry.base_s")
    kr = values.get("security.key_ref", "")
    if not kr.startswith(("kms://", "env-ref://", "file-ref://")):
        errs.append("security.key_ref must be a key reference, never key material")
    return errs


def merge_layers(layers: list[tuple[str, dict[str, Any]]]) -> tuple[dict[str, Any], list[str]]:
    vals = defaults()
    errs: list[str] = []
    for name, layer in layers:
        for k, raw in layer.items():
            if any(s in k.lower() for s in _SECRETY):
                errs.append(f"{name}:{k}: secret-bearing fields are not accepted in configuration")
                continue
            if k not in FIELDS:
                errs.append(f"{name}: unknown field {k}")
                continue
            try:
                vals[k] = _coerce(k, raw)
            except (TypeError, ValueError, OverflowError):
                errs.append(f"{name}:{k}: expected {FIELDS[k][0].__name__}")
    return vals, errs


def env_layer(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    environ = os.environ if environ is None else environ
    out = {}
    for k, v in environ.items():
        if k.startswith("INV19_"):
            out[k[6:].lower().replace("__", ".")] = v
    return out


def digest(values: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(values), sort_keys=True).encode()).hexdigest()


class ConfigStore:
    def __init__(self, actor: str = "bootstrap") -> None:
        self._lock = threading.Lock()
        self._active: Config | None = None
        self._previous: list[Config] = []
        self.history: list[dict] = []
        self.activate([("compiled-defaults", {})], actor=actor)

    @property
    def active(self) -> Config:
        return self._active  # type: ignore[return-value]

    def build(self, layers: list[tuple[str, dict[str, Any]]], actor: str) -> Config:
        vals, errs = merge_layers(layers)
        errs += validate(vals)
        if errs:
            raise ConfigError(errs)
        v = (self._active.version + 1) if self._active else 1
        return Config(MappingProxyType(vals), v, digest(vals),
                      tuple(["compiled-defaults"] + [n for n, _ in layers if n != "compiled-defaults"]),
                      actor, time.time())

    def restart_required(self, cand: Config) -> list[str]:
        if self._active is None:
            return []
        return [k for k, spec in FIELDS.items() if not spec[4] and cand[k] != self._active[k]]

    def activate(self, layers: list[tuple[str, dict[str, Any]]], actor: str,
                 allow_restart_fields: bool = True, on_activate=None) -> Config:
        cand = self.build(layers, actor)  # raises before any state change
        if not allow_restart_fields and self.restart_required(cand):
            raise ConfigError([f"restart-required field changed: {k}" for k in self.restart_required(cand)])
        with self._lock:
            prev = self._active
            self._active = cand
            try:
                if on_activate is not None:
                    on_activate(cand)
            except Exception as exc:
                self._active = prev  # roll back failed activation
                self.history.append({"event": "rollback", "version": cand.version, "reason": type(exc).__name__})
                raise ConfigError([f"activation hook failed: {type(exc).__name__}"]) from exc
            if prev is not None:
                self._previous.append(prev)
                del self._previous[:-16]
            self.history.append({"event": "activate", **cand.provenance()})
        return cand

    def rollback(self, actor: str) -> Config:
        with self._lock:
            if not self._previous:
                raise ConfigError(["no previous known-good configuration"])
            prev = self._previous.pop()
            self._active = prev
            self.history.append({"event": "operator-rollback", "to_version": prev.version,
                                 "digest": prev.digest, "actor": actor, "ts": time.time()})
            return prev
