"""Configuration lifecycle: schema, canonical digest, signature, provenance,
transactional activation and rollback (Sections 7-8, REQ-CFG-*).

Configuration describes *policy* (resource -> operations), limits and profile.
It never contains capability objects or seals: runtime references are process
local and cannot be expressed in this schema.  Activation builds a fresh
``Authority`` from the candidate off to the side, runs every check, and only
then swaps one pointer under a lock, so a reader sees the old or the new
complete snapshot and never a mix.  A new Authority is a new domain, so
references minted under the previous configuration are *not* carried over
(they keep working against their own domain until revoked; see ADR-0001 §5).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Final

from .capabilities import (
    MAX_IDENTIFIER_LENGTH, MAX_OPERATIONS, MAX_POLICY_RESOURCES, Authority,
)
from .errors import ConfigRejected, StaleState

CONFIG_SCHEMA: Final[str] = "INV41_CONFIG/1"
SUPPORTED_CONFIG_SCHEMAS: Final[tuple] = ("INV41_CONFIG/0", "INV41_CONFIG/1")
PROFILES: Final[tuple] = ("cloud", "near-edge", "far-edge", "workstation", "test")
MAX_CONFIG_BYTES: Final[int] = 1_048_576
CRITICAL_FIELDS: Final[frozenset] = frozenset({
    "schema", "config_version", "profile", "policy", "limits", "provenance",
})
LIMIT_KEYS: Final[dict] = {
    "max_concurrent_checks": (1, 100_000),
    "max_queue_depth": (0, 1_000_000),
    "max_live_references": (1, 10_000_000),
    "max_membrane_depth": (1, 32),
}


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(config: dict) -> str:
    body = {k: v for k, v in config.items() if k != "signature"}
    return hashlib.sha256(canonical(body)).hexdigest()


def sign(config: dict, key: bytes, key_id: str) -> dict:
    """HMAC-SHA256 approval signature.  Development mechanism; production must
    use the approved release-signing identity (see BLOCKERS.json)."""
    d = digest(config)
    return dict(config, signature={"alg": "HMAC-SHA256", "key_id": key_id, "digest": d,
                                   "mac": hmac.new(key, d.encode(), hashlib.sha256).hexdigest()})


def migrate(config: dict) -> dict:
    """Schema migration: /0 had no limits block and used 'grants' for policy."""
    if config.get("schema") == "INV41_CONFIG/0":
        out = {k: v for k, v in config.items() if k not in ("grants", "schema")}
        out["schema"] = CONFIG_SCHEMA
        out["policy"] = config.get("grants", {})
        out.setdefault("limits", {})
        return out
    return config


def validate(config: dict) -> None:
    """Syntax + schema + semantic checks.  Raises ConfigRejected (fails closed)."""
    if not isinstance(config, dict):
        raise ConfigRejected("configuration must be an object")
    raw = canonical(config)
    if len(raw) > MAX_CONFIG_BYTES:
        raise ConfigRejected("configuration exceeds size limit")
    if config.get("schema") not in SUPPORTED_CONFIG_SCHEMAS:
        raise ConfigRejected("unsupported configuration schema")
    cfg = migrate(config)
    unknown = set(cfg) - CRITICAL_FIELDS - {"signature", "description"}
    if unknown:
        raise ConfigRejected(f"unknown fields: {sorted(unknown)}")
    missing = {"config_version", "profile", "policy", "provenance"} - set(cfg)
    if missing:
        raise ConfigRejected(f"missing required fields: {sorted(missing)}")
    if type(cfg["config_version"]) is not int or cfg["config_version"] < 1:
        raise ConfigRejected("config_version must be a positive integer")
    if cfg["profile"] not in PROFILES:
        raise ConfigRejected("unknown profile")
    policy = cfg["policy"]
    if not isinstance(policy, dict) or not policy or len(policy) > MAX_POLICY_RESOURCES:
        raise ConfigRejected("policy must be a non-empty object within limits")
    for res, ops in policy.items():
        if not isinstance(res, str) or not res or len(res) > MAX_IDENTIFIER_LENGTH:
            raise ConfigRejected("invalid resource identifier")
        if not isinstance(ops, list) or not ops or len(ops) > MAX_OPERATIONS:
            raise ConfigRejected("operations must be a non-empty list within limits")
        if len(set(ops)) != len(ops):
            raise ConfigRejected("duplicate operations")
        if any(type(o) is not str or not o or len(o) > MAX_IDENTIFIER_LENGTH for o in ops):
            raise ConfigRejected("invalid operation identifier")
    for k, v in cfg.get("limits", {}).items():
        if k not in LIMIT_KEYS:
            raise ConfigRejected(f"unknown limit {k}")
        lo, hi = LIMIT_KEYS[k]
        if type(v) is not int or not lo <= v <= hi:
            raise ConfigRejected(f"limit {k} out of range")
    prov = cfg["provenance"]
    if not isinstance(prov, dict) or not {"author", "source", "change_request", "created"} <= set(prov):
        raise ConfigRejected("provenance incomplete")


@dataclass(frozen=True)
class ActiveConfig:
    config: dict
    digest: str
    authority: Authority
    activated_at: float
    key_id: str


@dataclass
class ConfigStore:
    """Holds the active configuration and last-known-good history."""

    trusted_keys: dict  # key_id -> bytes
    history_limit: int = 5
    _active: ActiveConfig | None = None
    _history: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _revoked_keys: set = field(default_factory=set)
    fault_hook: object = None  # test instrumentation: callable(phase) may raise
    events: list = field(default_factory=list)

    @property
    def active(self) -> ActiveConfig | None:
        return self._active

    def revoke_key(self, key_id: str) -> None:
        self._revoked_keys.add(key_id)

    def _fault(self, phase: str) -> None:
        if callable(self.fault_hook):
            self.fault_hook(phase)

    def preflight(self, config: dict) -> tuple[dict, str, str]:
        validate(config)
        sig = config.get("signature")
        if not isinstance(sig, dict):
            raise ConfigRejected("configuration is unsigned")
        key_id = sig.get("key_id")
        if key_id in self._revoked_keys:
            raise ConfigRejected("signing key revoked")
        key = self.trusted_keys.get(key_id)
        if key is None:
            raise ConfigRejected("untrusted signer")
        d = digest(config)
        if sig.get("digest") != d:
            raise ConfigRejected("digest mismatch")
        expected = hmac.new(key, d.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, str(sig.get("mac"))):
            raise ConfigRejected("bad signature")
        cfg = migrate(config)
        if self._active is not None and cfg["config_version"] <= self._active.config["config_version"]:
            raise StaleState("configuration version is not newer than the active one (rollback attack?)")
        return cfg, d, key_id

    def activate(self, config: dict) -> ActiveConfig:
        with self._lock:
            try:
                self._fault("preflight")
                cfg, d, key_id = self.preflight(config)
                self._fault("stage")
                authority = Authority({r: set(o) for r, o in cfg["policy"].items()},
                                      authority_id=f"cfg-v{cfg['config_version']}")
                staged = ActiveConfig(cfg, d, authority, time.time(), key_id)
                self._fault("commit")
            except Exception as exc:
                self.events.append(("config.rejected", type(exc).__name__))
                raise
            if self._active is not None:
                self._history.append(self._active)
                del self._history[:-self.history_limit]
            self._active = staged  # single pointer swap == atomic commit
            self.events.append(("config.activated", d))
            return staged

    def rollback(self, *, operator_authorized: bool) -> ActiveConfig:
        if not operator_authorized:
            raise ConfigRejected("rollback requires an authorized operator")
        with self._lock:
            if not self._history:
                raise ConfigRejected("no last-known-good configuration")
            previous = self._history.pop()
            # Re-mint: a rollback is a fresh domain, never a resurrection of revoked references.
            cfg = previous.config
            authority = Authority({r: set(o) for r, o in cfg["policy"].items()},
                                  authority_id=f"cfg-v{cfg['config_version']}-rb")
            self._active = ActiveConfig(cfg, previous.digest, authority, time.time(), previous.key_id)
            self.events.append(("config.rollback", previous.digest))
            return self._active


def default_profile(profile: str) -> dict:
    """Secure default configuration skeleton for a deployment profile (unsigned)."""
    if profile not in PROFILES:
        raise ConfigRejected("unknown profile")
    limits = {
        "cloud": {"max_concurrent_checks": 256, "max_queue_depth": 1024, "max_live_references": 1_000_000, "max_membrane_depth": 16},
        "near-edge": {"max_concurrent_checks": 64, "max_queue_depth": 256, "max_live_references": 100_000, "max_membrane_depth": 16},
        "far-edge": {"max_concurrent_checks": 8, "max_queue_depth": 32, "max_live_references": 10_000, "max_membrane_depth": 8},
        "workstation": {"max_concurrent_checks": 32, "max_queue_depth": 128, "max_live_references": 100_000, "max_membrane_depth": 16},
        "test": {"max_concurrent_checks": 4, "max_queue_depth": 8, "max_live_references": 1_000, "max_membrane_depth": 8},
    }[profile]
    return {"schema": CONFIG_SCHEMA, "config_version": 1, "profile": profile,
            "policy": {"example-resource": ["read"]}, "limits": limits,
            "provenance": {"author": "UNASSIGNED", "source": "defaults", "change_request": "NONE", "created": "1970-01-01T00:00:00Z"}}
