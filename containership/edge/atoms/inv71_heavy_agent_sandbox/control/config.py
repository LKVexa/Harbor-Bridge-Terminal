"""Declarative configuration: schema, secure defaults, overlays, provenance,
generation-switch activation and rollback (C019, C033-C038, C035, C036, C058-IMP-04).

Layer precedence (lowest -> highest): immutable defaults < environment profile <
site overlay < tenant policy < session request.  Overlays may touch only an
allowlisted field set per layer; security invariants (``LOCKED``) can never be
overridden by any layer.  Every activation records provenance and is
append-only; rollback re-activates a previous generation's exact bytes.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
import hashlib
import hmac
import json
import threading
from typing import Any, Callable, Iterable, Mapping

from .errors import ControlError

MAX_CONFIG_BYTES = 256 * 1024
SCHEMA_ID = "PK_HEAVYBOX_CONFIG/1"

# field -> (type, min, max, privileged_only)
FIELDS: Mapping[str, tuple[type, Any, Any, bool]] = {
    "egress.default": (str, None, None, True),
    "egress.max_rules": (int, 1, 4096, True),
    "session.vcpu": (int, 1, 16, False),
    "session.mem_mib": (int, 128, 65536, False),
    "session.pids_max": (int, 16, 32768, False),
    "session.fds_max": (int, 64, 65536, False),
    "session.disk_bytes": (int, 1 << 20, 1 << 36, False),
    "session.inodes": (int, 64, 1 << 22, False),
    "session.iops": (int, 10, 200_000, False),
    "session.net_mbps": (int, 1, 100_000, False),
    "session.net_pps": (int, 100, 10_000_000, False),
    "session.connections_max": (int, 1, 65536, False),
    "session.wall_clock_s": (int, 10, 86400, False),
    "host.devices": (list, None, None, True),
    "host.mounts": (list, None, None, True),
    "host.debug_console": (bool, None, None, True),
    "service.run_as_root": (bool, None, None, True),
    "api.require_auth": (bool, None, None, True),
    "artifacts.require_signature": (bool, None, None, True),
    "artifacts.manifest_digest": (str, None, None, True),
    "teardown.require_verification": (bool, None, None, True),
    "telemetry.export": (bool, None, None, False),
    "telemetry.sample_rate": (float, 0.0, 1.0, False),
    "residency.region": (str, None, None, True),
    "profile": (str, None, None, True),
}

SECURE_DEFAULTS: Mapping[str, Any] = {
    "egress.default": "deny", "egress.max_rules": 64,
    "session.vcpu": 2, "session.mem_mib": 2048, "session.pids_max": 1024, "session.fds_max": 4096,
    "session.disk_bytes": 1 << 30, "session.inodes": 65536, "session.iops": 2000,
    "session.net_mbps": 100, "session.net_pps": 20000, "session.connections_max": 256,
    "session.wall_clock_s": 3600,
    "host.devices": [], "host.mounts": [], "host.debug_console": False, "service.run_as_root": False,
    "api.require_auth": True, "artifacts.require_signature": True, "artifacts.manifest_digest": "",
    "teardown.require_verification": True, "telemetry.export": True, "telemetry.sample_rate": 0.1,
    "residency.region": "", "profile": "cloud",
}

# Security invariants: exact values no layer may change (C019-IMP-02, C035-IMP-02).
LOCKED: Mapping[str, Any] = {
    "egress.default": "deny", "host.devices": [], "host.mounts": [], "host.debug_console": False,
    "service.run_as_root": False, "api.require_auth": True, "artifacts.require_signature": True,
    "teardown.require_verification": True,
}

LAYERS = ("defaults", "environment", "site", "tenant", "session")
LAYER_ALLOW: Mapping[str, frozenset[str]] = {
    "environment": frozenset({"profile", "session.vcpu", "session.mem_mib", "session.pids_max", "session.fds_max",
                              "session.disk_bytes", "session.inodes", "session.iops", "session.net_mbps",
                              "session.net_pps", "session.connections_max", "session.wall_clock_s",
                              "egress.max_rules", "telemetry.export", "telemetry.sample_rate",
                              "artifacts.manifest_digest"}),
    "site": frozenset({"residency.region", "session.vcpu", "session.mem_mib", "telemetry.export",
                       "telemetry.sample_rate", "session.net_mbps"}),
    "tenant": frozenset({"session.vcpu", "session.mem_mib", "session.wall_clock_s", "session.disk_bytes",
                         "session.connections_max"}),
    "session": frozenset({"session.vcpu", "session.mem_mib", "session.wall_clock_s"}),
}
# Tenant and session layers may only lower resource values relative to the
# layer below them (a request can shrink, never grow, its ceiling).
LOWER_ONLY_LAYERS = frozenset({"tenant", "session"})
PROFILES = frozenset({"cloud", "datacenter", "near-edge", "far-edge"})


def canonical_bytes(obj: Any) -> bytes:
    """The single canonical serialization used for hashing/signing (C022-IMP-02)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest_of(obj: Any) -> str:
    return hashlib.sha256(canonical_bytes(obj)).hexdigest()


