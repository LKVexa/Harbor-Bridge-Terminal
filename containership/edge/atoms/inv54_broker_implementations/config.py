"""Declarative configuration: schema, fail-closed validation, overlays, provenance,
atomic staged apply, rollback, and secret references (components 26-32).

The schema is intentionally expressed in-code *and* exported as JSON Schema
(``schemas/config.schema.json``) so the two can be checked for drift in CI.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from threading import RLock
from typing import Any, Callable, Mapping, Protocol

from .errors import CONFIG_CONFLICT, CONFIG_INVALID, SECURITY_SERVICE_UNAVAILABLE, BrokerError

CONFIG_SCHEMA_VERSION = "inv54.config/1"
PROVIDERS = ("reference", "durable", "kafka", "rabbitmq", "sqs")
PROFILES = ("dev", "production")
SECRET_REF = re.compile(r"^secret://(?P<provider>[a-z][a-z0-9_-]{0,31})/(?P<name>[A-Za-z0-9_./-]{1,200})$")

HARD_LIMITS = {
    "max_message_bytes": 16 * 1024 * 1024,
    "max_partitions": 4096,
    "max_subscribers_per_tenant": 100_000,
    "max_backlog_per_subscriber": 10_000_000,
    "max_log_records_per_partition": 1_000_000_000,
    "max_inflight": 100_000,
}

DEFAULTS: dict[str, Any] = {
    "schema": CONFIG_SCHEMA_VERSION,
    "profile": "dev",
    "provider": {"kind": "reference", "endpoints": [], "options": {}},
    "tls": {"enabled": False, "min_version": "TLSv1.2", "ca_file": None, "cert_ref": None, "key_ref": None,
            "verify_hostname": True},
    "auth": {"mode": "none", "hmac_key_ref": None, "token_ttl_s": 300},
    "limits": {"partitions": 4, "max_message_bytes": 1_048_576, "max_subscribers_per_tenant": 1000,
               "max_backlog_per_subscriber": 10_000, "max_log_records_per_partition": 1_000_000,
               "max_inflight": 1024, "overflow_policy": "reject"},
    "quotas": {"default": {"publish_rate": 1000.0, "publish_burst": 2000.0, "max_bytes": 256 * 1024 * 1024}},
    "retry": {"max_attempts": 5, "base_delay_s": 0.05, "max_delay_s": 5.0},
    "retention": {"max_records": None, "max_age_s": None, "compact": False},
    "storage": {"path": None, "fsync": "always", "encrypt": False, "key_ref": None},
    "telemetry": {"log_level": "INFO", "trace_sample_ratio": 0.1, "max_label_values": 1000},
    "features": {},
}

_REQUIRED_TOP = set(DEFAULTS)


def _deep_merge(base: dict[str, Any], over: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, Mapping) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def apply_overlays(base: Mapping[str, Any], *overlays: Mapping[str, Any]) -> dict[str, Any]:
    """Apply site/environment overlays in order (later wins). Overlays may not change ``schema``."""
    cfg = _deep_merge(DEFAULTS, base)
    for ov in overlays:
        if "schema" in ov and ov["schema"] != cfg["schema"]:
            raise BrokerError(CONFIG_INVALID, "overlay may not change schema version")
        cfg = _deep_merge(cfg, ov)
    return cfg


def _is_secret_ref(v: Any) -> bool:
    return isinstance(v, str) and bool(SECRET_REF.fullmatch(v))


def validate(cfg: Mapping[str, Any]) -> list[str]:
    """Return every problem found (empty list == valid). Never mutates ``cfg``."""
    p: list[str] = []
    unknown = set(cfg) - _REQUIRED_TOP
    if unknown:
        p.append(f"unknown top-level keys: {sorted(unknown)}")
    if cfg.get("schema") != CONFIG_SCHEMA_VERSION:
        p.append(f"schema must be {CONFIG_SCHEMA_VERSION}")
    def sec(name: str) -> Mapping[str, Any]:
        v = cfg.get(name, {})
        if not isinstance(v, Mapping):
            p.append(f"{name} must be an object")
            return {}
        return v
    profile = cfg.get("profile")
    if profile not in PROFILES:
        p.append(f"profile must be one of {PROFILES}")
    prov = sec("provider")
    if not isinstance(prov.get("kind"), str) or prov.get("kind") not in PROVIDERS:
        p.append(f"provider.kind must be one of {PROVIDERS}")
    if prov.get("kind") in ("kafka", "rabbitmq", "sqs") and not prov.get("endpoints") and prov.get("kind") != "sqs":
        p.append("provider.endpoints required for networked providers")
    lim = sec("limits")
    for k, hard in (("partitions", HARD_LIMITS["max_partitions"]),
                    ("max_message_bytes", HARD_LIMITS["max_message_bytes"]),
                    ("max_subscribers_per_tenant", HARD_LIMITS["max_subscribers_per_tenant"]),
                    ("max_backlog_per_subscriber", HARD_LIMITS["max_backlog_per_subscriber"]),
                    ("max_log_records_per_partition", HARD_LIMITS["max_log_records_per_partition"]),
                    ("max_inflight", HARD_LIMITS["max_inflight"])):
        v = lim.get(k)
        if type(v) is not int or not (1 <= v <= hard):
            p.append(f"limits.{k} must be an int in 1..{hard}")
    if lim.get("overflow_policy") not in ("reject", "drop_oldest"):
        p.append("limits.overflow_policy must be reject|drop_oldest")
    r = sec("retry")
    if type(r.get("max_attempts")) is not int or not 1 <= r.get("max_attempts", 0) <= 20:
        p.append("retry.max_attempts must be 1..20")
    tls = sec("tls")
    if tls.get("min_version") not in ("TLSv1.2", "TLSv1.3"):
        p.append("tls.min_version must be TLSv1.2 or TLSv1.3")
    for k in ("cert_ref", "key_ref"):
        if tls.get(k) is not None and not _is_secret_ref(tls[k]):
            p.append(f"tls.{k} must be a secret:// reference, never an inline value")
    auth = sec("auth")
    if auth.get("mode") not in ("none", "hmac", "provider"):
        p.append("auth.mode must be none|hmac|provider")
    if auth.get("mode") == "hmac" and not _is_secret_ref(auth.get("hmac_key_ref")):
        p.append("auth.hmac_key_ref must be a secret:// reference when auth.mode=hmac")
    st = sec("storage")
    if st.get("fsync") not in ("always", "batch", "never"):
        p.append("storage.fsync must be always|batch|never")
    if st.get("encrypt") and not _is_secret_ref(st.get("key_ref")):
        p.append("storage.key_ref must be a secret:// reference when storage.encrypt=true")
    if prov.get("kind") == "durable" and not st.get("path"):
        p.append("storage.path required for provider.kind=durable")
    # Fail-closed production profile: security-critical settings are mandatory.
    if profile == "production":
        if not tls.get("enabled") and prov.get("kind") in ("kafka", "rabbitmq", "sqs"):
            p.append("production: tls.enabled must be true for networked providers")
        if not tls.get("verify_hostname", True):
            p.append("production: tls.verify_hostname may not be disabled")
        if auth.get("mode") == "none":
            p.append("production: auth.mode=none is forbidden")
        if prov.get("kind") == "reference":
            p.append("production: in-memory reference provider is not a supported production profile")
        if st.get("fsync") == "never" and prov.get("kind") == "durable":
            p.append("production: storage.fsync=never is forbidden")
    # Inline secrets anywhere are rejected.
    for path, v in _walk(cfg):
        leaf = path.rsplit(".", 1)[-1].lower()
        if isinstance(v, str) and any(s in leaf for s in ("password", "secret", "private_key")) and not _is_secret_ref(v):
            p.append(f"{path}: inline secret values are forbidden; use secret://")
    return p


def _walk(d: Any, prefix: str = "") -> list[tuple[str, Any]]:
    out: list[tuple[str, Any]] = []
    if isinstance(d, Mapping):
        for k, v in d.items():
            out.extend(_walk(v, f"{prefix}.{k}" if prefix else str(k)))
    else:
        out.append((prefix, d))
    return out


def digest(cfg: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@dataclass(frozen=True)
class Provenance:
    digest: str
    version: int
    author: str
    source: str
    activated_at: float
    previous_digest: str | None

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class ConfigStore:
    """Staged validate -> apply -> commit with optimistic concurrency and bounded history.

    ``apply_hook`` performs the activation; if it raises, the store stays on the previous
    known-good config (atomicity).  ``rollback()`` reactivates the previous committed version.
    """

    def __init__(self, apply_hook: Callable[[dict[str, Any]], None] | None = None, history: int = 16) -> None:
        self._hook = apply_hook or (lambda cfg: None)
        self._lock = RLock()
        self._history: list[tuple[dict[str, Any], Provenance]] = []
        self._max = history
        self._staged: tuple[dict[str, Any], str, str] | None = None

    @property
    def current(self) -> tuple[dict[str, Any], Provenance] | None:
        return self._history[-1] if self._history else None

    def stage(self, cfg: Mapping[str, Any], *, author: str, source: str) -> str:
        full = apply_overlays(cfg)
        problems = validate(full)
        if problems:
            raise BrokerError(CONFIG_INVALID, "; ".join(problems[:10]), problem_count=len(problems))
        with self._lock:
            self._staged = (full, author, source)
        return digest(full)

    def commit(self, expected_current: str | None, *, clock: Callable[[], float] = time.time) -> Provenance:
        with self._lock:
            if self._staged is None:
                raise BrokerError(CONFIG_INVALID, "nothing staged")
            cur = self.current
            cur_d = cur[1].digest if cur else None
            if expected_current != cur_d:
                raise BrokerError(CONFIG_CONFLICT, "config changed since staging", current=cur_d)
            cfg, author, source = self._staged
            self._hook(copy.deepcopy(cfg))  # raises -> nothing committed
            prov = Provenance(digest(cfg), (cur[1].version + 1) if cur else 1, author, source, clock(), cur_d)
            self._history.append((cfg, prov))
            if len(self._history) > self._max:
                del self._history[0]
            self._staged = None
            return prov

    def rollback(self, *, author: str, clock: Callable[[], float] = time.time) -> Provenance:
        with self._lock:
            if len(self._history) < 2:
                raise BrokerError(CONFIG_INVALID, "no known-good predecessor to roll back to")
            prev_cfg, _ = self._history[-2]
            cur = self._history[-1][1]
            self._hook(copy.deepcopy(prev_cfg))
            prov = Provenance(digest(prev_cfg), cur.version + 1, author, f"rollback-to:{digest(prev_cfg)[:12]}",
                              clock(), cur.digest)
            self._history.append((prev_cfg, prov))
            if len(self._history) > self._max:
                del self._history[0]
            return prov

    def provenance_log(self) -> list[dict[str, Any]]:
        return [p.to_dict() for _, p in self._history]


# ---------------------------------------------------------------- secrets (component 32)

class Secret:
    """Opaque secret value; never rendered by repr/str/json."""

    __slots__ = ("_v",)

    def __init__(self, value: bytes) -> None:
        self._v = value

    def reveal(self) -> bytes:
        return self._v

    def __repr__(self) -> str:
        return "Secret(***)"

    __str__ = __repr__


class SecretProvider(Protocol):
    def get(self, name: str) -> Secret: ...


class EnvSecretProvider:
    """``secret://env/NAME`` -> environment variable ``NAME``. Missing => fail closed."""

    def __init__(self, environ: Mapping[str, str] | None = None) -> None:
        self._env = environ if environ is not None else os.environ

    def get(self, name: str) -> Secret:
        if name not in self._env:
            raise BrokerError(SECURITY_SERVICE_UNAVAILABLE, "secret not available", secret_name=name)
        return Secret(self._env[name].encode())


