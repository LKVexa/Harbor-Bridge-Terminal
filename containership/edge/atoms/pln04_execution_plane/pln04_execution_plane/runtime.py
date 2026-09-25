"""Dependency-free execution-plane runtime primitives for PLN-04.

This module contains the state machine that can be unit-tested without the
external ``pk_core`` certification framework.  ``component.py`` adapts these
primitives into the wider Post-Kubernetes checklist/gate system.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import hashlib
import json
import threading
import time
from types import MappingProxyType
from typing import Callable, Mapping

#: Isolation tiers, ordered weakest to strongest for this policy profile.
TIERS = ("process", "wasm", "unikernel", "microvm", "vm")

#: Minimum tier each trust class requires.
TRUST_CLASSES = {
    "trusted": "process",
    "first-party": "wasm",
    "third-party": "unikernel",
    "untrusted": "microvm",
    "hostile": "vm",
}


class ExecutionPlaneError(RuntimeError):
    """Base exception for execution-plane admission/lifecycle failures."""


class NoSufficientTier(ExecutionPlaneError):
    """No currently attested tier satisfies the requested trust class."""


class AdmissionConflict(ExecutionPlaneError):
    """An existing workload cannot be changed in-place safely."""


class CapacityExceeded(ExecutionPlaneError):
    """The node or tenant admission ceiling has been reached."""


class ResidentTierUnattested(ExecutionPlaneError):
    """A resident workload's tier lost attestation and is quarantined."""