def parse(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, (bytes, bytearray)):
        raise ControlError("CONFIG.INVALID", "bytes required")
    if len(raw) > MAX_CONFIG_BYTES:  # bound before parsing (C028-IMP-03)
        raise ControlError("VALIDATION.LIMIT_EXCEEDED", "config too large")

    def no_dupes(pairs):
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise ControlError("CONFIG.INVALID", "duplicate key")
        return dict(pairs)
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=no_dupes,
                         parse_constant=lambda c: (_ for _ in ()).throw(ControlError("CONFIG.INVALID", "NaN/Infinity")))
    except ControlError:
        raise
    except Exception:
        raise ControlError("CONFIG.INVALID", "not UTF-8 JSON") from None
    if not isinstance(doc, dict) or doc.get("schema") != SCHEMA_ID or not isinstance(doc.get("values"), dict):
        raise ControlError("CONFIG.INVALID", "schema/values missing")
    return doc


def validate_values(values: Mapping[str, Any], *, partial: bool) -> None:
    for k, v in values.items():
        if k not in FIELDS:
            raise ControlError("VALIDATION.UNKNOWN_FIELD", k)
        typ, lo, hi, _ = FIELDS[k]
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if typ is int and isinstance(v, bool) or not isinstance(v, typ):
            raise ControlError("CONFIG.INVALID", f"{k}: type")
        if lo is not None and not (lo <= v <= hi):
            raise ControlError("CONFIG.INVALID", f"{k}: out of range")
    if not partial:
        missing = set(FIELDS) - set(values)
        if missing:
            raise ControlError("CONFIG.INVALID", f"missing {sorted(missing)[:3]}")
        for k, want in LOCKED.items():
            if values[k] != want:
                raise ControlError("CONFIG.FORBIDDEN_OVERRIDE", k)
        if values["profile"] not in PROFILES:
            raise ControlError("CONFIG.INVALID", "profile")
        # cross-field (C034-IMP-01/02)
        if values["profile"] == "far-edge" and values["session.mem_mib"] > 8192:
            raise ControlError("CONFIG.INVALID", "far-edge memory ceiling")
        if values["session.vcpu"] * 1024 > values["session.mem_mib"] * 8:
            raise ControlError("CONFIG.INVALID", "vcpu:mem ratio")


