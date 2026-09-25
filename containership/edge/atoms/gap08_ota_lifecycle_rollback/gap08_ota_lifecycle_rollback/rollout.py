"""Production-facing OTA rollout state machine for GAP-08.

This module intentionally has no dependency on ``pk_core`` so the safety-critical
rollout mechanics can be unit-tested in isolation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
import re
from typing import Any, Iterable, Mapping
from uuid import uuid4

STATE_SCHEMA = "PK_ROLLOUT_STATE/1"
ROLLOUT_SCHEMA = "PK_ROLLOUT/1"
GATE_SCHEMA = "PK_ROLLOUT_GATE/1"
ROLLBACK_SCHEMA = "PK_ROLLBACK/1"
VERIFICATION_SCHEMA = "PK_VERIFICATION/1"
_GENESIS_HASH = "0" * 64
_SHA256_RE = re.compile(r"^(?:sha256:)?[0-9a-fA-F]{64}$")


class RolloutError(RuntimeError):
    """Base class for rollout failures."""


class BundleRejected(PermissionError, RolloutError):
    """Raised when an update bundle is not verified for rollout."""


class GateFailed(RolloutError):
    """Raised when a rollout cannot continue after a failed health gate."""


class NoRollbackTarget(RolloutError):
    """Raised when a rollout is attempted without a pinned previous version."""


class InvalidRollout(ValueError, RolloutError):
    """Raised when rollout topology or externally supplied state is invalid."""


class StateIntegrityError(RolloutError):
    """Raised when persisted rollout state or its audit chain is inconsistent."""


class RolloutState(str, Enum):
    CREATED = "created"
    PINNED = "pinned"
    READY = "ready"
    RUNNING = "running"
    COMPLETE = "complete"
    DEFERRED = "deferred"
    ROLLED_BACK = "rolled_back"
    ROLLBACK_INCOMPLETE = "rollback_incomplete"


def _canonical_json(value: Mapping[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _clean_node(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRollout(f"node identifiers must be non-empty strings, got {value!r}")
    return value.strip()


def _clean_version(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InvalidRollout(f"{field_name} must be a non-empty string")
    return value.strip()


def _safe_mapping(value: Mapping[str, Any] | None, *, field_name: str) -> dict[str, Any]:
    result = dict(value or {})
    try:
        _canonical_json(result)
    except (TypeError, ValueError) as exc:
        raise InvalidRollout(f"{field_name} must contain only finite JSON-serializable values") from exc
    return result


def _node_set(values: Iterable[str], *, field_name: str) -> set[str]:
    if isinstance(values, (str, bytes)):
        raise InvalidRollout(f"{field_name} must be an iterable of node identifiers, not a string")
    return {_clean_node(node) for node in values}


@dataclass
class Rollout:
    """A staged, gated, automatically reversible fleet update.

    Security and recovery invariants:
    * a rollback target is pinned before any node is touched;
    * verification must be bound to the exact bundle identifier;
    * one node may appear in only one rollout wave;
    * a failed gate permanently closes the rollout and starts rollback;
    * every security-sensitive transition is chained into a tamper-evident log;
    * deferred nodes are explicit and can only be retried through another gate;
    * rollback failures are quarantined instead of being reported as success.
    """

    bundle: str
    waves: list[list[str]]
    rollout_id: str = field(default_factory=lambda: uuid4().hex)
    pinned_target: str | None = None
    verified: bool = False
    verification_digest: str | None = None
    wave_index: int = 0
    versions: dict[str, str] = field(default_factory=dict)
    deferred: list[str] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    audit_log: list[dict[str, Any]] = field(default_factory=list)
    rolled_back: bool = False
    rollback_failed: list[str] = field(default_factory=list)
    quarantined: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.bundle = _clean_version(self.bundle, field_name="bundle")
        self.rollout_id = _clean_version(self.rollout_id, field_name="rollout_id")
        self.waves = self._validated_waves(self.waves)
        normalized_versions: dict[str, str] = {}
        for raw_node, raw_version in self.versions.items():
            node = _clean_node(raw_node)
            if node in normalized_versions:
                raise InvalidRollout(f"duplicate version-map node after normalization: {node}")
            normalized_versions[node] = _clean_version(raw_version, field_name=f"version for {node}")
        self.versions = normalized_versions
        self.deferred = self._unique_nodes(self.deferred)
        self.rollback_failed = self._unique_nodes(self.rollback_failed)
        self.quarantined = self._unique_nodes(self.quarantined)
        if self.pinned_target is not None:
            self.pinned_target = _clean_version(self.pinned_target, field_name="pinned_target")
        if self.verification_digest is not None:
            if not isinstance(self.verification_digest, str) or not _SHA256_RE.fullmatch(self.verification_digest):
                raise InvalidRollout("verification_digest is not a valid SHA-256 value")
            self.verification_digest = self.verification_digest.lower()
        if self.wave_index < 0 or self.wave_index > len(self.waves):
            raise InvalidRollout("wave_index is outside the declared wave range")

    @staticmethod
    def _unique_nodes(values: Iterable[Any]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for raw in values:
            node = _clean_node(raw)
            if node not in seen:
                seen.add(node)
                result.append(node)
        return result

    @classmethod
    def _validated_waves(cls, waves: Any) -> list[list[str]]:
        if not isinstance(waves, list) or not waves:
            raise InvalidRollout("waves must be a non-empty list")
        normalized: list[list[str]] = []
        all_nodes: set[str] = set()
        previous_size = 0
        for index, raw_wave in enumerate(waves, start=1):
            if not isinstance(raw_wave, (list, tuple)) or not raw_wave:
                raise InvalidRollout(f"wave {index} must contain at least one node")
            wave = [_clean_node(node) for node in raw_wave]
            if len(wave) != len(set(wave)):
                raise InvalidRollout(f"wave {index} contains duplicate node identifiers")
            if len(wave) < previous_size:
                raise InvalidRollout("wave sizes must be non-decreasing so the canary is not larger than later waves")
            previous_size = len(wave)
            duplicate = sorted(set(wave) & all_nodes)
            if duplicate:
                raise InvalidRollout(f"nodes scheduled in more than one wave: {duplicate}")
            all_nodes.update(wave)
            normalized.append(wave)
        return normalized

    @property
    def scheduled_nodes(self) -> set[str]:
        return {node for wave in self.waves for node in wave}

    @property
    def state(self) -> RolloutState:
        if self.rolled_back:
            return RolloutState.ROLLBACK_INCOMPLETE if self.rollback_failed else RolloutState.ROLLED_BACK
        if self.wave_index >= len(self.waves):
            return RolloutState.DEFERRED if self.deferred else RolloutState.COMPLETE
        if self.wave_index:
            return RolloutState.RUNNING
        if self.verified and self.pinned_target is not None:
            return RolloutState.READY
        if self.pinned_target is not None:
            return RolloutState.PINNED
        return RolloutState.CREATED

    def _record(self, event: str, **payload: Any) -> dict[str, Any]:
        prev_hash = self.audit_log[-1]["event_hash"] if self.audit_log else _GENESIS_HASH
        body = {
            "schema": "PK_ROLLOUT_AUDIT/1",
            "rollout_id": self.rollout_id,
            "sequence": len(self.audit_log) + 1,
            "event": event,
            "prev_hash": prev_hash,
            "payload": payload,
        }
        body["event_hash"] = hashlib.sha256(_canonical_json(body)).hexdigest()
        self.audit_log.append(body)
        return body

    def verify_audit_chain(self) -> bool:
        prev_hash = _GENESIS_HASH
        for index, event in enumerate(self.audit_log, start=1):
            if not isinstance(event, dict):
                raise StateIntegrityError(f"audit event {index} is not an object")
            candidate = dict(event)
            recorded_hash = candidate.pop("event_hash", None)
            if candidate.get("sequence") != index or candidate.get("prev_hash") != prev_hash:
                raise StateIntegrityError(f"audit event {index} has a broken chain")
            expected_hash = hashlib.sha256(_canonical_json(candidate)).hexdigest()
            if recorded_hash != expected_hash:
                raise StateIntegrityError(f"audit event {index} hash mismatch")
            prev_hash = recorded_hash
        return True

    def _validate_state_invariants(self, *, require_audit: bool = False) -> None:
        if self.pinned_target is None:
            if self.wave_index or self.versions or self.deferred or self.rolled_back:
                raise StateIntegrityError("unpinned rollout contains advanced mutable state")
        else:
            if not self.versions:
                raise StateIntegrityError("pinned rollout has no fleet version map")
            missing = sorted(self.scheduled_nodes - set(self.versions))
            if missing:
                raise StateIntegrityError(f"rollout state is missing scheduled nodes: {missing}")

        if self.wave_index and (not self.verified or self.pinned_target is None):
            raise StateIntegrityError("advanced rollout state is missing admission or rollback pin")

        unknown_deferred = sorted(set(self.deferred) - self.scheduled_nodes)
        if unknown_deferred:
            raise StateIntegrityError(f"deferred list contains unscheduled nodes: {unknown_deferred}")
        unknown_failed = sorted(set(self.rollback_failed) - set(self.versions))
        if unknown_failed:
            raise StateIntegrityError(f"rollback-failed list contains unknown nodes: {unknown_failed}")
        unknown_quarantine = sorted(set(self.quarantined) - set(self.versions))
        if unknown_quarantine:
            raise StateIntegrityError(f"quarantine contains unknown nodes: {unknown_quarantine}")
        if self.rollback_failed and not self.rolled_back:
            raise StateIntegrityError("rollback failures are present before rollback")
        if not set(self.rollback_failed).issubset(self.quarantined):
            raise StateIntegrityError("every rollback failure must be quarantined")

        completed_nodes = {node for wave in self.waves[: self.wave_index] for node in wave}
        if not self.rolled_back and self.pinned_target is not None:
            for node in completed_nodes:
                if node in self.deferred:
                    if self.versions.get(node) != self.pinned_target:
                        raise StateIntegrityError(f"deferred node {node} is not on the pinned target")
                elif self.versions.get(node) != self.bundle:
                    raise StateIntegrityError(f"completed node {node} is not on the rollout bundle")
            future_nodes = self.scheduled_nodes - completed_nodes
            illegally_advanced = sorted(node for node in future_nodes if self.versions.get(node) == self.bundle)
            if illegally_advanced:
                raise StateIntegrityError(f"future-wave nodes already show the rollout bundle: {illegally_advanced}")
        if self.rolled_back:
            for node in self.rollback_failed:
                if self.versions.get(node) != self.bundle:
                    raise StateIntegrityError(f"rollback-failed node {node} is no longer on the failed bundle")
            unexpected_bundle = sorted(
                node for node, version in self.versions.items()
                if version == self.bundle and node not in self.rollback_failed
            )
            if unexpected_bundle:
                raise StateIntegrityError(f"rollback left unreported bundle nodes: {unexpected_bundle}")

        if require_audit:
            self.verify_audit_chain()
            event_types = [event.get("event") for event in self.audit_log]
            if self.pinned_target is not None and "rollback_target_pinned" not in event_types:
                raise StateIntegrityError("pinned state has no rollback-target audit event")
            if self.verified and "bundle_admitted" not in event_types:
                raise StateIntegrityError("verified state has no bundle-admission audit event")
            if self.rolled_back and "rollback" not in event_types:
                raise StateIntegrityError("rolled-back state has no rollback audit event")
            audit_hashes = {event.get("event_hash") for event in self.audit_log}
            for index, verdict in enumerate(self.history, start=1):
                if not isinstance(verdict, dict) or verdict.get("schema") != GATE_SCHEMA:
                    raise StateIntegrityError(f"history entry {index} is not a gate verdict")
                if verdict.get("audit_hash") not in audit_hashes:
                    raise StateIntegrityError(f"history entry {index} is not linked to the audit chain")

    def pin(self, current_versions: Mapping[str, str]) -> str:
        """Pin the rollback target before anything is touched; never recompute it."""
        if self.pinned_target is not None:
            raise StateIntegrityError("rollback target is already pinned and may not be repointed")
        if not isinstance(current_versions, Mapping) or not current_versions:
            raise NoRollbackTarget("cannot pin an empty or missing fleet state")

        fleet: dict[str, str] = {}
        for raw_node, raw_version in current_versions.items():
            node = _clean_node(raw_node)
            if node in fleet:
                raise InvalidRollout(f"duplicate fleet node after normalization: {node}")
            fleet[node] = _clean_version(raw_version, field_name=f"version for {node}")

        unknown = sorted(self.scheduled_nodes - set(fleet))
        if unknown:
            raise InvalidRollout(f"{self.bundle}: waves name nodes outside the fleet: {unknown}")

        distinct = set(fleet.values())
        if len(distinct) != 1:
            raise NoRollbackTarget(f"fleet is not on a single version: {sorted(distinct)}")
        target = next(iter(distinct))
        if target == self.bundle:
            raise NoRollbackTarget(f"fleet already runs {self.bundle}; rollback would be a no-op")

        self.pinned_target = target
        self.versions = fleet
        self._record("rollback_target_pinned", target=target, fleet_nodes=len(fleet))
        return target

    def admit(self, verification: Mapping[str, Any] | None) -> None:
        """Admit only an exact-bundle verification result.

        The verifier must bind its verdict to this rollout's bundle via one of
        ``bundle``, ``artifact``, ``artifact_id``, or ``subject``.  A bare
        ``verified: true`` is intentionally insufficient.
        """
        if self.verified:
            raise StateIntegrityError("bundle admission is immutable once accepted")
        if not isinstance(verification, Mapping) or verification.get("verified") is not True:
            raise BundleRejected(f"{self.bundle}: not admitted without a verified signature")
        if verification.get("kind") != "bundle":
            raise BundleRejected(
                f"{self.bundle}: verification covers kind {verification.get('kind')!r}, not a bundle"
            )
        schema = verification.get("schema")
        if schema is not None and schema != VERIFICATION_SCHEMA:
            raise BundleRejected(f"{self.bundle}: unsupported verification schema {schema!r}")

        subjects = [verification.get(key) for key in ("bundle", "artifact", "artifact_id", "subject")]
        bound_subjects = [value for value in subjects if value is not None]
        if not bound_subjects or self.bundle not in bound_subjects:
            raise BundleRejected(f"{self.bundle}: verification is not bound to this exact bundle")

        digest = verification.get("digest")
        if digest is not None:
            if not isinstance(digest, str) or not _SHA256_RE.fullmatch(digest):
                raise BundleRejected(f"{self.bundle}: verification digest is not a valid SHA-256 value")
            digest = digest.lower()

        self.verified = True
        self.verification_digest = digest
        self._record("bundle_admitted", bundle=self.bundle, digest=digest)

    def _validate_gate_inputs(self, *, healthy: bool, offline: Iterable[str], allowed_nodes: set[str]) -> set[str]:
        if type(healthy) is not bool:
            raise InvalidRollout("healthy must be an explicit bool")
        offline_nodes = _node_set(offline, field_name="offline")
        unexpected = sorted(offline_nodes - allowed_nodes)
        if unexpected:
            raise InvalidRollout(f"offline set includes nodes outside the active gate: {unexpected}")
        return offline_nodes

    def run_wave(
        self,
        *,
        healthy: bool,
        offline: Iterable[str] = (),
        gate_id: str | None = None,
        evidence: Mapping[str, Any] | None = None,
        rollback_failures: Iterable[str] = (),
    ) -> dict[str, Any]:
        """Apply the next wave and gate it; a failing gate starts rollback immediately."""
        if not self.verified:
            raise BundleRejected(f"{self.bundle}: rollout attempted before verification")
        if self.pinned_target is None:
            raise NoRollbackTarget("rollout attempted with no pinned rollback target")
        if self.rolled_back:
            raise GateFailed("rollout already rolled back; start a new rollout")
        if self.wave_index >= len(self.waves):
            return {
                "schema": ROLLOUT_SCHEMA,
                "rollout_id": self.rollout_id,
                "complete": not self.deferred,
                "wave": self.wave_index,
                "deferred": list(self.deferred),
            }

        wave = self.waves[self.wave_index]
        offline_nodes = self._validate_gate_inputs(healthy=healthy, offline=offline, allowed_nodes=set(wave))
        gate_evidence = _safe_mapping(evidence, field_name="gate evidence")
        touched: list[str] = []
        for node in wave:
            if node in offline_nodes:
                if node not in self.deferred:
                    self.deferred.append(node)
                continue
            self.versions[node] = self.bundle
            touched.append(node)

        self.wave_index += 1
        verdict: dict[str, Any] = {
            "schema": GATE_SCHEMA,
            "rollout_id": self.rollout_id,
            "wave": self.wave_index,
            "touched": touched,
            "deferred": list(self.deferred),
            "healthy": healthy,
            "gate_id": gate_id,
            "evidence": gate_evidence,
        }
        event = self._record(
            "wave_gate",
            wave=self.wave_index,
            touched=touched,
            deferred=list(self.deferred),
            healthy=healthy,
            gate_id=gate_id,
            evidence=gate_evidence,
        )
        verdict["audit_hash"] = event["event_hash"]
        self.history.append(verdict)

        if not healthy:
            rollback = self.rollback(
                reason=f"health gate failed after wave {self.wave_index}",
                fail_nodes=rollback_failures,
            )
            verdict["rolled_back"] = True
            verdict["rollback_complete"] = rollback["complete"]
            verdict["rollback_failed"] = rollback["failed"]
        return verdict

    def retry_deferred(
        self,
        *,
        healthy: bool,
        nodes: Iterable[str] | None = None,
        gate_id: str | None = None,
        evidence: Mapping[str, Any] | None = None,
        rollback_failures: Iterable[str] = (),
    ) -> dict[str, Any]:
        """Retry deferred nodes behind their own health gate.

        This closes the common correctness hole where an offline node is recorded
        as deferred forever with no safe catch-up path.
        """
        if self.rolled_back:
            raise GateFailed("rollout already rolled back; deferred nodes cannot be retried")
        if not self.verified or self.pinned_target is None:
            raise RolloutError("deferred retry requires an admitted and pinned rollout")
        if not self.deferred:
            return {
                "schema": GATE_SCHEMA,
                "rollout_id": self.rollout_id,
                "retry": True,
                "touched": [],
                "deferred": [],
                "healthy": healthy,
            }

        requested = set(self.deferred) if nodes is None else _node_set(nodes, field_name="deferred retry nodes")
        unknown = sorted(requested - set(self.deferred))
        if unknown:
            raise InvalidRollout(f"deferred retry names nodes that are not deferred: {unknown}")
        self._validate_gate_inputs(healthy=healthy, offline=(), allowed_nodes=requested)
        gate_evidence = _safe_mapping(evidence, field_name="gate evidence")

        touched = sorted(requested)
        for node in touched:
            self.versions[node] = self.bundle
        self.deferred = [node for node in self.deferred if node not in requested]

        verdict: dict[str, Any] = {
            "schema": GATE_SCHEMA,
            "rollout_id": self.rollout_id,
            "retry": True,
            "wave": self.wave_index,
            "touched": touched,
            "deferred": list(self.deferred),
            "healthy": healthy,
            "gate_id": gate_id,
            "evidence": gate_evidence,
        }
        event = self._record(
            "deferred_gate",
            touched=touched,
            deferred=list(self.deferred),
            healthy=healthy,
            gate_id=gate_id,
            evidence=gate_evidence,
        )
        verdict["audit_hash"] = event["event_hash"]
        self.history.append(verdict)
        if not healthy:
            rollback = self.rollback(
                reason="health gate failed while retrying deferred nodes",
                fail_nodes=rollback_failures,
            )
            verdict["rolled_back"] = True
            verdict["rollback_complete"] = rollback["complete"]
            verdict["rollback_failed"] = rollback["failed"]
        return verdict

    def rollback(self, *, reason: str, fail_nodes: Iterable[str] = ()) -> dict[str, Any]:
        """Revert updated nodes to the pinned target and quarantine failures."""
        if self.pinned_target is None:
            raise NoRollbackTarget("nothing to roll back to")
        reason = _clean_version(reason, field_name="rollback reason")
        candidate = {node for node, version in self.versions.items() if version == self.bundle}
        requested_failures = _node_set(fail_nodes, field_name="rollback failure nodes")
        impossible = sorted(requested_failures - candidate)
        if impossible:
            raise InvalidRollout(f"rollback failure set includes nodes not on the bundle: {impossible}")

        failed = sorted(requested_failures)
        reverted = sorted(candidate - requested_failures)
        for node in reverted:
            self.versions[node] = self.pinned_target

        self.rolled_back = True
        self.rollback_failed = failed
        self.quarantined = sorted(set(self.quarantined) | set(failed))
        event = self._record(
            "rollback",
            target=self.pinned_target,
            reverted=reverted,
            failed=failed,
            reason=reason,
        )
        return {
            "schema": ROLLBACK_SCHEMA,
            "rollout_id": self.rollout_id,
            "target": self.pinned_target,
            "reverted": reverted,
            "failed": failed,
            "quarantined": list(self.quarantined),
            "complete": not failed,
            "reason": reason,
            "audit_hash": event["event_hash"],
        }

    def fleet_on(self, version: str) -> list[str]:
        version = _clean_version(version, field_name="version")
        return sorted(node for node, current in self.versions.items() if current == version)

    def snapshot(self) -> dict[str, Any]:
        """Return crash-recoverable state plus an integrity digest."""
        self._validate_state_invariants(require_audit=True)
        state: dict[str, Any] = {
            "schema": STATE_SCHEMA,
            "rollout_id": self.rollout_id,
            "bundle": self.bundle,
            "waves": [list(wave) for wave in self.waves],
            "pinned_target": self.pinned_target,
            "verified": self.verified,
            "verification_digest": self.verification_digest,
            "wave_index": self.wave_index,
            "versions": dict(self.versions),
            "deferred": list(self.deferred),
            "history": list(self.history),
            "audit_log": list(self.audit_log),
            "rolled_back": self.rolled_back,
            "rollback_failed": list(self.rollback_failed),
            "quarantined": list(self.quarantined),
        }
        digest = hashlib.sha256(_canonical_json(state)).hexdigest()
        return {**state, "state_digest": digest}

    @classmethod
    def from_snapshot(cls, snapshot: Mapping[str, Any]) -> "Rollout":
        """Restore state only when the snapshot digest and audit chain verify."""
        if not isinstance(snapshot, Mapping) or snapshot.get("schema") != STATE_SCHEMA:
            raise StateIntegrityError("unsupported or missing rollout state schema")
        candidate = dict(snapshot)
        recorded_digest = candidate.pop("state_digest", None)
        expected_digest = hashlib.sha256(_canonical_json(candidate)).hexdigest()
        if recorded_digest != expected_digest:
            raise StateIntegrityError("rollout state digest mismatch")

        obj = cls(
            bundle=candidate["bundle"],
            waves=[list(wave) for wave in candidate["waves"]],
            rollout_id=candidate["rollout_id"],
            pinned_target=candidate.get("pinned_target"),
            verified=bool(candidate.get("verified")),
            verification_digest=candidate.get("verification_digest"),
            wave_index=int(candidate.get("wave_index", 0)),
            versions=dict(candidate.get("versions", {})),
            deferred=list(candidate.get("deferred", [])),
            history=list(candidate.get("history", [])),
            audit_log=list(candidate.get("audit_log", [])),
            rolled_back=bool(candidate.get("rolled_back")),
            rollback_failed=list(candidate.get("rollback_failed", [])),
            quarantined=list(candidate.get("quarantined", [])),
        )
        obj._validate_state_invariants(require_audit=True)
        return obj
