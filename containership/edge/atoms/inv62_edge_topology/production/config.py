"""Declarative configuration: schema + secure defaults, overlays, secret
references, pre-activation validation, provenance, atomic generation swap and
rollback (MC-022 .. MC-029).

Separation of concerns (MC-022):
  * immutable artifact  = this package + ``schemas/`` (digest in the release manifest)
  * mutable configuration = documents validated here and activated as numbered generations
  * mutable state        = topology graph + election terms, persisted by :mod:`.persistence`
    under ``state_dir`` which must not live inside the artifact directory.
"""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import os
import stat
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from collections.abc import Callable, Mapping

from . import errors
from .schema import SchemaViolation, Validator

SCHEMA_VERSION = 1

#: Constraint precedence (MC-010).  Fixed, not configurable in order: a
#: config may only *omit* cost.  Earlier entries always win.
PRECEDENCE = ("security", "tenant_isolation", "residency", "availability", "slo", "cost")

POS_INT = {"type": "integer", "minimum": 1}
POS_NUM = {"type": "number", "exclusiveMinimum": 0}
SECRET_REF = {"type": "string", "pattern": r"secret://[a-z0-9][a-z0-9\-_/]{0,127}"}

CONFIG_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:inv62:config:1",
    "title": "INV-62 edge topology configuration v1",
    "$defs": {"ident": {"type": "string", "minLength": 1, "maxLength": 128, "pattern": r"[A-Za-z0-9\-_.:]+"}},
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "environment", "cloud_node", "secrets"],
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        "environment": {"enum": ["dev", "test", "staging", "prod"]},
        "site": {"$ref": "#/$defs/ident"},
        "cloud_node": {"$ref": "#/$defs/ident"},
        "coordinator_capability": {"$ref": "#/$defs/ident"},
        "state_dir": {"type": "string", "minLength": 1, "maxLength": 1024},
        "limits": {"type": "object", "additionalProperties": False, "properties": {
            "max_nodes": {"type": "integer", "minimum": 1, "maximum": 1_000_000},
            "max_links": {"type": "integer", "minimum": 1, "maximum": 5_000_000},
            "max_degree": {"type": "integer", "minimum": 1, "maximum": 65_536},
            "max_caps_per_node": {"type": "integer", "minimum": 1, "maximum": 1024},
            "max_tenants": {"type": "integer", "minimum": 1, "maximum": 100_000}}},
        "admission": {"type": "object", "additionalProperties": False, "properties": {
            "rate_per_s": POS_NUM, "burst": POS_INT, "max_in_flight": POS_INT}},
        "health": {"type": "object", "additionalProperties": False, "properties": {
            "probe_interval_s": POS_NUM, "stale_after_s": POS_NUM, "down_after_failures": POS_INT,
            "up_after_successes": POS_INT, "flap_window_s": POS_NUM, "max_flaps": POS_INT,
            "suspect_after_s": POS_NUM}},
        "election": {"type": "object", "additionalProperties": False, "properties": {
            "lease_ttl_s": POS_NUM, "renew_before_s": POS_NUM}},
        "policy": {"type": "object", "additionalProperties": False, "properties": {
            "residency_required": {"type": "boolean"},
            "allow_cross_site_failover": {"type": "boolean"},
            "stale_link_behaviour": {"enum": ["exclude", "degrade"]}}},
        "security": {"type": "object", "additionalProperties": False, "properties": {
            "require_auth": {"const": True},
            "require_signed_config": {"type": "boolean"},
            "audit_fsync": {"type": "boolean"},
            "encrypt_at_rest": {"type": "boolean"}}},
        "secrets": {"type": "object", "additionalProperties": False, "required": ["token_keys", "audit_key"],
                    "properties": {"token_keys": {"type": "object", "additionalProperties": SECRET_REF},
                                   "active_token_key": {"type": "string", "pattern": r"[A-Za-z0-9\-_]{1,64}"},
                                   "audit_key": SECRET_REF, "state_key": SECRET_REF, "config_signing_key": SECRET_REF}},
        "telemetry": {"type": "object", "additionalProperties": False, "properties": {
            "log_level": {"enum": ["debug", "info", "warning", "error"]},
            "trace_sample_rate": {"type": "number", "minimum": 0, "maximum": 1},
            "max_label_values": {"type": "integer", "minimum": 1, "maximum": 100_000},
            "retention_days": {"type": "integer", "minimum": 1, "maximum": 400},
            "expose_node_names": {"type": "boolean"}}},
    },
}

