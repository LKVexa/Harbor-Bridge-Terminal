"""Declarative configuration lifecycle (WS 5).

Schema ``PK_INV32_CONFIG/1`` is independent of Python constructor defaults.  Layers merge in fixed
precedence ``defaults < site < environment < node < emergency``.  Rules:

* unknown keys, out-of-range values, or inline secret material are rejected;
* the same key set to *different* values by two sources in the same layer is ambiguous -> rejected;
* the ``emergency`` layer may only set keys in ``EMERGENCY_KEYS``;
* the result is an immutable ``Config`` with a SHA-256 digest of its canonical JSON;
* activation is two-phase (``stage`` validates, ``activate`` publishes with a single reference
  swap) so readers see old or new, never a mix; previous revisions are retained for rollback.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
import threading
import time
from types import MappingProxyType
from typing import Any, Callable, Mapping

from . import errors as E

CONFIG_SCHEMA = "PK_INV32_CONFIG/1"
LAYERS = ("defaults", "site", "environment", "node", "emergency")
_SECRET_REF_RE = re.compile(r"^secret://[a-z0-9][a-z0-9._/-]{0,127}$")
_INLINE_SECRET_RE = re.compile(r"(-----BEGIN|bearer\s|inv32tok\.|eyJ[A-Za-z0-9_-]{8,}\.|password=|AKIA[0-9A-Z]{12})", re.I)

# key: (type, min, max / allowed, security_critical, reloadable, default)
SCHEMA: dict[str, tuple] = {
    "host_reserve_fraction": (float, 0.05, 0.5, True, True, 0.10),
    "host_reserve_min_mib": (int, 64, 1 << 20, True, True, 512),
    "guest_default_floor_fraction": (float, 0.05, 1.0, True, True, 0.25),
    "operation_timeout_s": (float, 0.01, 600.0, False, True, 30.0),
    "provider_call_timeout_s": (float, 0.01, 600.0, False, True, 10.0),
    "retry_max_attempts": (int, 1, 10, False, True, 3),
    "retry_base_delay_s": (float, 0.001, 10.0, False, True, 0.05),
    "retry_max_delay_s": (float, 0.01, 60.0, False, True, 2.0),
    "retry_budget_ratio": (float, 0.0, 1.0, False, True, 0.2),
    "max_inflight_per_guest": (int, 1, 1, True, False, 1),  # conflicting ops per guest are serialized
    "max_inflight_per_host": (int, 1, 4096, False, True, 64),
    "max_inflight_per_tenant": (int, 1, 4096, False, True, 16),
    "max_queue_depth": (int, 0, 65536, False, True, 256),
    "max_queue_wait_s": (float, 0.0, 60.0, False, True, 1.0),
    "safety_reserved_slots": (int, 1, 64, True, True, 4),
    "tenant_rate_per_s": (float, 0.1, 100000.0, False, True, 50.0),
    "tenant_burst": (int, 1, 100000, False, True, 100),
    "circuit_failure_threshold": (int, 1, 1000, False, True, 5),
    "circuit_reset_s": (float, 0.1, 3600.0, False, True, 10.0),
    "idempotency_retention_s": (int, 3600, 30 * 86400, True, True, 7 * 86400),
    "audit_segment_max_events": (int, 16, 1_000_000, False, True, 10_000),
    "audit_anchor_interval_s": (int, 10, 86400, True, True, 300),
    "audit_retention_days": (int, 30, 3650, True, True, 400),
    "lease_duration_s": (float, 1.0, 300.0, True, False, 15.0),
    "lease_renew_s": (float, 0.5, 100.0, True, False, 5.0),
    "stall_memory_reclaim_s": (float, 0.1, 3600.0, False, True, 30.0),
    "stall_memory_grow_s": (float, 0.1, 3600.0, False, True, 10.0),
    "stall_vcpu_s": (float, 0.1, 3600.0, False, True, 5.0),
    "free_page_report_stale_s": (float, 1.0, 3600.0, False, True, 60.0),
    "telemetry_enabled": (bool, None, None, False, True, True),
    "provider_endpoint": (str, None, 256, True, False, "unix:///run/hyperflux/control.sock"),
    "provider_credential_ref": (str, None, 128, True, False, "secret://inv32/provider"),
    "authn_key_ref": (str, None, 128, True, False, "secret://inv32/authn-keyring"),
    "audit_signing_key_ref": (str, None, 128, True, False, "secret://inv32/audit-signing"),
    "state_dir": (str, None, 512, True, False, "/var/lib/inv32"),
    "feature_memory_hot_unplug": (bool, None, None, False, True, False),
    "feature_free_page_reporting": (bool, None, None, False, True, True),
    "emergency_disable": (bool, None, None, True, True, False),
    "mode": (str, ("normal", "read_only", "freeze"), None, True, True, "normal"),
}
EMERGENCY_KEYS = frozenset({"emergency_disable", "mode"})
SECRET_REF_KEYS = frozenset(k for k in SCHEMA if k.endswith("_ref"))
DEFAULTS = {k: v[5] for k, v in SCHEMA.items()}
HARDENED_PROFILE = dict(DEFAULTS)  # defaults *are* the hardened profile (reserve on, freeze-safe)


@dataclass(frozen=True)
class ConfigMeta:
    revision: str
    author: str
    source: str
    approval: str | None
    release_version: str
    created_at: float
    activated_at: float | None = None


@dataclass(frozen=True)
class Config:
    values: Mapping[str, Any]
    digest: str
    meta: ConfigMeta
    schema: str = CONFIG_SCHEMA

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def inspect(self) -> dict[str, Any]:
        """Effective config for operators; secret references are shown only as references."""
        return {"schema": self.schema, "digest": self.digest, "revision": self.meta.revision,
                "author": self.meta.author, "source": self.meta.source, "approval": self.meta.approval,
                "release_version": self.meta.release_version, "activated_at": self.meta.activated_at,
                "values": dict(self.values)}


def _check_value(key: str, value: Any) -> Any:
    if key not in SCHEMA:
        raise E.ConfigInvalid("unknown configuration key", key=key)
    typ, lo, hi, *_ = SCHEMA[key]
    if typ is float and isinstance(value, int) and not isinstance(value, bool):
        value = float(value)
    if typ is bool:
        if not isinstance(value, bool):
            raise E.ConfigInvalid("expected boolean", key=key)
        return value
    if not isinstance(value, typ) or isinstance(value, bool):
        raise E.ConfigInvalid("wrong type", key=key, expected=typ.__name__)
    if typ is str:
        if isinstance(lo, tuple) and value not in lo:
            raise E.ConfigInvalid("value not in allowed set", key=key)
        if hi is not None and len(value) > hi:
            raise E.ConfigInvalid("string too long", key=key)
        if key in SECRET_REF_KEYS and not _SECRET_REF_RE.match(value):
            raise E.ConfigInvalid("secret keys must be secret:// references", key=key)
        if _INLINE_SECRET_RE.search(value):
            raise E.ConfigInvalid("inline secret material is prohibited in configuration", key=key)
        return value
    if value != value or not lo <= value <= hi:  # NaN / range
        raise E.ConfigInvalid("value out of range", key=key, min=lo, max=hi)
    return value


def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise E.ConfigInvalid("duplicate key in configuration document", key=k)
        out[k] = v
    return out


def parse_document(text: str) -> dict[str, Any]:
    try:
        doc = json.loads(text, object_pairs_hook=_no_dupes)
    except E.ConfigInvalid:
        raise
    except ValueError:
        raise E.ConfigInvalid("configuration is not valid JSON") from None
    if not isinstance(doc, dict):
        raise E.ConfigInvalid("configuration must be an object")
    return doc


def merge(layers: Mapping[str, list[Mapping[str, Any]]]) -> dict[str, Any]:
    for name in layers:
        if name not in LAYERS:
            raise E.ConfigInvalid("unknown configuration layer", layer=name)
    merged = dict(DEFAULTS)
    for layer in LAYERS[1:]:
        seen: dict[str, Any] = {}
        for doc in layers.get(layer, []):
            for key, value in doc.items():
                value = _check_value(key, value)
                if layer == "emergency" and key not in EMERGENCY_KEYS:
                    raise E.ConfigInvalid("emergency override may not set this key", key=key)
                if key in seen and seen[key] != value:
                    raise E.ConfigInvalid("conflicting values within one layer", key=key, layer=layer)
                seen[key] = value
        merged.update(seen)
    return merged


def validate_cross_field(v: Mapping[str, Any]) -> None:
    if v["retry_base_delay_s"] > v["retry_max_delay_s"]:
        raise E.ConfigInvalid("retry_base_delay_s exceeds retry_max_delay_s")
    if v["lease_renew_s"] * 2 > v["lease_duration_s"]:
        raise E.ConfigInvalid("lease must be renewed at least twice per lease duration")
    if v["provider_call_timeout_s"] > v["operation_timeout_s"]:
        raise E.ConfigInvalid("provider timeout exceeds operation timeout")
    if v["safety_reserved_slots"] >= v["max_inflight_per_host"]:
        raise E.ConfigInvalid("safety slots must leave room for normal operations")
    if v["max_inflight_per_tenant"] > v["max_inflight_per_host"]:
        raise E.ConfigInvalid("per-tenant concurrency exceeds per-host concurrency")
    if v["retry_max_attempts"] * v["retry_max_delay_s"] > v["operation_timeout_s"] * 4:
        raise E.ConfigInvalid("retry budget cannot fit inside the operation deadline")


def canonical_digest(values: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps({"schema": CONFIG_SCHEMA, "values": dict(values)}, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


class ConfigManager:
    """Two-phase activation, retained known-good revisions, rollback, audited transitions."""

    def __init__(self, *, release_version: str, audit: Callable[[dict[str, Any]], None] | None = None,
                 validators: list[Callable[[Mapping[str, Any]], None]] | None = None, keep: int = 16) -> None:
        self._lock = threading.Lock()
        self._release = release_version
        self._audit = audit or (lambda e: None)
        self._validators = list(validators or [])
        self._staged: dict[str, Config] = {}
        self._history: list[Config] = []
        self._keep = keep
        self._active: Config | None = None
        self.activate(self.stage({}, author="package", source="defaults", approval="release"))

    def add_validator(self, fn: Callable[[Mapping[str, Any]], None]) -> None:
        self._validators.append(fn)

    @property
    def active(self) -> Config:
        assert self._active is not None
        return self._active  # single attribute read: atomic under the GIL

    def stage(self, layers: Mapping[str, list[Mapping[str, Any]]], *, author: str, source: str,
              approval: str | None = None) -> Config:
        try:
            values = merge(layers)
            validate_cross_field(values)
            for fn in self._validators:
                fn(values)
        except E.ConfigInvalid as exc:
            self._audit({"kind": "config_rejected", "code": exc.code, "details": exc.details, "author": author})
            raise
        digest = canonical_digest(values)
        meta = ConfigMeta(revision=digest[:16], author=author, source=source, approval=approval,
                          release_version=self._release, created_at=time.time())
        cfg = Config(MappingProxyType(dict(values)), digest, meta)
        with self._lock:
            self._staged[cfg.meta.revision] = cfg
        return cfg

    def activate(self, cfg: Config, *, health_gate: Callable[[Config], bool] | None = None) -> Config:
        with self._lock:
            previous = self._active
            if previous is not None:
                for key, spec in SCHEMA.items():
                    if not spec[4] and previous.values[key] != cfg.values[key]:
                        raise E.ConfigInvalid("setting requires restart; not dynamically reloadable", key=key)
            activated = Config(cfg.values, cfg.digest, ConfigMeta(**{**cfg.meta.__dict__, "activated_at": time.time()}))
            self._active = activated
            self._history.append(activated)
            del self._history[:-self._keep]
        self._audit({"kind": "config_activated", "revision": activated.meta.revision, "digest": activated.digest,
                     "author": activated.meta.author, "approval": activated.meta.approval})
        if health_gate is not None and previous is not None and not health_gate(activated):
            self.rollback(previous.meta.revision, reason="auto: health gate failed")
        return self._active

    def rollback(self, revision: str, *, reason: str) -> Config:
        with self._lock:
            target = next((c for c in reversed(self._history) if c.meta.revision == revision), None)
            if target is None:
                raise E.ConfigInvalid("unknown configuration revision", revision=revision)
            self._active = Config(target.values, target.digest,
                                  ConfigMeta(**{**target.meta.__dict__, "activated_at": time.time()}))
            self._history.append(self._active)
        self._audit({"kind": "config_rollback", "revision": revision, "digest": target.digest, "reason": reason})
        return self._active

    def revisions(self) -> list[str]:
        return [c.meta.revision for c in self._history]


class SecretResolver:
    """Resolves secret:// references at the point of use.  Values never enter Config or logs."""

    def __init__(self, backend: Callable[[str], bytes]) -> None:
        self._backend = backend

    def resolve(self, ref: str) -> bytes:
        if not _SECRET_REF_RE.match(ref or ""):
            raise E.ConfigInvalid("invalid secret reference")
        return self._backend(ref)