@dataclass(frozen=True, slots=True)
class InstanceRecord:
    """Immutable snapshot of one admitted workload instance."""

    workload: str
    tenant: str
    trust_class: str
    tier: str
    state: str
    generation: int


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Hash-chained security/lifecycle event."""

    sequence: int
    timestamp_ns: int
    kind: str
    details: Mapping[str, object]
    previous_hash: str
    event_hash: str


def _require_identifier(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty, non-whitespace string")
    if len(value) > 256:
        raise ValueError(f"{name} must not exceed 256 characters")
    if any(ord(char) < 32 or ord(char) == 127 for char in value):
        raise ValueError(f"{name} must not contain ASCII control characters")
    return value


def _require_tier(tier: object) -> str:
    if not isinstance(tier, str) or tier not in TIERS:
        raise ValueError(f"unknown tier: {tier!r}")
    return tier


def _canonical_event_bytes(
    sequence: int,
    timestamp_ns: int,
    kind: str,
    details: Mapping[str, object],
    previous_hash: str,
) -> bytes:
    payload = {
        "details": dict(details),
        "kind": kind,
        "previous_hash": previous_hash,
        "sequence": sequence,
        "timestamp_ns": timestamp_ns,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class Node:
    """Thread-safe attested tier catalogue and resident-instance registry.

    The bounded defaults are intentionally conservative safety limits rather
    than a capacity recommendation.  Production deployments should supply
    validated site-specific ceilings.
    """

    def __init__(
        self,
        tiers: Mapping[str, bool],
        *,
        max_instances: int = 4096,
        per_tenant_limit: int = 1024,
        clock_ns: Callable[[], int] | None = None,
        audit_limit: int = 65536,
    ) -> None:
        if not isinstance(tiers, Mapping):
            raise TypeError("tiers must be a mapping of tier name to bool")
        unknown = set(tiers) - set(TIERS)
        if unknown:
            raise ValueError(f"unknown tiers: {sorted(unknown)}")
        invalid_values = {name: value for name, value in tiers.items() if type(value) is not bool}
        if invalid_values:
            raise TypeError(f"tier attestation values must be bool: {invalid_values!r}")
        if not isinstance(max_instances, int) or isinstance(max_instances, bool) or max_instances < 1:
            raise ValueError("max_instances must be a positive integer")
        if not isinstance(per_tenant_limit, int) or isinstance(per_tenant_limit, bool) or per_tenant_limit < 1:
            raise ValueError("per_tenant_limit must be a positive integer")
        if per_tenant_limit > max_instances:
            raise ValueError("per_tenant_limit cannot exceed max_instances")
        if not isinstance(audit_limit, int) or isinstance(audit_limit, bool) or audit_limit < 16:
            raise ValueError("audit_limit must be an integer >= 16")
        if clock_ns is not None and not callable(clock_ns):
            raise TypeError("clock_ns must be callable")

        self._tiers = dict(tiers)
        self._instances: dict[str, InstanceRecord] = {}
        self._max_instances = max_instances
        self._per_tenant_limit = per_tenant_limit
        self._clock_ns = clock_ns or time.time_ns
        self._lock = threading.RLock()
        self._audit: deque[AuditEvent] = deque()
        self._audit_head = "0" * 64
        # 4.3.0: the in-memory chain is bounded.  When the oldest event is
        # evicted its hash becomes the verification base, so verification
        # still covers every retained event and the head.  Durable, complete
        # history is the job of observability.DurableAuditSink (M19).
        self._audit_limit = audit_limit
        self._audit_base = "0" * 64
        self._audit_sequence = 0

    @property
    def max_instances(self) -> int:
        return self._max_instances

    @property
    def per_tenant_limit(self) -> int:
        return self._per_tenant_limit

    @property
    def instances(self) -> Mapping[str, InstanceRecord]:
        """Read-only point-in-time resident instance map."""
        with self._lock:
            return MappingProxyType(dict(self._instances))

    def instance(self, workload: str) -> InstanceRecord | None:
        _require_identifier(workload, "workload")
        with self._lock:
            return self._instances.get(workload)

    def attested(self) -> list[str]:
        """Return present tiers whose current attestation state is true."""
        with self._lock:
            return [tier for tier in TIERS if self._tiers.get(tier) is True]

    def catalogue(self) -> Mapping[str, bool]:
        """Return a read-only point-in-time tier-attestation snapshot."""
        with self._lock:
            return MappingProxyType(dict(self._tiers))

    def fail_attestation(self, tier: str) -> tuple[str, ...]:
        """Fail a configured tier closed and quarantine its residents."""
        tier = _require_tier(tier)
        with self._lock:
            if tier not in self._tiers:
                raise ValueError(f"tier is not configured on this node: {tier!r}")
            self._tiers[tier] = False
            affected: list[str] = []
            for workload, record in tuple(self._instances.items()):
                if record.tier == tier and record.state == "active":
                    self._instances[workload] = replace(record, state="quarantined")
                    affected.append(workload)
            self._emit("attestation_failed", tier=tier, affected=sorted(affected))
            return tuple(sorted(affected))

    def restore_attestation(self, tier: str) -> None:
        """Restore catalogue eligibility for future admissions.

        Existing quarantined residents are deliberately *not* reactivated;
        recovery requires teardown/recreation so stale execution state cannot
        silently resume after a trust failure.
        """
        tier = _require_tier(tier)
        with self._lock:
            if tier not in self._tiers:
                raise ValueError(f"tier is not configured on this node: {tier!r}")
            self._tiers[tier] = True
            self._emit("attestation_restored", tier=tier)

    def audit_events(self) -> tuple[AuditEvent, ...]:
        with self._lock:
            return tuple(self._audit)

    def verify_audit_chain(self) -> bool:
        """Verify the in-memory event chain from genesis through the head."""
        with self._lock:
            previous = self._audit_base
            for event in self._audit:
                if event.previous_hash != previous:
                    return False
                expected = hashlib.sha256(
                    _canonical_event_bytes(
                        event.sequence,
                        event.timestamp_ns,
                        event.kind,
                        event.details,
                        event.previous_hash,
                    )
                ).hexdigest()
                if expected != event.event_hash:
                    return False
                previous = event.event_hash
            return previous == self._audit_head

    def _tenant_count(self, tenant: str) -> int:
        return sum(1 for record in self._instances.values() if record.tenant == tenant)

    def _emit(self, kind: str, **details: object) -> None:
        sequence = self._audit_sequence + 1
        timestamp_ns = int(self._clock_ns())
        previous = self._audit_head
        event_hash = hashlib.sha256(
            _canonical_event_bytes(sequence, timestamp_ns, kind, details, previous)
        ).hexdigest()
        event = AuditEvent(
            sequence=sequence,
            timestamp_ns=timestamp_ns,
            kind=kind,
            details=MappingProxyType(dict(details)),
            previous_hash=previous,
            event_hash=event_hash,
        )
        self._audit.append(event)
        self._audit_head = event_hash
        self._audit_sequence = sequence
        while len(self._audit) > self._audit_limit:
            self._audit_base = self._audit.popleft().event_hash

    # -- 4.3.0 plane integration hooks (used by plane.ExecutionPlane) -------
    def put_instance(self, record: InstanceRecord) -> None:
        """Record a provider-confirmed instance (called only by the plane)."""
        if not isinstance(record, InstanceRecord):
            raise TypeError("record must be an InstanceRecord")
        _require_tier(record.tier)
        with self._lock:
            self._instances[record.workload] = record

    def drop_instance(self, workload: str) -> None:
        with self._lock:
            self._instances.pop(workload, None)

    def tenant_count(self, tenant: str) -> int:
        with self._lock:
            return self._tenant_count(tenant)


def select_tier(node: Node, trust_class: str) -> str:
    """Pure policy decision: weakest attested tier satisfying ``trust_class``."""
    if trust_class not in TRUST_CLASSES:
        raise ValueError(f"unknown trust class: {trust_class!r}")
    floor = TIERS.index(TRUST_CLASSES[trust_class])
    with node._lock:
        for tier in TIERS[floor:]:
            if node._tiers.get(tier) is True:
                return tier
        attested = [t for t in TIERS if node._tiers.get(t) is True]
    raise NoSufficientTier(
        f"trust class {trust_class!r} needs at least {TIERS[floor]!r}; node attests {attested}"
    )


def admit(node: Node, workload: str, tenant: str, trust_class: str) -> str:
    """Admit a workload to the weakest currently attested sufficient tier.

    Re-admission is safe and idempotent only while the same tenant still owns
    the workload and its resident tier remains sufficient.  The function never
    silently downgrades isolation and never migrates a live workload across
    tiers; a stronger reclassification that needs another tier must be handled
    as an explicit teardown/recreate transaction by the caller.
    """
    if not isinstance(node, Node):
        raise TypeError("node must be a Node")
    workload = _require_identifier(workload, "workload")
    tenant = _require_identifier(tenant, "tenant")
    if trust_class not in TRUST_CLASSES:
        raise ValueError(f"unknown trust class: {trust_class!r}")

    requested_floor = TIERS.index(TRUST_CLASSES[trust_class])
    with node._lock:
        existing = node._instances.get(workload)
        if existing is not None:
            if existing.tenant != tenant:
                raise PermissionError(f"{workload}: already admitted for another tenant")
            if existing.state != "active" or node._tiers.get(existing.tier) is not True:
                if existing.state == "active":
                    node._instances[workload] = replace(existing, state="quarantined")
                raise ResidentTierUnattested(
                    f"{workload}: resident tier {existing.tier!r} is not trusted; teardown/recreate required"
                )
            current_tier_index = TIERS.index(existing.tier)
            if current_tier_index < requested_floor:
                raise AdmissionConflict(
                    f"{workload}: live tier {existing.tier!r} is below the new floor "
                    f"{TRUST_CLASSES[trust_class]!r}; teardown/recreate required"
                )

            # Preserve the stronger of the old and newly requested policy
            # labels; a weaker re-admission request can never downgrade policy.
            old_floor = TIERS.index(TRUST_CLASSES[existing.trust_class])
            if requested_floor > old_floor:
                node._instances[workload] = replace(existing, trust_class=trust_class)
                existing = node._instances[workload]
                node._emit(
                    "workload_reclassified",
                    workload=workload,
                    tenant=tenant,
                    trust_class=existing.trust_class,
                    tier=existing.tier,
                )
            else:
                node._emit(
                    "admission_reused",
                    workload=workload,
                    tenant=tenant,
                    trust_class=existing.trust_class,
                    tier=existing.tier,
                )
            return existing.tier

        if len(node._instances) >= node._max_instances:
            raise CapacityExceeded(f"node admission limit {node._max_instances} reached")
        if node._tenant_count(tenant) >= node._per_tenant_limit:
            raise CapacityExceeded(
                f"tenant {tenant!r} admission limit {node._per_tenant_limit} reached"
            )

        for tier in TIERS[requested_floor:]:
            if node._tiers.get(tier) is True:
                node._instances[workload] = InstanceRecord(
                    workload=workload,
                    tenant=tenant,
                    trust_class=trust_class,
                    tier=tier,
                    state="active",
                    generation=1,
                )
                node._emit(
                    "workload_admitted",
                    workload=workload,
                    tenant=tenant,
                    trust_class=trust_class,
                    tier=tier,
                )
                return tier

        attested = [tier for tier in TIERS if node._tiers.get(tier) is True]
        node._emit(
            "admission_refused",
            workload=workload,
            tenant=tenant,
            trust_class=trust_class,
            minimum_tier=TIERS[requested_floor],
            attested=attested,
        )
        raise NoSufficientTier(
            f"{workload}: trust class {trust_class!r} needs at least {TIERS[requested_floor]!r}; "
            f"node attests {attested}"
        )


def teardown(
    node: Node,
    workload: str,
    tenant: str | None = None,
    *,
    privileged: bool = False,
) -> bool:
    """Release a resident tier instance with ownership enforcement.

    Tenant-scoped callers must provide their tenant id.  Control-plane callers
    may omit it only when they explicitly set ``privileged=True``.  Missing
    workloads are an idempotent no-op and return ``False``.
    """
    if not isinstance(node, Node):
        raise TypeError("node must be a Node")
    workload = _require_identifier(workload, "workload")
    if tenant is not None:
        tenant = _require_identifier(tenant, "tenant")
    if type(privileged) is not bool:
        raise TypeError("privileged must be bool")
    if tenant is None and not privileged:
        raise PermissionError("tenant is required unless privileged=True")

    with node._lock:
        existing = node._instances.get(workload)
        if existing is None:
            return False
        if tenant is not None and existing.tenant != tenant:
            raise PermissionError(f"{workload}: owned by another tenant")
        del node._instances[workload]
        node._emit(
            "workload_torn_down",
            workload=workload,
            tenant=existing.tenant,
            tier=existing.tier,
            prior_state=existing.state,
            privileged=bool(privileged),
        )
        return True
