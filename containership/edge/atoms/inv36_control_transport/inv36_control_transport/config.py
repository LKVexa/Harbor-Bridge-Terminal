"""Runtime configuration subsystem (MC-08).

* Versioned schema (``inv36.config/1``) with strict units and ranges; unknown
  fields are rejected (MC-08.001/.006/.007).
* Secure production defaults; development-only toggles are labelled and
  refused in ``prod`` (MC-08.003).
* Deterministic overlays: ``defaults < base < environment < site < node``
  (MC-08.004).  Merge is key-wise and order-independent of dict iteration.
* Secrets appear only as ``secretref://`` handles (MC-08.005).
* Validation happens before activation; activation builds an immutable
  snapshot and swaps one reference under a lock, so readers see old or new,
  never a mix (MC-08.011/.012).  ``validate_only`` gives dry-run (MC-08.014).
* Provenance, bounded known-good history, operator rollback, automatic rollback
  on failed post-activation health, and refusal to roll back to revoked
  configurations (MC-08.016-.021).
* Optional durable activation: the snapshot is written ``tmp -> fsync ->
  rename`` so a crash leaves either the old or the new complete file
  (MC-08.026).
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import pathlib
import threading
import time
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Callable, Mapping

from .errors import ErrorCode, Inv36Error
from .keys import SECRET_REF_RE
from .transport import MAX_FRAME

SCHEMA = "inv36.config/1"
MAX_CONFIG_BYTES = 64 * 1024
ENVIRONMENTS = ("dev", "test", "stage", "prod")


class ConfigError(Inv36Error, ValueError):
    code = ErrorCode.CONFIG_INVALID


# field -> (type, min, max, unit, hot_reloadable, description)
FIELDS: dict[str, tuple[type, Any, Any, str, bool, str]] = {
    "environment": (str, None, None, "enum", False, "dev|test|stage|prod key namespace"),
    "site": (str, None, None, "id", False, "site identifier"),
    "node": (str, None, None, "id", False, "node identifier"),
    "listen_port": (int, 1024, 65535, "port", False, "vsock listen port"),
    "peer_cid": (int, 2, 0xFFFFFFFE, "cid", False, "peer context id (host=2)"),
    "max_frame_bytes": (int, 1, MAX_FRAME, "bytes", False, "plaintext ceiling <= protocol maximum"),
    "max_sessions": (int, 1, 65536, "count", True, "concurrent session limit per process"),
    "max_sessions_per_tenant": (int, 1, 65536, "count", True, "per-tenant session limit"),
    "accept_rate_per_s": (float, 0.1, 10000.0, "1/s", True, "accept admission rate"),
    "send_queue_high_water": (int, 2, 1 << 20, "frames", True, "send queue high-water mark"),
    "send_queue_low_water": (int, 1, 1 << 20, "frames", True, "send queue low-water mark"),
    "connect_timeout_ms": (int, 10, 60000, "ms", True, "connect deadline"),
    "handshake_timeout_ms": (int, 50, 60000, "ms", True, "handshake deadline"),
    "read_timeout_ms": (int, 10, 600000, "ms", True, "per-record read deadline"),
    "write_timeout_ms": (int, 10, 600000, "ms", True, "per-record write deadline"),
    "heartbeat_interval_ms": (int, 100, 600000, "ms", True, "heartbeat interval"),
    "stall_threshold_ms": (int, 200, 3600000, "ms", True, "no-progress stall threshold"),
    "retry_max_attempts": (int, 1, 20, "count", True, "retry attempts"),
    "retry_base_ms": (int, 1, 60000, "ms", True, "backoff base"),
    "retry_cap_ms": (int, 1, 600000, "ms", True, "backoff cap"),
    "session_max_age_s": (int, 60, 86400 * 7, "s", True, "rekey (re-handshake) after this age"),
    "session_max_frames": (int, 1000, 1 << 62, "frames", True, "rekey after this many frames"),
    "auth_failure_limit": (int, 1, 1000, "count", True, "auth failures before a peer is isolated"),
    "breaker_failure_threshold": (int, 1, 1000, "count", True, "circuit breaker failures to open"),
    "breaker_reset_ms": (int, 100, 3600000, "ms", True, "circuit breaker open duration"),
    "identity_key_ref": (str, None, None, "secretref", False, "identity signing key handle"),
    "policy_ref": (str, None, None, "uri", True, "authorization policy source"),
    "telemetry_endpoint": (str, None, None, "uri", True, "telemetry export endpoint (https://)"),
    "telemetry_buffer": (int, 16, 1 << 20, "events", True, "bounded exporter buffer"),
    "log_level": (str, None, None, "enum", True, "debug|info|warning|error"),
    "feature_flags": (dict, None, None, "map", True, "boolean feature flags"),
    "dev_allow_insecure_test_keys": (bool, None, None, "bool", False, "DEV ONLY - refused in prod/stage"),
}
DEV_ONLY = {"dev_allow_insecure_test_keys"}
KNOWN_FLAGS = {"relay_history": False, "explain_endpoint": True, "trace_propagation": True}

DEFAULTS: dict[str, Any] = {
    "environment": "prod", "site": "default", "node": "node-0", "listen_port": 5036, "peer_cid": 2,
    "max_frame_bytes": MAX_FRAME, "max_sessions": 256, "max_sessions_per_tenant": 64, "accept_rate_per_s": 50.0,
    "send_queue_high_water": 256, "send_queue_low_water": 64, "connect_timeout_ms": 2000,
    "handshake_timeout_ms": 5000, "read_timeout_ms": 30000, "write_timeout_ms": 10000,
    "heartbeat_interval_ms": 5000, "stall_threshold_ms": 20000, "retry_max_attempts": 5, "retry_base_ms": 50,
    "retry_cap_ms": 5000, "session_max_age_s": 3600, "session_max_frames": 1 << 32, "auth_failure_limit": 5,
    "breaker_failure_threshold": 5, "breaker_reset_ms": 10000, "identity_key_ref": "secretref://prod/inv36/identity",
    "policy_ref": "policy://inv36/default", "telemetry_endpoint": "https://telemetry.invalid/v1",
    "telemetry_buffer": 4096, "log_level": "info", "feature_flags": dict(KNOWN_FLAGS),
    "dev_allow_insecure_test_keys": False,
}
_SECRETISH = ("password", "secret", "private_key", "token", "shared")


def _digest(obj: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def merge(*layers: Mapping[str, Any] | None) -> dict[str, Any]:
    """Deterministic precedence: later layers win key-wise; feature_flags merge by key."""
    out: dict[str, Any] = copy.deepcopy(DEFAULTS)
    for layer in layers:
        for k in sorted(layer or {}):
            v = (layer or {})[k]
            if k == "feature_flags" and isinstance(v, Mapping):
                out[k] = {**out.get(k, {}), **{fk: v[fk] for fk in sorted(v)}}
            else:
                out[k] = copy.deepcopy(v)
    return out


def validate(cfg: Mapping[str, Any]) -> dict[str, Any]:
    raw = json.dumps(cfg, sort_keys=True, default=str)
    if len(raw) > MAX_CONFIG_BYTES:
        raise ConfigError("configuration above size bound")
    unknown = set(cfg) - set(FIELDS)
    if unknown:
        raise ConfigError("unknown configuration fields", detail={"fields": ",".join(sorted(unknown))[:200]})
    missing = set(FIELDS) - set(cfg)
    if missing:
        raise ConfigError("missing configuration fields", detail={"fields": ",".join(sorted(missing))[:200]})
    for k, (typ, lo, hi, unit, _hot, _d) in FIELDS.items():
        v = cfg[k]
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if typ is int and isinstance(v, bool) or not isinstance(v, typ):
            raise ConfigError(f"{k} has wrong type", detail={"field": k, "unit": unit})
        if lo is not None and not lo <= v <= hi:
            raise ConfigError(f"{k} out of range", detail={"field": k, "min": lo, "max": hi, "unit": unit})
    for k, v in cfg.items():
        if any(s in k.lower() for s in _SECRETISH):
            raise ConfigError("secret-like field in ordinary configuration", detail={"field": k})
        if isinstance(v, str) and ("-----BEGIN" in v or "PRIVATE KEY" in v):
            raise ConfigError("key material in configuration", detail={"field": k})
    env = cfg["environment"]
    if env not in ENVIRONMENTS:
        raise ConfigError("unknown environment")
    for k in ("site", "node"):
        if not cfg[k] or len(cfg[k]) > 64 or not all(c.isalnum() or c in "-_." for c in cfg[k]):
            raise ConfigError(f"{k} identifier invalid", detail={"field": k})
    m = SECRET_REF_RE.match(cfg["identity_key_ref"])
    if not m:
        raise ConfigError("identity_key_ref must be a secretref:// handle")
    if m["ns"] != env:
        raise ConfigError("identity key namespace must equal environment", detail={"ns": m["ns"], "env": env})
    if ".." in cfg["identity_key_ref"] or ".." in cfg["policy_ref"]:
        raise ConfigError("path traversal in reference")
    if not cfg["policy_ref"].startswith("policy://"):
        raise ConfigError("policy_ref must use policy://")
    if env in ("prod", "stage") and not cfg["telemetry_endpoint"].startswith("https://"):
        raise ConfigError("telemetry endpoint must be https in prod/stage")
    if cfg["log_level"] not in ("debug", "info", "warning", "error"):
        raise ConfigError("invalid log_level")
    if env in ("prod", "stage") and cfg["log_level"] == "debug":
        raise ConfigError("debug logging is development-only")
    for flag, val in cfg["feature_flags"].items():
        if flag not in KNOWN_FLAGS or not isinstance(val, bool):
            raise ConfigError("unknown or non-boolean feature flag", detail={"flag": str(flag)[:32]})
    if env in ("prod", "stage") and any(cfg[k] for k in DEV_ONLY):
        raise ConfigError("development-only setting enabled outside dev/test")
    # cross-field semantics (MC-08.009)
    if cfg["send_queue_high_water"] <= cfg["send_queue_low_water"]:
        raise ConfigError("send_queue_high_water must exceed send_queue_low_water")
    if cfg["max_sessions_per_tenant"] > cfg["max_sessions"]:
        raise ConfigError("per-tenant session limit exceeds process limit")
    if cfg["retry_cap_ms"] < cfg["retry_base_ms"]:
        raise ConfigError("retry_cap_ms below retry_base_ms")
    if cfg["stall_threshold_ms"] <= 2 * cfg["heartbeat_interval_ms"]:
        raise ConfigError("stall threshold must exceed two heartbeat intervals")
    if cfg["handshake_timeout_ms"] < cfg["connect_timeout_ms"] // 4:
        raise ConfigError("handshake timeout implausibly small relative to connect timeout")
    return dict(cfg)


def restart_required(old: Mapping[str, Any], new: Mapping[str, Any]) -> list[str]:
    return sorted(k for k in FIELDS if not FIELDS[k][4] and old.get(k) != new.get(k))


@dataclass(frozen=True)
class Snapshot:
    version: int
    digest: str
    values: Mapping[str, Any]
    source: str
    author: str
    approval: str
    activated_at: float
    scope: str

    def get(self, key: str) -> Any:
        return self.values[key]

    def provenance(self) -> dict:
        return {"version": self.version, "digest": self.digest, "source": self.source, "author": self.author,
                "approval": self.approval, "activated_at": self.activated_at, "scope": self.scope}


@dataclass
class ConfigStore:
    history_limit: int = 8
    persist_path: pathlib.Path | None = None
    authorize: Callable[[str], bool] = lambda actor: True
    audit: Callable[[str, dict], None] | None = None
    clock: Callable[[], float] = time.time
    _current: Snapshot | None = field(default=None, init=False)
    _history: list[Snapshot] = field(default_factory=list, init=False)
    _revoked: set[str] = field(default_factory=set, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)
    _version: int = field(default=0, init=False)

    def _emit(self, ev: str, **data) -> None:
        if self.audit:
            self.audit(ev, data)

    @property
    def current(self) -> Snapshot:
        snap = self._current  # single reference read: atomic w.r.t. activation
        if snap is None:
            raise ConfigError("no configuration active")
        return snap

    def validate_only(self, *layers: Mapping[str, Any] | None) -> dict:
        cfg = validate(merge(*layers))
        return {"valid": True, "digest": _digest(cfg),
                "restart_required": restart_required(self._current.values, cfg) if self._current else []}

    def activate(self, *layers: Mapping[str, Any] | None, source: str, author: str, approval: str = "",
                 scope: str = "process", expected_version: int | None = None,
                 health_check: Callable[[Snapshot], bool] | None = None) -> Snapshot:
        if not self.authorize(author):
            self._emit("config.validation_failed", author=author, reason="unauthorized")
            raise ConfigError("actor not authorized to activate configuration", code=ErrorCode.CONFIG_UNAUTHORIZED)
        try:
            cfg = validate(merge(*layers))
        except ConfigError as exc:
            self._emit("config.validation_failed", author=author, reason=str(exc)[:128])
            raise
        digest = _digest(cfg)
        if digest in self._revoked:
            raise ConfigError("configuration digest is revoked", code=ErrorCode.CONFIG_ROLLBACK_DENIED)
        with self._lock:
            if expected_version is not None and expected_version != self._version:
                raise ConfigError("concurrent configuration change", code=ErrorCode.CONFIG_CONFLICT)
            previous = self._current
            self._version += 1
            snap = Snapshot(self._version, digest, MappingProxyType(copy.deepcopy(cfg)), source[:256], author[:128],
                            approval[:128], self.clock(), scope[:64])
            self._persist(snap)
            self._current = snap
            if previous is not None:
                self._history.append(previous)
                del self._history[:-self.history_limit]
        self._emit("config.activate", **snap.provenance(),
                   restart_required=restart_required(previous.values, cfg) if previous else [])
        if health_check is not None:
            try:
                ok = bool(health_check(snap))
            except Exception:  # noqa: BLE001 - failing health check is a signal, not a crash
                ok = False
            if not ok and previous is not None:
                self._rollback_to(previous, actor="auto-rollback", reason="post-activation health check failed")
                raise ConfigError("activation failed health check; rolled back",
                                  detail={"rolled_back_to": previous.version})
        return snap

    def _persist(self, snap: Snapshot) -> None:
        if not self.persist_path:
            return
        doc = {"schema": SCHEMA, **snap.provenance(), "values": dict(snap.values)}
        body = json.dumps(doc, sort_keys=True)
        doc_digest = hashlib.sha256(body.encode()).hexdigest()
        tmp = self.persist_path.with_suffix(".tmp")
        with open(tmp, "w") as fh:
            fh.write(json.dumps({"sha256": doc_digest, "doc": doc}, sort_keys=True))
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.persist_path)

    @classmethod
    def recover(cls, path: pathlib.Path, **kw) -> "ConfigStore":
        store = cls(persist_path=path, **kw)
        tmp = path.with_suffix(".tmp")
        if tmp.exists():
            tmp.unlink()  # incomplete activation: discard, old complete snapshot remains
        if path.exists():
            wrapper = json.loads(path.read_text())
            doc = wrapper["doc"]
            if hashlib.sha256(json.dumps(doc, sort_keys=True).encode()).hexdigest() != wrapper["sha256"]:
                raise ConfigError("persisted configuration corrupt")
            values = validate(doc["values"])
            store._version = int(doc["version"])
            store._current = Snapshot(doc["version"], doc["digest"], MappingProxyType(values), doc["source"],
                                      doc["author"], doc["approval"], doc["activated_at"], doc["scope"])
        return store

    def revoke(self, digest: str, *, actor: str) -> None:
        self._revoked.add(digest)
        self._emit("config.revoke", digest=digest, actor=actor)

    def _rollback_to(self, target: Snapshot, *, actor: str, reason: str) -> Snapshot:
        with self._lock:
            self._version += 1
            snap = Snapshot(self._version, target.digest, target.values, f"rollback:{target.version}", actor,
                            reason[:128], self.clock(), target.scope)
            self._persist(snap)
            if self._current is not None:
                self._history.append(self._current)
                del self._history[:-self.history_limit]
            self._current = snap
        self._emit("config.rollback", to_version=target.version, actor=actor, reason=reason)
        return snap

    def rollback(self, version: int, *, actor: str, reason: str) -> Snapshot:
        if not self.authorize(actor):
            raise ConfigError("actor not authorized to roll back", code=ErrorCode.CONFIG_UNAUTHORIZED)
        target = next((s for s in reversed(self._history) if s.version == version), None)
        if target is None:
            self._emit("config.rollback_denied", version=version, reason="not in known-good history")
            raise ConfigError("version not in rollback history", code=ErrorCode.CONFIG_ROLLBACK_DENIED)
        if target.digest in self._revoked:
            self._emit("config.rollback_denied", version=version, reason="revoked")
            raise ConfigError("rollback target is revoked", code=ErrorCode.CONFIG_ROLLBACK_DENIED)
        return self._rollback_to(target, actor=actor, reason=reason)

    def history(self) -> list[dict]:
        return [s.provenance() for s in self._history]


def dev_profile(**over: Any) -> dict:
    """Convenience overlay for tests (test namespace)."""
    base = {"environment": "test", "identity_key_ref": "secretref://test/inv36/identity",
            "telemetry_endpoint": "http://127.0.0.1:0/none"}
    base.update(over)
    return base
