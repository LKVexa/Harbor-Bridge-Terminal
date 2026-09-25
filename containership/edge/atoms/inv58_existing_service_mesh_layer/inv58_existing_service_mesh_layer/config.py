"""Declarative configuration subsystem (MC-009; INV-58-C032..C039, C014 C048 outage matrix).

* Immutable artifacts (this package) never contain site/environment settings;
  everything mutable arrives as a ``PK_MESH_CONFIG/1`` document (C032).
* :data:`SECURE_DEFAULTS` is complete and safe on its own (C033).
* ``compose()`` applies ordered environment/site overlays by deep merge, so a
  site changes behaviour without rebuilding the artifact (C035).
* ``validate()`` performs structural *and* semantic validation and rejects any
  security downgrade; nothing is activated unless validation passes (C034).
* :class:`ConfigStore` activates a whole document in one reference swap, with
  optimistic concurrency, provenance, bounded history, operator rollback and
  automatic rollback when a post-activation health probe fails (C036–C038).
* Secrets appear only as ``secretref://`` references; literal secret material
  is rejected and diagnostics are redacted (C039).
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable, Mapping, Sequence

from .authz import ACTOR_TYPES, CAPABILITIES, DEFAULT_ROLES
from .secret_refs import is_secret_ref, looks_like_secret_material

CONFIG_SCHEMA = "PK_MESH_CONFIG/1"
SUPPORTED_CONFIG_SCHEMAS = ("PK_MESH_CONFIG/1",)
MAX_CONFIG_BYTES = 256 * 1024
MAX_HISTORY = 32
_TENANT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_SECURITY_DEPENDENCIES = ("identity", "policy", "key", "time", "attestation")
_OUTAGE_MODES = ("fail_closed", "fail_safe_degraded", "fail_open")

SECURE_DEFAULTS: dict[str, Any] = {
    "schema": CONFIG_SCHEMA,
    "version": "0",
    "trust_domain": "estate.local",
    "default_budget": 3,
    "max_budget": 5,
    "tenants": [],
    "meshed_destinations": [],
    "limits": {
        "max_routes": 10_000, "max_flags": 1024, "max_destinations": 10_000,
        "max_payload_bytes": 16_384, "max_inflight": 256, "max_queue": 1024,
        "max_routes_per_tenant": 2_000, "max_label_cardinality": 1_000,
    },
    "retry": {"base_delay_ms": 25, "max_delay_ms": 2_000, "max_elapsed_ms": 10_000},
    "breaker": {"failure_threshold": 5, "reset_timeout_s": 30.0, "half_open_max": 1},
    "admission": {"rate_per_s": 500.0, "burst": 1000, "tenant_share": 0.5},
    "deadline_ms": {"default": 1_000, "max": 30_000},
    "trust_outage_policy": {
        "identity": "fail_closed", "policy": "fail_closed", "key": "fail_closed",
        "time": "fail_closed", "attestation": "fail_closed", "telemetry": "fail_safe_degraded",
        "audit_sink": "fail_closed",
    },
    "health": {"stall_after_s": 30.0, "max_error_ratio": 0.5, "min_samples": 20},
    "audit_key_ref": "secretref://kms/inv58/audit",
    "token_key_ref": "secretref://kms/inv58/token",
    "artifact_key_ref": "secretref://kms/inv58/artifact",
    "spiffe_bindings": {},
    "policy": {"version": "p0", "max_age_s": 86_400.0, "roles": {k: sorted(v) for k, v in DEFAULT_ROLES.items()}},
    "telemetry": {"sample_rate": 1.0, "redact_high_cardinality": True, "retention_days": 30},
}


class ConfigError(ValueError):
    def __init__(self, problems: Sequence[str]):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems[:20]))


def canonical(doc: Mapping) -> bytes:
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def digest(doc: Mapping) -> str:
    return "sha256:" + hashlib.sha256(canonical(doc)).hexdigest()


def _merge(base: Any, over: Any) -> Any:
    if isinstance(base, dict) and isinstance(over, dict):
        out = dict(base)
        for k, v in over.items():
            out[k] = _merge(base.get(k), v) if k in base else copy.deepcopy(v)
        return out
    return copy.deepcopy(over)


def compose(*layers: Mapping) -> dict:
    """Secure defaults ← base ← environment overlay ← site overlay (C035)."""
    doc: dict = copy.deepcopy(SECURE_DEFAULTS)
    for layer in layers:
        if not isinstance(layer, Mapping):
            raise ConfigError(["overlay must be a mapping"])
        doc = _merge(doc, dict(layer))
    return doc


def _int(p, doc, path, lo, hi):
    v = doc
    for part in path.split("."):
        v = v.get(part) if isinstance(v, dict) else None
    if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
        p.append(f"{path} must be an integer in [{lo}, {hi}]")
    return v


def _num(p, doc, path, lo, hi):
    v = doc
    for part in path.split("."):
        v = v.get(part) if isinstance(v, dict) else None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
        p.append(f"{path} must be a number in [{lo}, {hi}]")
    return v


def _scan_secrets(obj, path, problems):
    if isinstance(obj, str):
        if looks_like_secret_material(obj):
            problems.append(f"{path} contains literal secret material; use secretref://")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            _scan_secrets(v, f"{path}.{k}", problems)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _scan_secrets(v, f"{path}[{i}]", problems)


def validate(doc: Mapping) -> dict:
    """Return a validated deep copy or raise :class:`ConfigError` (fail closed)."""
    problems: list[str] = []
    if not isinstance(doc, Mapping):
        raise ConfigError(["configuration must be an object"])
    raw = canonical(doc)
    if len(raw) > MAX_CONFIG_BYTES:
        raise ConfigError([f"configuration exceeds {MAX_CONFIG_BYTES} bytes"])
    doc = json.loads(raw)
    known = set(SECURE_DEFAULTS)
    for k in doc:
        if k not in known:
            problems.append(f"unknown top-level key {k!r}")
    if doc.get("schema") not in SUPPORTED_CONFIG_SCHEMAS:
        problems.append(f"unsupported schema {doc.get('schema')!r}")
    if not isinstance(doc.get("version"), str) or not doc.get("version"):
        problems.append("version must be a non-empty string")
    td = doc.get("trust_domain")
    if not isinstance(td, str) or not re.fullmatch(r"[a-z0-9]([a-z0-9.-]{0,253}[a-z0-9])?", td or "") or ".." in (td or ""):
        problems.append("trust_domain invalid")
    mb = _int(problems, doc, "max_budget", 1, 10)
    db = _int(problems, doc, "default_budget", 1, 10)
    if isinstance(mb, int) and isinstance(db, int) and db > mb:
        problems.append("default_budget must not exceed max_budget")
    tenants = doc.get("tenants")
    if not isinstance(tenants, list) or len(tenants) > 1000 or any(not isinstance(t, str) or not _TENANT_RE.fullmatch(t) for t in tenants):
        problems.append("tenants must be a list (<=1000) of DNS-label tenant ids")
    elif len(set(tenants)) != len(tenants):
        problems.append("tenants must be unique")
    md = doc.get("meshed_destinations")
    if not isinstance(md, list) or any(not isinstance(d, str) or not d or d != d.strip() or len(d) > 512 for d in md):
        problems.append("meshed_destinations must be a list of non-empty strings")
    for key, lo, hi in (("max_routes", 1, 1_000_000), ("max_flags", 1, 1_000_000), ("max_destinations", 1, 1_000_000),
                        ("max_payload_bytes", 256, 1_048_576), ("max_inflight", 1, 100_000), ("max_queue", 1, 1_000_000),
                        ("max_routes_per_tenant", 1, 1_000_000), ("max_label_cardinality", 1, 100_000)):
        _int(problems, doc, f"limits.{key}", lo, hi)
    b = _int(problems, doc, "retry.base_delay_ms", 1, 60_000)
    m = _int(problems, doc, "retry.max_delay_ms", 1, 600_000)
    _int(problems, doc, "retry.max_elapsed_ms", 1, 3_600_000)
    if isinstance(b, int) and isinstance(m, int) and b > m:
        problems.append("retry.base_delay_ms must not exceed retry.max_delay_ms")
    _int(problems, doc, "breaker.failure_threshold", 1, 10_000)
    _num(problems, doc, "breaker.reset_timeout_s", 0.1, 3_600)
    _int(problems, doc, "breaker.half_open_max", 1, 1_000)
    _num(problems, doc, "admission.rate_per_s", 0.001, 1_000_000)
    _int(problems, doc, "admission.burst", 1, 10_000_000)
    _num(problems, doc, "admission.tenant_share", 0.01, 1.0)
    d1 = _int(problems, doc, "deadline_ms.default", 1, 600_000)
    d2 = _int(problems, doc, "deadline_ms.max", 1, 600_000)
    if isinstance(d1, int) and isinstance(d2, int) and d1 > d2:
        problems.append("deadline_ms.default must not exceed deadline_ms.max")
    top = doc.get("trust_outage_policy")
    if not isinstance(top, dict):
        problems.append("trust_outage_policy must be an object")
    else:
        for dep, mode in top.items():
            if mode not in _OUTAGE_MODES:
                problems.append(f"trust_outage_policy.{dep} has invalid mode {mode!r}")
        for dep in _SECURITY_DEPENDENCIES + ("audit_sink",):
            if top.get(dep) != "fail_closed":
                problems.append(f"trust_outage_policy.{dep} is security-critical and must be fail_closed")
    _num(problems, doc, "health.stall_after_s", 1, 86_400)
    _num(problems, doc, "health.max_error_ratio", 0.0, 1.0)
    _int(problems, doc, "health.min_samples", 1, 1_000_000)
    for ref in ("audit_key_ref", "token_key_ref", "artifact_key_ref"):
        if not is_secret_ref(doc.get(ref)):
            problems.append(f"{ref} must be a secretref:// reference")
    binds = doc.get("spiffe_bindings")
    pol = doc.get("policy") if isinstance(doc.get("policy"), dict) else {}
    roles = pol.get("roles") if isinstance(pol.get("roles"), dict) else None
    if roles is None:
        problems.append("policy.roles must be an object")
        roles = {}
    if not isinstance(pol.get("version"), str) or not pol.get("version"):
        problems.append("policy.version required")
    _num(problems, doc, "policy.max_age_s", 60, 31_536_000)
    for role, caps in roles.items():
        if not isinstance(caps, list) or any(c not in CAPABILITIES for c in caps):
            problems.append(f"policy.roles.{role} contains unknown capability")
        elif "control.break_glass" in caps and role != "break-glass":
            problems.append("control.break_glass may only be granted by the dedicated break-glass role")
    if not isinstance(binds, dict) or len(binds) > 10_000:
        problems.append("spiffe_bindings must be an object (<=10000 entries)")
    else:
        for rid, b in binds.items():
            if not isinstance(rid, str) or not rid.startswith("runtime:"):
                problems.append(f"spiffe_bindings key {rid!r} must be a runtime identity")
            if not isinstance(b, dict) or b.get("actor_type") not in ACTOR_TYPES or b.get("actor_type") in ("operator", "ci", "auditor"):
                problems.append(f"spiffe_bindings.{rid} actor_type must be workload/controller/node")
            elif not isinstance(b.get("roles", []), list) or not isinstance(b.get("tenants", []), list):
                problems.append(f"spiffe_bindings.{rid} roles/tenants must be lists")
            elif set(b) - {"actor_type", "roles", "tenants"}:
                problems.append(f"spiffe_bindings.{rid} has unknown keys")
            elif any(t not in (tenants or []) for t in b.get("tenants", [])):
                problems.append(f"spiffe_bindings.{rid} grants an undeclared tenant")
            elif any(r not in roles for r in b.get("roles", [])):
                problems.append(f"spiffe_bindings.{rid} references undefined role")
            elif any("control.break_glass" in roles.get(r, []) for r in b.get("roles", [])):
                problems.append(f"spiffe_bindings.{rid} may not hold break-glass via mesh identity")
    tel = doc.get("telemetry")
    _num(problems, doc, "telemetry.sample_rate", 0.0, 1.0)
    _int(problems, doc, "telemetry.retention_days", 1, 3650)
    if not isinstance(tel, dict) or tel.get("redact_high_cardinality") is not True:
        problems.append("telemetry.redact_high_cardinality must be true")
    _scan_secrets(doc, "$", problems)
    if problems:
        raise ConfigError(problems)
    return doc


@dataclass(frozen=True)
class Provenance:
    digest: str
    version: str
    author: str
    source: str
    activated_at: float
    previous_digest: str | None
    reason: str

    def as_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class ConfigStore:
    """Atomic, revisioned, rollback-capable active configuration holder."""

    clock: Callable[[], float] = time.time
    max_history: int = MAX_HISTORY
    _active: tuple[dict, Provenance] | None = field(default=None, init=False)
    _history: list[tuple[dict, Provenance]] = field(default_factory=list, init=False)
    _lock: RLock = field(default_factory=RLock, init=False, repr=False)

    def active(self) -> tuple[dict, Provenance] | None:
        with self._lock:
            if self._active is None:
                return None
            return copy.deepcopy(self._active[0]), self._active[1]

    def provenance(self) -> Provenance | None:
        """Active provenance without copying the document (hot path; OPT-2)."""
        with self._lock:
            return None if self._active is None else self._active[1]

    def history(self) -> list[Provenance]:
        with self._lock:
            return [p for _, p in self._history]

    def activate(self, doc: Mapping, *, author: str, source: str, expected_digest: str | None = None,
                 health_probe: Callable[[dict], bool] | None = None, reason: str = "activate") -> Provenance:
        """Validate then swap atomically.  If ``health_probe`` returns False or
        raises, the previous configuration is restored automatically (C038)."""
        if not isinstance(author, str) or not author or not isinstance(source, str) or not source:
            raise ConfigError(["author and source are required for provenance"])
        valid = validate(doc)
        d = digest(valid)
        with self._lock:
            current = self._active[1].digest if self._active else None
            if expected_digest is not None and expected_digest != current:
                raise ConfigError([f"conflict: expected active {expected_digest}, found {current}"])
            prov = Provenance(d, valid["version"], author, source, self.clock(), current, reason)
            previous = self._active
            self._active = (valid, prov)
            if previous is not None:
                self._history.append(previous)
                del self._history[:-self.max_history]
        if health_probe is not None:
            ok = False
            try:
                ok = bool(health_probe(copy.deepcopy(valid)))
            except Exception:
                ok = False
            if not ok:
                with self._lock:
                    if self._active and self._active[1].digest == d:
                        if self._history:
                            self._active = self._history.pop()
                        else:
                            self._active = previous
                raise ConfigError([f"post-activation health probe failed; automatically rolled back from {d}"])
        return prov

    def rollback(self, *, author: str, to_digest: str | None = None) -> Provenance:
        with self._lock:
            if not self._history:
                raise ConfigError(["no previous configuration to roll back to"])
            idx = len(self._history) - 1
            if to_digest is not None:
                matches = [i for i, (_, p) in enumerate(self._history) if p.digest == to_digest]
                if not matches:
                    raise ConfigError([f"digest {to_digest} not in retained history"])
                idx = matches[-1]
            doc, old = self._history.pop(idx)
            current = self._active
            prov = Provenance(old.digest, old.version, author, "rollback", self.clock(),
                              current[1].digest if current else None, "rollback")
            if current is not None:
                self._history.append(current)
                del self._history[:-self.max_history]
            self._active = (doc, prov)
            return prov
