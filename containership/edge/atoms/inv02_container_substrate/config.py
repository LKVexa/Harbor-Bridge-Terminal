"""MC54 — configuration system.

Precedence: built-in defaults < JSON file < ``INV02_*`` environment variables.
Unknown keys are rejected (typos fail closed), every value is type- and range-checked,
secrets are referenced by *file path* only, and the effective configuration has a
stable digest recorded in release/decision evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass, field, fields

from .registry import ValidationError

CONFIG_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Config:
    schema: int = CONFIG_SCHEMA_VERSION
    store_root: str = "/var/lib/inv02"
    audit_log: str = "/var/lib/inv02/audit.jsonl"
    audit_key_file: str = "/etc/inv02/audit.key"
    offline: bool = False
    protected_environments: tuple[str, ...] = ("prod", "production")
    mirrors: dict = field(default_factory=dict)
    insecure_registries: tuple[str, ...] = ()
    ca_file: str | None = None
    max_blob_bytes: int = 8 * 1024**3
    max_store_bytes: int = 256 * 1024**3
    max_inflight_pulls: int = 8
    max_queued_pulls: int = 64
    tenant_rate_per_s: float = 20.0
    tenant_burst: float = 40.0
    tenant_byte_quota: int = 64 * 1024**3
    gc_grace_s: float = 3600.0
    scan_max_age_s: float = 86400.0
    default_runtime_class: str = "runc"
    rootless: bool = True
    metrics_listen: str = "127.0.0.1:9464"
    log_level: str = "INFO"

    def validate(self) -> "Config":
        if self.schema != CONFIG_SCHEMA_VERSION:
            raise ValidationError(f"config schema {self.schema} unsupported")
        for name in ("max_blob_bytes", "max_store_bytes", "max_inflight_pulls", "tenant_byte_quota"):
            if getattr(self, name) <= 0:
                raise ValidationError(f"{name} must be positive")
        if self.max_queued_pulls < 0 or self.tenant_rate_per_s <= 0 or self.tenant_burst <= 0:
            raise ValidationError("admission/rate settings out of range")
        if self.max_blob_bytes > self.max_store_bytes:
            raise ValidationError("max_blob_bytes exceeds max_store_bytes")
        if self.log_level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            raise ValidationError("log_level invalid")
        host, _, port = self.metrics_listen.rpartition(":")
        if not host or not port.isdigit():
            raise ValidationError("metrics_listen must be host:port")
        for p in (self.store_root, self.audit_log, self.audit_key_file):
            if not os.path.isabs(p):
                raise ValidationError(f"path must be absolute: {p}")
        return self

    def digest(self) -> str:
        return "sha256:" + hashlib.sha256(json.dumps(asdict(self), sort_keys=True, default=list).encode()).hexdigest()


_TYPES = {f.name: f for f in fields(Config)}


def _coerce(name: str, value, from_env: bool):
    f = _TYPES[name]
    t = str(f.type)
    try:
        if t.startswith("bool"):
            if isinstance(value, bool):
                return value
            if from_env and str(value).lower() in ("1", "true", "yes", "0", "false", "no"):
                return str(value).lower() in ("1", "true", "yes")
            raise ValueError
        if t.startswith("int"):
            if isinstance(value, bool):
                raise ValueError
            return int(value)
        if t.startswith("float"):
            return float(value)
        if t.startswith("tuple"):
            if from_env:
                value = [v.strip() for v in str(value).split(",") if v.strip()]
            if not isinstance(value, (list, tuple)) or not all(isinstance(v, str) for v in value):
                raise ValueError
            return tuple(value)
        if t.startswith("dict"):
            value = json.loads(value) if from_env else value
            if not isinstance(value, dict):
                raise ValueError
            return value
        if value is None and "None" in t:
            return None
        if not isinstance(value, str):
            raise ValueError
        return value
    except (TypeError, ValueError):
        raise ValidationError(f"config {name}: invalid value {value!r}") from None


def load_config(path: str | None = None, env: dict | None = None) -> Config:
    env = os.environ if env is None else env
    values: dict = {}
    if path:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if not isinstance(doc, dict):
            raise ValidationError("config root must be an object")
        unknown = set(doc) - set(_TYPES)
        if unknown:
            raise ValidationError(f"unknown config keys: {sorted(unknown)}")
        values.update({k: _coerce(k, v, False) for k, v in doc.items()})
    for k, v in env.items():
        if k.startswith("INV02_"):
            name = k[6:].lower()
            if name not in _TYPES:
                raise ValidationError(f"unknown config env var {k}")
            values[name] = _coerce(name, v, True)
    return Config(**values).validate()
