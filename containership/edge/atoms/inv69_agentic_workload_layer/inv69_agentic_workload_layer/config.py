"""Declarative configuration, deployment profiles, overlays, provenance and
atomic generations for INV-69 (C012, C033, C035, C036, C037).

Precedence (lowest -> highest):
    built-in secure defaults -> deployment profile defaults -> base -> environment
    -> site -> instance -> emergency override (tighten-only)

* Strict parsing: unknown fields, wrong types, out-of-range values, duplicate
  JSON keys and unsupported schema versions are rejected (AGT-CFG-001).
* Locked fields may only be set at or above their lock scope (AGT-CFG-002).
* Secrets never appear inline: sensitive fields must be ``secretref://`` refs.
* ``ConfigStore`` holds immutable generations and switches the active pointer
  with compare-and-swap; a provenance record is appended to a hash chain in the
  same critical section as activation, so no generation is active without one.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
import copy
import hashlib
import json
import threading
import time

from .errors import AgentError

SCHEMA_VERSION = "PK_AGENT_CONFIG/1"
PROFILE_SCHEMA = "PK_AGENT_PROFILE/1"
SUPPORTED_SCHEMAS = {SCHEMA_VERSION}
SCOPES = ("default", "profile", "base", "environment", "site", "instance", "emergency")
PROFILE_DIR = Path(__file__).resolve().parent / "config" / "profiles"

# field path -> (type, min, max, unit, reloadable, sensitive, lock_scope, tighten)
# lock_scope: the LOWEST-precedence scope allowed to set it is "default"; a field
#   locked at "environment" may be set by default/profile/base/environment only.
# tighten: "min" (lower is safer), "max" (higher is safer), "true"/"false" (that
#   value is safer), "enum:<ordered safe list>" or None.
F = {
    "schema_version": (str, None, None, None, False, False, "base", None),
    "profile": (str, None, None, None, False, False, "environment", None),
    "budgets.max_steps": (int, 1, 10_000, "steps", True, False, "instance", "min"),
    "budgets.max_cost": (int, 1, 1_000_000, "cost-units", True, False, "instance", "min"),
    "budgets.max_transcript_events": (int, 2, 1_000_000, "events", False, False, "site", None),
    "concurrency.max_active": (int, 3, 100_000, "runs", True, False, "instance", "min"),
    "concurrency.max_waiting": (int, 0, 1_000_000, "runs", True, False, "instance", "min"),
    "concurrency.reserved_critical": (int, 1, 1_000, "runs", True, False, "site", None),
    "timeouts.authorization": (float, 0.01, 60, "s", True, False, "instance", "min"),
    "timeouts.policy": (float, 0.01, 60, "s", True, False, "instance", "min"),
    "timeouts.tool_execution": (float, 0.1, 3600, "s", True, False, "instance", "min"),
    "timeouts.sandbox_launch_heavy": (float, 0.1, 600, "s", True, False, "instance", "min"),
    "timeouts.overall_run": (float, 1, 86_400, "s", True, False, "instance", "min"),
    "retry.max_attempts": (int, 1, 10, "attempts", True, False, "instance", "min"),
    "retry.base_delay": (float, 0.001, 10, "s", True, False, "instance", None),
    "retry.max_delay": (float, 0.001, 60, "s", True, False, "instance", None),
    "sandbox.high_risk_tier": (str, None, None, None, False, False, "base", "enum:heavy"),
    "sandbox.generated_code_tier": (str, None, None, None, False, False, "base", "enum:heavy,reject"),
    "sandbox.low_risk_tier": (str, None, None, None, True, False, "environment", "enum:heavy,fast"),
    "approval.required_for_side_effects": (bool, None, None, None, False, False, "base", "true"),
    "approval.ttl_s": (float, 1, 86_400, "s", True, False, "environment", "min"),
    "approval.allow_cached_offline": (bool, None, None, None, True, False, "environment", "false"),
    "audit.export_endpoint": (str, None, None, None, True, True, "site", None),
    "audit.require_remote_anchor": (bool, None, None, None, False, False, "environment", "true"),
    "telemetry.policy_id": (str, None, None, None, True, False, "environment", None),
    "telemetry.trace_sample_rate": (float, 0.0, 1.0, "ratio", True, False, "instance", None),
    "residency.zone": (str, None, None, None, False, False, "environment", None),
    "residency.allowed_failover_zones": (list, None, None, None, False, False, "environment", None),
    "offline.queue_enabled": (bool, None, None, None, True, False, "site", "false"),
    "offline.max_queue": (int, 0, 100_000, "ops", True, False, "site", "min"),
    "trust.max_policy_age_s": (float, 0, 86_400, "s", True, False, "environment", "min"),
    "trust.max_time_skew_s": (float, 0, 3600, "s", True, False, "environment", "min"),
    "health.stall_warning_s": (float, 0.1, 86_400, "s", True, False, "instance", None),
    "health.stall_critical_s": (float, 0.1, 86_400, "s", True, False, "instance", None),
    "health.queue_age_warning_s": (float, 0.01, 3600, "s", True, False, "instance", None),
    "health.queue_age_critical_s": (float, 0.01, 3600, "s", True, False, "instance", None),
    "precedence.policy_version": (str, None, None, None, False, False, "base", None),
}

SECURE_DEFAULTS: dict[str, Any] = {
    "schema_version": SCHEMA_VERSION, "profile": "cloud",
    "budgets": {"max_steps": 10, "max_cost": 100, "max_transcript_events": 256},
    "concurrency": {"max_active": 64, "max_waiting": 256, "reserved_critical": 2},
    "timeouts": {"authorization": 0.5, "policy": 0.25, "tool_execution": 30.0,
                 "sandbox_launch_heavy": 10.0, "overall_run": 300.0},
    "retry": {"max_attempts": 4, "base_delay": 0.05, "max_delay": 2.0},
    "sandbox": {"high_risk_tier": "heavy", "generated_code_tier": "heavy", "low_risk_tier": "fast"},
    "approval": {"required_for_side_effects": True, "ttl_s": 900.0, "allow_cached_offline": False},
    "audit": {"export_endpoint": "secretref://unset", "require_remote_anchor": True},
    "telemetry": {"policy_id": "PK_AGENT_TELEMETRY_POLICY/1.0.0", "trace_sample_rate": 0.1},
    "residency": {"zone": "unassigned", "allowed_failover_zones": []},
    "offline": {"queue_enabled": False, "max_queue": 0},
    "trust": {"max_policy_age_s": 300.0, "max_time_skew_s": 5.0},
    "health": {"stall_warning_s": 60.0, "stall_critical_s": 300.0,
               "queue_age_warning_s": 1.0, "queue_age_critical_s": 5.0},
    "precedence": {"policy_version": "PK_AGENT_PRECEDENCE/1.0.0"},
}


# ------------------------------------------------------------------ parsing
def _no_dupes(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise AgentError("AGT-CFG-001", "duplicate key in configuration", details={"key": k[:64]})
        out[k] = v
    return out


def loads_strict(text: str | bytes) -> dict:
    if isinstance(text, bytes):
        if len(text) > 1 << 20:
            raise AgentError("AGT-CFG-001", "configuration document too large")
        try:
            text = text.decode("utf-8")
        except UnicodeDecodeError:
            raise AgentError("AGT-CFG-001", "configuration is not valid UTF-8") from None
    if len(text) > 1 << 20:
        raise AgentError("AGT-CFG-001", "configuration document too large")
    try:
        doc = json.loads(text, object_pairs_hook=_no_dupes,
                         parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    except AgentError:
        raise
    except (ValueError, RecursionError):
        raise AgentError("AGT-CFG-001", "configuration is not strict JSON") from None
    if not isinstance(doc, dict):
        raise AgentError("AGT-CFG-001", "configuration root must be an object")
    return doc


def flatten(doc: Mapping[str, Any], prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in doc.items():
        if not isinstance(k, str):
            raise AgentError("AGT-CFG-001", "non-string key")
        path = f"{prefix}{k}"
        if isinstance(v, Mapping):
            if path in F:
                raise AgentError("AGT-CFG-001", "object where scalar expected", details={"field": path})
            out.update(flatten(v, path + "."))
        else:
            out[path] = v
    return out


def unflatten(flat: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for path, v in flat.items():
        cur = out
        parts = path.split(".")
        for p in parts[:-1]:
            cur = cur.setdefault(p, {})
        cur[parts[-1]] = copy.deepcopy(v)
    return out


def _check_value(path: str, v: Any) -> None:
    if path not in F:
        raise AgentError("AGT-CFG-001", "unknown configuration field", details={"field": path[:128]})
    typ, lo, hi, _unit, _rel, sensitive, _lock, tighten = F[path]
    if v is None:
        raise AgentError("AGT-CFG-001", "null is not a value; omit the field to inherit", details={"field": path})
    if typ is float and isinstance(v, int) and not isinstance(v, bool):
        v = float(v)
    if typ is int and isinstance(v, bool) or not isinstance(v, typ):
        raise AgentError("AGT-CFG-001", "wrong type", details={"field": path, "expected": typ.__name__})
    if lo is not None and not (lo <= v <= hi):
        raise AgentError("AGT-CFG-001", "value out of range", details={"field": path, "min": lo, "max": hi})
    if typ is list and not all(isinstance(x, str) and x for x in v):
        raise AgentError("AGT-CFG-001", "list items must be non-empty strings", details={"field": path})
    if sensitive and not (isinstance(v, str) and v.startswith("secretref://")):
        raise AgentError("AGT-CFG-001", "sensitive field must be a secretref:// reference", details={"field": path})
    if tighten and tighten.startswith("enum:") and v not in tighten[5:].split(","):
        raise AgentError("AGT-CFG-001", "value not permitted", details={"field": path, "allowed": tighten[5:]})


def validate_document(doc: Mapping[str, Any], *, scope: str) -> dict[str, Any]:
    """Validate one layer document; returns its flattened field map."""
    if scope not in SCOPES:
        raise ValueError(scope)
    flat = flatten(doc)
    sv = flat.get("schema_version")
    if sv is not None and not isinstance(sv, str):
        raise AgentError("AGT-CFG-001", "schema_version must be a string")
    if scope in ("base", "default") and sv not in SUPPORTED_SCHEMAS:
        raise AgentError("AGT-CFG-001", "unsupported or missing schema_version", details={"got": str(sv)[:64]})
    if sv is not None and sv not in SUPPORTED_SCHEMAS:
        raise AgentError("AGT-CFG-001", "unsupported schema_version", details={"got": str(sv)[:64]})
    for path, v in flat.items():
        _check_value(path, v)
        lock = F[path][6]
        if SCOPES.index(scope) > SCOPES.index(lock) and scope != "emergency":
            raise AgentError("AGT-CFG-002", details={"field": path, "scope": scope, "locked_at": lock})
    return flat


def _is_tighter(path: str, old: Any, new: Any) -> bool:
    t = F[path][7]
    if t == "min":
        return new <= old
    if t == "max":
        return new >= old
    if t in ("true", "false"):
        return new == (t == "true") or new == old
    if t and t.startswith("enum:"):
        order = t[5:].split(",")
        return order.index(new) <= order.index(old) if old in order else new == order[0]
    return False


# ------------------------------------------------------------------ profiles
def load_profiles(directory: Path = PROFILE_DIR) -> dict[str, dict]:
    out = {}
    for p in sorted(directory.glob("*.json")):
        doc = loads_strict(p.read_bytes())
        if doc.get("schema") != PROFILE_SCHEMA:
            raise AgentError("AGT-CFG-001", "bad profile schema", details={"file": p.name})
        required = {"context", "applicability", "rationale", "mandatory_capabilities",
                    "prohibited_capabilities", "defaults", "environment", "resource_envelope", "security_posture"}
        missing = required - set(doc)
        if missing:
            raise AgentError("AGT-CFG-001", "profile missing fields", details={"file": p.name, "missing": sorted(missing)})
        if set(doc["mandatory_capabilities"]) & set(doc["prohibited_capabilities"]):
            raise AgentError("AGT-CFG-001", "profile is internally inconsistent", details={"file": p.name})
        validate_document(doc["defaults"], scope="profile")
        out[doc["context"]] = doc
    return out


def capabilities(eff: Mapping[str, Any]) -> set[str]:
    """Capability flags derived from the effective configuration (never from the build)."""
    caps = {"allowlist", "step_budget", "cost_budget", "transcript"}
    if eff["approval.required_for_side_effects"]:
        caps.add("approval_gate")
    caps.add("heavy_sandbox")
    if eff["sandbox.low_risk_tier"] == "fast":
        caps.add("fast_sandbox")
    if eff["offline.queue_enabled"]:
        caps.add("offline_queue")
    if eff["approval.allow_cached_offline"]:
        caps.add("offline_cached_approval")
    if not eff["audit.export_endpoint"].endswith("://unset"):
        caps.add("remote_audit_export")
    if eff["audit.require_remote_anchor"]:
        caps.add("remote_audit_anchor_required")
    if eff["residency.allowed_failover_zones"]:
        caps.add("cross_zone_failover")
    return caps


# ------------------------------------------------------------------ effective config
@dataclass(frozen=True)
class EffectiveConfig:
    values: Mapping[str, Any]           # flattened, read-only
    sources: Mapping[str, str]          # field -> scope that supplied it
    layers: tuple[tuple[str, str], ...]  # (scope, sha256) contributing
    digest: str
    profile: Mapping[str, Any]

    def get(self, path: str) -> Any:
        return self.values[path]

    def as_document(self) -> dict:
        return unflatten(self.values)

    def capabilities(self) -> set[str]:
        return capabilities(self.values)

    def explain(self) -> list[dict[str, Any]]:
        from .redaction import REDACTED
        return [{"field": k, "value": (REDACTED if F[k][5] else self.values[k]), "source": self.sources[k],
                 "unit": F[k][3], "reloadable": F[k][4], "locked_at": F[k][6]} for k in sorted(self.values)]


def _digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def resolve(layers: list[tuple[str, Mapping[str, Any]]], profiles: dict[str, dict] | None = None) -> EffectiveConfig:
    """Merge layers deterministically. Maps merge per field; lists and scalars replace; null is rejected."""
    profiles = profiles if profiles is not None else load_profiles()
    order = [s for s, _ in layers]
    if order != sorted(order, key=SCOPES.index) or len(set(order)) != len(order):
        raise AgentError("AGT-CFG-001", "layers must be unique and in precedence order", details={"order": order})
    values = flatten(SECURE_DEFAULTS)
    sources = {k: "default" for k in values}
    contributing = [("default", _digest(SECURE_DEFAULTS))]
    parsed = [(s, validate_document(d, scope=s), d) for s, d in layers]
    # The profile named by the highest layer that names one (profile field is env-locked).
    profile_name = values["profile"]
    for s, flat, _ in parsed:
        profile_name = flat.get("profile", profile_name)
    if profile_name not in profiles:
        raise AgentError("AGT-CFG-001", "unknown deployment profile", details={"profile": str(profile_name)[:64]})
    prof = profiles[profile_name]
    for k, v in flatten(prof["defaults"]).items():
        values[k], sources[k] = v, "profile"
    contributing.append(("profile", _digest(prof)))
    for scope, flat, doc in parsed:
        for k, v in flat.items():
            if scope == "emergency" and not _is_tighter(k, values[k], v):
                raise AgentError("AGT-CFG-002", "emergency override may only tighten", details={"field": k})
            values[k] = float(v) if F[k][0] is float else v
            sources[k] = scope
        contributing.append((scope, _digest(doc)))
    # cross-field invariants
    if values["health.stall_warning_s"] > values["health.stall_critical_s"]:
        raise AgentError("AGT-CFG-001", "stall warning must not exceed critical")
    if values["health.queue_age_warning_s"] > values["health.queue_age_critical_s"]:
        raise AgentError("AGT-CFG-001", "queue-age warning must not exceed critical")
    if values["retry.base_delay"] > values["retry.max_delay"]:
        raise AgentError("AGT-CFG-001", "retry.base_delay must not exceed retry.max_delay")
    if values["concurrency.reserved_critical"] >= values["concurrency.max_active"]:
        raise AgentError("AGT-CFG-001", "reserved_critical must be below max_active")
    if values["offline.queue_enabled"] and values["offline.max_queue"] == 0:
        raise AgentError("AGT-CFG-001", "offline queue enabled with zero capacity")
    caps = capabilities(values)
    bad = caps & set(prof["prohibited_capabilities"])
    if bad:
        raise AgentError("AGT-CFG-001", "configuration enables capabilities the profile prohibits",
                         details={"profile": profile_name, "prohibited": sorted(bad)})
    missing = set(prof["mandatory_capabilities"]) - caps
    if missing:
        raise AgentError("AGT-CFG-001", "configuration lacks capabilities the profile mandates",
                         details={"profile": profile_name, "missing": sorted(missing)})
    return EffectiveConfig(MappingProxyType(dict(values)), MappingProxyType(sources), tuple(contributing),
                           _digest(values), MappingProxyType(prof))


# ------------------------------------------------------------------ generations + provenance
@dataclass(frozen=True)
class Generation:
    number: int
    config: EffectiveConfig
    provenance: Mapping[str, Any]


class ConfigStore:
    """Immutable configuration generations with atomic CAS activation and a provenance chain."""

    def __init__(self, initial: EffectiveConfig, *, author: str = "bootstrap", clock=time.time,
                 trusted_time=None):
        self._lock = threading.Lock()
        self._clock = clock
        self._trusted_time = trusted_time      # callable -> (epoch, trustworthy: bool)
        self._chain_head = "0" * 64
        self._provenance: list[dict[str, Any]] = []
        self._generations: list[Generation] = []
        self._active: Generation | None = None
        self._activate_locked(initial, author=author, reviewer=None, source="builtin", reason="bootstrap")

    @property
    def active(self) -> Generation:
        return self._active  # single reference read is atomic

    @property
    def provenance(self) -> tuple[dict, ...]:
        return tuple(self._provenance)

    def _now(self) -> tuple[float, bool]:
        if self._trusted_time is None:
            return self._clock(), False
        return self._trusted_time()

    def _activate_locked(self, cfg: EffectiveConfig, *, author, reviewer, source, reason) -> Generation:
        now, trusted = self._now()
        number = len(self._generations)
        prev = self._active
        rec = {
            "schema": "PK_AGENT_CONFIG_PROVENANCE/1",
            "generation": number,
            "config_schema": SCHEMA_VERSION,
            "config_digest": cfg.digest,
            "layers": [list(x) for x in cfg.layers],
            "profile": cfg.profile["context"],
            "source": source,
            "author": author,
            "reviewer": reviewer,
            "activated_at": now,
            "time_trusted": trusted,
            "supersedes": prev.number if prev else None,
            "reason": reason,
            "prev_hash": self._chain_head,
        }
        rec["record_hash"] = _digest(rec)
        gen = Generation(number, cfg, MappingProxyType(rec))
        # evidence first, then pointer switch; both inside the lock => never active without provenance
        self._provenance.append(rec)
        self._generations.append(gen)
        self._chain_head = rec["record_hash"]
        self._active = gen
        return gen

    def activate(self, layers: list[tuple[str, Mapping[str, Any]]], *, expected_generation: int, author: str,
                 reviewer: str | None = None, source: str = "operator", reason: str = "update",
                 profiles: dict | None = None, require_trusted_time: bool = False) -> Generation:
        """Validate the whole candidate, then CAS-switch. On any failure the old generation stays active."""
        if not author or not isinstance(author, str):
            raise AgentError("AGT-CFG-001", "author required")
        candidate = resolve(layers, profiles)            # full validation before touching anything
        with self._lock:
            if self._active.number != expected_generation:
                raise AgentError("AGT-CFG-003", details={"expected": expected_generation, "active": self._active.number})
            _, trusted = self._now()
            if require_trusted_time and not trusted:
                raise AgentError("AGT-TRU-001", "activation time cannot be established from a trusted source")
            return self._activate_locked(candidate, author=author, reviewer=reviewer, source=source, reason=reason)

    def rollback(self, to_generation: int, *, expected_generation: int, author: str) -> Generation:
        with self._lock:
            if self._active.number != expected_generation:
                raise AgentError("AGT-CFG-003")
            target = self._generations[to_generation]
            return self._activate_locked(target.config, author=author, reviewer=None, source="rollback",
                                         reason=f"rollback to generation {to_generation}")

    def verify_provenance(self) -> bool:
        prev = "0" * 64
        for rec in self._provenance:
            body = {k: v for k, v in rec.items() if k != "record_hash"}
            if body["prev_hash"] != prev or _digest(body) != rec["record_hash"]:
                return False
            prev = rec["record_hash"]
        return prev == self._chain_head

    def export_provenance(self) -> dict[str, Any]:
        return {"schema": "PK_AGENT_CONFIG_PROVENANCE_EXPORT/1", "head": self._chain_head,
                "records": [dict(r) for r in self._provenance]}


def load_layer_file(path: str | Path) -> dict:
    return loads_strict(Path(path).read_bytes())