def merge(layers: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    """Deterministic layered merge with forbidden-override detection."""
    unknown = set(layers) - set(LAYERS)
    if unknown:
        raise ControlError("CONFIG.INVALID", f"unknown layer {sorted(unknown)}")
    eff = copy.deepcopy(dict(SECURE_DEFAULTS))
    for layer in LAYERS[1:]:
        ov = layers.get(layer) or {}
        validate_values(ov, partial=True)
        for k, v in ov.items():
            if k in LOCKED and v != LOCKED[k]:
                raise ControlError("CONFIG.FORBIDDEN_OVERRIDE", f"{layer}:{k}")
            if k not in LAYER_ALLOW[layer]:
                raise ControlError("CONFIG.FORBIDDEN_OVERRIDE", f"{layer}:{k} not overridable at this layer")
            if layer in LOWER_ONLY_LAYERS and isinstance(v, (int, float)) and not isinstance(v, bool) and v > eff[k]:
                raise ControlError("POLICY.CONSTRAINT_CONFLICT", f"{layer}:{k} may only lower the ceiling")
            eff[k] = copy.deepcopy(v)
    validate_values(eff, partial=False)
    return eff


@dataclass(frozen=True)
class Provenance:
    config_id: str
    version: int
    source: str
    author: str
    approvals: tuple[str, ...]
    created_at: float
    digest: str
    signature: str


@dataclass(frozen=True)
class Activation:
    generation: int
    digest: str
    actor: str
    reason: str
    activated_at: float
    previous_digest: str
    rollback_of: int | None
    cohort: str


class Participant:
    """A component that must hold the same committed generation (node agent,
    firewall/proxy, cgroup helper, policy cache).  Reference implementations
    record what they were told; production ones apply and report back."""

    def __init__(self, name: str, *, accept: bool = True) -> None:
        self.name, self.accept = name, accept
        self.prepared: int | None = None
        self.committed: int = 0
        self.aborted: list[int] = []

    def prepare(self, generation: int, values: Mapping[str, Any]) -> bool:
        if not self.accept:
            return False
        self.prepared = generation
        return True

    def commit(self, generation: int) -> None:
        if self.prepared != generation:
            raise ControlError("CONFIG.STALE_GENERATION", self.name)
        self.committed, self.prepared = generation, None

    def abort(self, generation: int) -> None:
        self.aborted.append(generation)
        self.prepared = None


class ConfigStore:
    """Two-phase generation switch across participants with rollback (C037)."""

    def __init__(self, *, signing_key: bytes, clock: Callable[[], float]) -> None:
        self._key, self._clock = signing_key, clock
        self._versions: dict[str, tuple[dict, Provenance]] = {}
        self.history: list[Activation] = []
        self.generation = 0
        self.active_digest = ""
        self._lock = threading.Lock()

    def sign(self, values: Mapping[str, Any]) -> str:
        return hmac.new(self._key, canonical_bytes(values), hashlib.sha256).hexdigest()

    def stage(self, values: Mapping[str, Any], *, config_id: str, version: int, source: str,
              author: str, approvals: Iterable[str], signature: str) -> Provenance:
        validate_values(values, partial=False)
        if not hmac.compare_digest(signature, self.sign(values)):
            raise ControlError("CONFIG.INVALID", "unsigned or bad signature")
        approvals = tuple(approvals)
        # v4.3.0 review fix: approvals were stored but never checked.
        if not approvals or author in approvals:
            raise ControlError("AUTHZ.DENIED", "config needs at least one approver other than its author")
        d = digest_of(values)
        prov = Provenance(config_id, version, source, author, approvals, self._clock(), d, signature)
        with self._lock:
            self._versions[d] = (copy.deepcopy(dict(values)), prov)
        return prov

    def activate(self, digest: str, *, actor: str, reason: str, participants: Iterable["Participant"],
                 expected_generation: int, cohort: str = "all", rollback_of: int | None = None) -> Activation:
        """Two-phase generation switch: every participant prepares; only if all
        prepared does anyone commit.  Any refusal or exception aborts every
        participant that had prepared, and the previous generation stays active."""
        with self._lock:
            if expected_generation != self.generation:
                raise ControlError("CONFIG.STALE_GENERATION", f"have {self.generation}")
            if digest not in self._versions:
                raise ControlError("CONFIG.INVALID", "unknown staged digest")
            values = copy.deepcopy(self._versions[digest][0])
            new_gen = self.generation + 1
            prepared: list = []
            try:
                for p in participants:
                    if not p.prepare(new_gen, values):
                        raise ControlError("CONFIG.INVALID", "participant rejected prepare")
                    prepared.append(p)
            except Exception:
                for p in prepared:
                    p.abort(new_gen)
                raise
            for p in prepared:
                p.commit(new_gen)
            act = Activation(new_gen, digest, actor, reason, self._clock(), self.active_digest, rollback_of, cohort)
            self.history.append(act)
            self.generation, self.active_digest = new_gen, digest
            return act

    def rollback(self, *, actor: str, reason: str, participants, to_generation: int) -> Activation:
        target = next((a for a in self.history if a.generation == to_generation), None)
        if target is None:
            raise ControlError("CONFIG.INVALID", "no such generation")
        _, prov = self._versions[target.digest]
        values = self._versions[target.digest][0]
        if not hmac.compare_digest(prov.signature, self.sign(values)):  # re-verify before rollback
            raise ControlError("CONFIG.INVALID", "rollback target signature no longer verifies")
        return self.activate(target.digest, actor=actor, reason=reason, participants=participants,
                             expected_generation=self.generation, rollback_of=to_generation)

    def effective(self) -> tuple[dict, Provenance]:
        with self._lock:
            v, p = self._versions[self.active_digest]
            return copy.deepcopy(v), p


def precedence_decide(request: Mapping[str, Any]) -> tuple[str, str]:
    """Deterministic constraint precedence (C019).  Returns (decision, reason_code).

    Order: authentication > artifact integrity > isolation > residency > egress
    policy > teardown verification > tenant policy > safety > SLO > capacity >
    cost > optimization.  Lower-ranked constraints can never relax higher ones.
    """
    order = [
        ("authenticated", False, "DENY", "PREC.AUTHENTICATION"),
        ("artifact_verified", False, "DENY", "PREC.ARTIFACT_INTEGRITY"),
        ("isolation_available", False, "DENY", "PREC.ISOLATION"),
        ("residency_ok", False, "DENY", "PREC.RESIDENCY"),
        ("egress_policy_ok", False, "DENY", "PREC.EGRESS_POLICY"),
        ("teardown_verifiable", False, "DENY", "PREC.TEARDOWN_VERIFICATION"),
        ("tenant_policy_ok", False, "DENY", "PREC.TENANT_POLICY"),
        ("capacity_ok", False, "REJECT_RETRYABLE", "PREC.CAPACITY"),
    ]
    for key, bad, decision, reason in order:
        if request.get(key, False) is bad:
            return decision, reason
    if not request.get("slo_ok", True):
        return "ADMIT_DEGRADED", "PREC.SLO_AT_RISK"
    if not request.get("within_budget", True):
        return "ADMIT_DEGRADED", "PREC.COST_OVER_BUDGET"
    return "ADMIT", "PREC.ALL_SATISFIED"