class StaticSecretProvider:
    """Test/dev provider with rotation support."""

    def __init__(self, values: dict[str, bytes] | None = None) -> None:
        self._values = dict(values or {})
        self.available = True

    def put(self, name: str, value: bytes) -> None:
        self._values[name] = value

    def get(self, name: str) -> Secret:
        if not self.available or name not in self._values:
            raise BrokerError(SECURITY_SERVICE_UNAVAILABLE, "secret not available", secret_name=name)
        return Secret(self._values[name])


class SecretResolver:
    def __init__(self, providers: Mapping[str, SecretProvider]) -> None:
        self._p = dict(providers)

    def resolve(self, ref: str) -> Secret:
        m = SECRET_REF.fullmatch(ref or "")
        if not m:
            raise BrokerError(CONFIG_INVALID, "malformed secret reference")
        prov = self._p.get(m["provider"])
        if prov is None:
            raise BrokerError(SECURITY_SERVICE_UNAVAILABLE, "no provider for secret reference",
                              secret_provider=m["provider"])
        return prov.get(m["name"])


def redact(cfg: Mapping[str, Any]) -> dict[str, Any]:
    """Copy safe for logs/evidence: secret refs kept (they are pointers), secret-named values masked."""
    def r(d: Any, key: str = "") -> Any:
        if isinstance(d, Mapping):
            return {k: r(v, k) for k, v in d.items()}
        if isinstance(d, str) and any(s in key.lower() for s in ("password", "secret", "private_key")) \
                and not _is_secret_ref(d):
            return "***REDACTED***"
        return d
    return r(cfg)