#: Secure defaults (MC-023): everything security-relevant is on unless
#: explicitly relaxed *and* the relaxation is allowed by the schema.
DEFAULTS: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION,
    "coordinator_capability": "coordinator",
    "limits": {"max_nodes": 10_000, "max_links": 50_000, "max_degree": 1024, "max_caps_per_node": 64, "max_tenants": 1024},
    "admission": {"rate_per_s": 500.0, "burst": 1000, "max_in_flight": 256},
    "health": {"probe_interval_s": 5.0, "stale_after_s": 30.0, "down_after_failures": 3, "up_after_successes": 2,
               "flap_window_s": 60.0, "max_flaps": 4, "suspect_after_s": 10.0},
    "election": {"lease_ttl_s": 10.0, "renew_before_s": 3.0},
    "policy": {"residency_required": True, "allow_cross_site_failover": False, "stale_link_behaviour": "exclude"},
    "security": {"require_auth": True, "require_signed_config": False, "audit_fsync": True, "encrypt_at_rest": False},
    "telemetry": {"log_level": "info", "trace_sample_rate": 0.05, "max_label_values": 1000, "retention_days": 30,
                  "expose_node_names": False},
}

_VALIDATOR = Validator(CONFIG_SCHEMA)


def deep_merge(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    """Objects merge recursively; scalars and lists replace.  ``None`` in an
    overlay is rejected (deletion by overlay is not allowed)."""
    out = copy.deepcopy(dict(base))
    for key, value in overlay.items():
        if value is None:
            raise errors.TopoError(errors.INVALID_REQUEST, f"overlay may not null out {key!r}")
        if isinstance(value, Mapping) and isinstance(out.get(key), Mapping):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def compose(document: Mapping[str, Any], *overlays: Mapping[str, Any]) -> dict[str, Any]:
    """defaults <- base document <- environment overlay <- site overlay ... (MC-025)."""
    effective = deep_merge(DEFAULTS, document)
    for overlay in overlays:
        effective = deep_merge(effective, overlay)
    return effective


def canonical_digest(config: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(config, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


# ------------------------------------------------------------------ secrets
class SecretProvider:
    """Boundary for secret material (MC-029).  Implementations must never log values."""

    available = True

    def resolve(self, ref: str) -> bytes:  # pragma: no cover - interface
        raise NotImplementedError


class StaticSecretProvider(SecretProvider):
    def __init__(self, values: Mapping[str, bytes]):
        self._values = dict(values)

    def resolve(self, ref: str) -> bytes:
        if not self.available:
            raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "secret provider unavailable", {"dependency": "secrets"})
        try:
            return self._values[ref]
        except KeyError:
            raise errors.TopoError(errors.INVALID_REQUEST, "secret reference does not resolve", {"ref": ref}) from None


class FileSecretProvider(SecretProvider):
    """``secret://a/b`` -> ``<root>/a/b``; refuses group/world-readable files on POSIX."""

    def __init__(self, root: str | os.PathLike[str]):
        self.root = Path(root).resolve()

    def resolve(self, ref: str) -> bytes:
        rel = ref[len("secret://"):]
        path = (self.root / rel).resolve()
        if self.root not in path.parents:
            raise errors.TopoError(errors.INVALID_REQUEST, "secret reference escapes root", {"ref": ref})
        try:
            st = path.stat()
        except OSError:
            raise errors.TopoError(errors.DEPENDENCY_UNAVAILABLE, "secret unavailable", {"ref": ref}) from None
        if os.name == "posix" and st.st_mode & (stat.S_IRWXG | stat.S_IRWXO):
            raise errors.TopoError(errors.INVALID_REQUEST, "secret file permissions too open", {"ref": ref})
        return path.read_bytes().strip()


# --------------------------------------------------------------- validation
@dataclass(frozen=True)
class Resolved:
    config: dict[str, Any]
    token_keys: dict[str, bytes]
    active_token_key: str
    audit_key: bytes
    state_key: bytes | None
    digest: str


def validate(config: Mapping[str, Any], secrets: SecretProvider) -> Resolved:
    """Complete pre-activation validation (MC-024).  Fails closed with the first
    violated rule; never returns a partially valid configuration."""
    try:
        _VALIDATOR.validate(dict(config))
    except SchemaViolation as exc:
        raise errors.TopoError(errors.INVALID_REQUEST, "configuration failed schema validation",
                               {"path": exc.path, "reason": exc.reason}) from None
    problems = []
    h, e = config["health"], config["election"]
    if h["stale_after_s"] <= h["probe_interval_s"]:
        problems.append("health.stale_after_s must exceed probe_interval_s")
    if h["suspect_after_s"] >= h["stale_after_s"]:
        problems.append("health.suspect_after_s must be below stale_after_s")
    if e["renew_before_s"] >= e["lease_ttl_s"]:
        problems.append("election.renew_before_s must be below lease_ttl_s")
    if config["limits"]["max_links"] < config["limits"]["max_nodes"] - 1:
        problems.append("limits.max_links cannot connect max_nodes")
    if config["environment"] == "prod":
        if config["telemetry"]["log_level"] == "debug":
            problems.append("prod forbids debug logging")
        if not config["security"]["audit_fsync"]:
            problems.append("prod requires audit_fsync")
        if not config["policy"]["residency_required"]:
            problems.append("prod requires residency_required")
    sec = config["secrets"]
    if not sec["token_keys"]:
        problems.append("secrets.token_keys must name at least one key")
    for kid in sec["token_keys"]:
        if not (1 <= len(kid) <= 64 and all(c.isalnum() or c in "-_" for c in kid)):
            problems.append(f"secrets.token_keys has invalid key id {kid[:64]!r}")
    if "active_token_key" in sec and sec["active_token_key"] not in sec["token_keys"]:
        problems.append("secrets.active_token_key is not one of token_keys")
    if config["security"]["encrypt_at_rest"] and "state_key" not in sec:
        problems.append("encrypt_at_rest requires secrets.state_key")
    if config["security"]["require_signed_config"] and "config_signing_key" not in sec:
        problems.append("require_signed_config requires secrets.config_signing_key")
    if problems:
        raise errors.TopoError(errors.INVALID_REQUEST, "configuration failed semantic validation", {"problems": problems})
    token_keys = {kid: secrets.resolve(ref) for kid, ref in sorted(sec["token_keys"].items())}
    for kid, value in token_keys.items():
        if len(value) < 32:
            raise errors.TopoError(errors.INVALID_REQUEST, "token key too short", {"kid": kid})
    audit_key = secrets.resolve(sec["audit_key"])
    state_key = secrets.resolve(sec["state_key"]) if "state_key" in sec else None
    for label, key_value in (("audit_key", audit_key), ("state_key", state_key)):
        if key_value is not None and len(key_value) < 32:
            raise errors.TopoError(errors.INVALID_REQUEST, f"{label} too short")
    active = sec.get("active_token_key") or sorted(token_keys)[-1]
    return Resolved(dict(config), token_keys, active, audit_key, state_key, canonical_digest(config))


# --------------------------------------------------------- generation store
@dataclass(frozen=True)
class Provenance:
    generation: int
    digest: str
    author: str
    source: str
    created_at: float
    previous: int | None
    signature: str | None = None
    activated_at: float | None = None

    def as_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


@dataclass
class Generation:
    provenance: Provenance
    resolved: Resolved


def sign_config(config: Mapping[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical_digest(config).encode(), hashlib.sha256).hexdigest()


@dataclass
class ConfigStore:
    """Numbered, immutable generations with CAS activation and rollback
    (MC-026, MC-027, MC-028).  Activation calls ``on_activate`` (which may
    rebuild runtime objects); if it raises, the previous generation stays
    active — the swap is all-or-nothing."""

    secrets: SecretProvider
    keep: int = 20
    directory: Path | None = None
    clock: Callable[[], float] = time.time
    on_activate: Callable[[Generation], None] | None = None
    _gens: dict[int, Generation] = field(default_factory=dict)
    _active: int | None = None
    _next: int = 1
    _lock: threading.Lock = field(default_factory=threading.Lock)

    @property
    def active(self) -> Generation | None:
        return None if self._active is None else self._gens[self._active]

    def history(self) -> list[dict[str, Any]]:
        return [g.provenance.as_dict() for _, g in sorted(self._gens.items())]

    def activate(self, config: Mapping[str, Any], *, author: str, source: str,
                 expected_generation: int | None, signature: str | None = None) -> Provenance:
        with self._lock:
            if expected_generation != self._active:
                raise errors.TopoError(errors.CONFLICT, "active configuration generation changed",
                                       {"expected": expected_generation, "actual": self._active})
            resolved = validate(config, self.secrets)
            if resolved.config["security"]["require_signed_config"]:
                key = self.secrets.resolve(resolved.config["secrets"]["config_signing_key"])
                if not signature or not hmac.compare_digest(signature, sign_config(config, key)):
                    raise errors.TopoError(errors.UNAUTHENTICATED, "configuration signature missing or invalid")
            gen = self._next
            prov = Provenance(gen, resolved.digest, author, source, self.clock(), self._active, signature)
            candidate = Generation(prov, resolved)
            if self.on_activate:
                self.on_activate(candidate)  # may raise -> nothing changes
            prov = Provenance(**{**prov.as_dict(), "activated_at": self.clock()})
            candidate = Generation(prov, resolved)
            self._gens[gen] = candidate
            self._active, self._next = gen, gen + 1
            self._persist(candidate)
            for old in sorted(self._gens)[:-self.keep]:
                if old != self._active:
                    del self._gens[old]
            return prov

    def rollback(self, *, to_generation: int | None = None, author: str, reason: str) -> Provenance:
        """Re-activate an earlier generation as a *new* generation number so
        history is never rewritten.  Re-validates (secrets may have rotated)."""
        with self._lock:
            current = self.active
            if current is None:
                raise errors.TopoError(errors.NOT_READY, "no active configuration")
            target = to_generation if to_generation is not None else current.provenance.previous
            if target is None or target not in self._gens:
                raise errors.TopoError(errors.INVALID_REQUEST, "rollback target unavailable", {"target": target})
            config = self._gens[target].resolved.config
            signature = self._gens[target].provenance.signature
            expected = self._active
        return self.activate(config, author=author, source=f"rollback:{target}:{reason}",
                             expected_generation=expected, signature=signature)

    def _persist(self, gen: Generation) -> None:
        if self.directory is None:
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        payload = {"provenance": gen.provenance.as_dict(), "config": gen.resolved.config}
        tmp = self.directory / f".gen-{gen.provenance.generation}.tmp"
        tmp.write_text(json.dumps(payload, sort_keys=True, indent=1))
        os.replace(tmp, self.directory / f"gen-{gen.provenance.generation:06d}.json")
        ptr = self.directory / ".ACTIVE.tmp"
        ptr.write_text(str(gen.provenance.generation))
        os.replace(ptr, self.directory / "ACTIVE")
