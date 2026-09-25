"""Self-contained reconciliation engine for INV-63.

This module deliberately has no dependency on :mod:`pk_core` so the deployment
algorithm can be unit-tested even when the inventory-wide audit framework is
not installed.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
import hashlib
import heapq
import json
from typing import Any

MAX_IDENTIFIER_LENGTH = 256


def _validate_identifier(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise ValueError(f"{field_name} exceeds {MAX_IDENTIFIER_LENGTH} characters")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{field_name} contains control characters")
    return value


def _validate_positive_or_zero_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer, got {value!r}")
    return value


def _validate_positive_int(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer, got {value!r}")
    return value


@dataclass(frozen=True)
class DesiredState:
    """Validated desired state for one logical component."""

    component: str
    version: str
    count: int
    spread: bool = True

    def __post_init__(self) -> None:
        _validate_identifier(self.component, "component")
        _validate_identifier(self.version, "version")
        _validate_positive_or_zero_int(self.count, "count")
        if not isinstance(self.spread, bool):
            raise ValueError(f"spread must be bool, got {self.spread!r}")


@dataclass(frozen=True)
class AuditEvent:
    """One hash-chained audit record.

    The chain is tamper-evident inside the reference implementation. Production
    deployments still need durable, access-controlled storage and external head
    anchoring.
    """

    sequence: int
    kind: str
    details_json: str
    previous_digest: str
    digest: str


Instance = tuple[str, str, str]  # component, version, host
Diff = dict[str, list[Instance]]


@dataclass
class Manager:
    """Deterministic in-memory desired-state reconciler.

    ``hosts`` maps host identifier -> spread label (for example, zone).
    ``actual`` is normalized to immutable tuples.  All externally supplied
    state and actions are validated before mutation, and ``apply`` is
    transactional: validation failure leaves ``actual`` unchanged.
    """

    hosts: Mapping[str, str]
    actual: Sequence[Instance] = field(default_factory=list)
    desired: dict[str, DesiredState] = field(default_factory=dict)
    audit_events: list[AuditEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.hosts, Mapping):
            raise ValueError("hosts must be a mapping of host -> spread label")
        normalized_hosts: dict[str, str] = {}
        for host, label in self.hosts.items():
            h = _validate_identifier(host, "host")
            z = _validate_identifier(label, f"spread label for host {h!r}")
            normalized_hosts[h] = z
        self.hosts = normalized_hosts

        if isinstance(self.actual, (str, bytes)) or not isinstance(self.actual, Sequence):
            raise ValueError("actual must be a sequence of (component, version, host) tuples")
        self.actual = [self._validate_instance(item, allow_unknown_host=False) for item in self.actual]

        normalized_desired: dict[str, DesiredState] = {}
        for component, state in dict(self.desired).items():
            if not isinstance(state, DesiredState):
                raise ValueError("desired values must be DesiredState instances")
            if component != state.component:
                raise ValueError("desired key must equal DesiredState.component")
            normalized_desired[component] = state
        self.desired = normalized_desired

        if self.audit_events:
            raise ValueError("pre-populated audit_events are not accepted; replay through a verified store")

    def _validate_instance(self, item: object, *, allow_unknown_host: bool) -> Instance:
        if (
            isinstance(item, (str, bytes))
            or not isinstance(item, Sequence)
            or len(item) != 3
        ):
            raise ValueError(f"instance must be a 3-item sequence, got {item!r}")
        component = _validate_identifier(item[0], "instance component")
        version = _validate_identifier(item[1], "instance version")
        host = _validate_identifier(item[2], "instance host")
        if not allow_unknown_host and host not in self.hosts:
            raise LookupError(f"instance references unknown host {host!r}")
        return (component, version, host)

    def _validate_runtime_state(self) -> None:
        # Detect direct caller mutation of the public reference implementation
        # fields before making a decision or applying a change. Valid sequence
        # forms are normalized back to tuples so downstream Counter operations
        # cannot be broken by an injected unhashable list.
        normalized = [
            self._validate_instance(item, allow_unknown_host=False)
            for item in self.actual
        ]
        self.actual = normalized

    def _record(self, kind: str, details: Mapping[str, Any]) -> AuditEvent:
        kind = _validate_identifier(kind, "audit event kind")
        details_json = json.dumps(details, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        previous = self.audit_events[-1].digest if self.audit_events else "0" * 64
        sequence = len(self.audit_events) + 1
        envelope = json.dumps(
            {
                "sequence": sequence,
                "kind": kind,
                "details": details_json,
                "previous_digest": previous,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        digest = hashlib.sha256(envelope).hexdigest()
        event = AuditEvent(sequence, kind, details_json, previous, digest)
        self.audit_events.append(event)
        return event

    def verify_audit_chain(self) -> bool:
        previous = "0" * 64
        for expected_sequence, event in enumerate(self.audit_events, start=1):
            if not isinstance(event, AuditEvent):
                return False
            if event.sequence != expected_sequence or event.previous_digest != previous:
                return False
            envelope = json.dumps(
                {
                    "sequence": event.sequence,
                    "kind": event.kind,
                    "details": event.details_json,
                    "previous_digest": event.previous_digest,
                },
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=True,
            ).encode("utf-8")
            if hashlib.sha256(envelope).hexdigest() != event.digest:
                return False
            previous = event.digest
        return True

    def set_desired(self, component: str, version: str, count: int, spread: bool = True) -> DesiredState:
        state = DesiredState(component, version, count, spread)
        if state.count and not self.hosts:
            raise LookupError("no hosts available for a non-zero desired count")
        self.desired[state.component] = state
        self._record(
            "desired_state_set",
            {
                "component": state.component,
                "version": state.version,
                "count": state.count,
                "spread": state.spread,
            },
        )
        return state

    def diff(self, component: str, version: str, count: int, spread: bool = True,
             eligible_hosts: Sequence[str] | None = None) -> Diff:
        """Compute the minimal start/stop plan.

        ``eligible_hosts`` (added in 4.3.0, optional, backward compatible)
        restricts placement to a subset of hosts -- used by the service layer
        for residency and quarantine constraints.  Current-version instances on
        ineligible hosts are stopped and replaced.
        """
        self._validate_runtime_state()
        state = DesiredState(component, version, count, spread)
        if eligible_hosts is None:
            allowed = set(self.hosts)
        else:
            if isinstance(eligible_hosts, (str, bytes)):
                raise ValueError("eligible_hosts must be a sequence of host ids")
            allowed = {_validate_identifier(h, "eligible host") for h in eligible_hosts}
            unknown = allowed - set(self.hosts)
            if unknown:
                raise LookupError(f"eligible_hosts references unknown hosts {sorted(unknown)!r}")
        if state.count and not allowed:
            raise LookupError("no hosts to place instances on")

        mine = [a for a in self.actual if a[0] == state.component]
        stale = [a for a in mine if a[1] != state.version or a[2] not in allowed]
        good = [a for a in mine if a[1] == state.version and a[2] in allowed]

        # Stop stale instances first; then trim excess current-version replicas.
        stops = list(stale) + good[state.count :]
        retained = good[: state.count]
        starts: list[Instance] = []

        zone_counts = Counter(self.hosts[h] for _, _, h in retained)
        host_counts = Counter(h for _, _, h in retained)
        hosts = sorted(allowed)
        # INV-63-C066: heap-based placement.  Selects exactly the same host as
        # min(hosts, key=(zone_count, host_count, host)) -- proven equivalent by
        # tests/test_manager.py::PlacementEquivalenceTest::test_heap_placement_matches_reference -- but in
        # O(count * zones + count * log hosts) instead of O(count * hosts).
        need = state.count - len(retained)
        if need > 0:
            if state.spread:
                zone_heaps: dict[str, list[tuple[int, str]]] = {}
                for h in hosts:
                    zone_heaps.setdefault(self.hosts[h], []).append((host_counts[h], h))
                for heap in zone_heaps.values():
                    heapq.heapify(heap)
                for _ in range(need):
                    zone = min(zone_heaps, key=lambda z: (zone_counts[z],) + zone_heaps[z][0])
                    count_h, host = heapq.heappop(zone_heaps[zone])
                    heapq.heappush(zone_heaps[zone], (count_h + 1, host))
                    zone_counts[zone] += 1
                    host_counts[host] += 1
                    starts.append((state.component, state.version, host))
            else:
                heap = [(host_counts[h], h) for h in hosts]
                heapq.heapify(heap)
                for _ in range(need):
                    count_h, host = heapq.heappop(heap)
                    heapq.heappush(heap, (count_h + 1, host))
                    zone_counts[self.hosts[host]] += 1
                    host_counts[host] += 1
                    starts.append((state.component, state.version, host))

        result: Diff = {"start": starts, "stop": stops}
        self._record(
            "reconcile_diff",
            {
                "component": state.component,
                "version": state.version,
                "count": state.count,
                "spread": state.spread,
                "start": [list(x) for x in starts],
                "stop": [list(x) for x in stops],
            },
        )
        return result

    def _validate_diff(self, diff: object) -> tuple[list[Instance], list[Instance]]:
        if not isinstance(diff, Mapping):
            raise ValueError("diff must be a mapping with 'start' and 'stop'")
        extra = set(diff) - {"start", "stop"}
        missing = {"start", "stop"} - set(diff)
        if extra or missing:
            raise ValueError(f"diff keys must be exactly 'start' and 'stop'; missing={sorted(missing)}, extra={sorted(extra)}")
        starts_raw = diff["start"]
        stops_raw = diff["stop"]
        if isinstance(starts_raw, (str, bytes)) or not isinstance(starts_raw, Sequence):
            raise ValueError("diff['start'] must be a sequence")
        if isinstance(stops_raw, (str, bytes)) or not isinstance(stops_raw, Sequence):
            raise ValueError("diff['stop'] must be a sequence")
        starts = [self._validate_instance(x, allow_unknown_host=False) for x in starts_raw]
        stops = [self._validate_instance(x, allow_unknown_host=False) for x in stops_raw]
        return starts, stops

    def apply(self, diff: object) -> None:
        self._validate_runtime_state()
        starts, stops = self._validate_diff(diff)

        # Validate against a copy before changing live state. Counter handles
        # duplicate instances correctly, so over-stopping is detected.
        remaining = Counter(self.actual)
        remaining.subtract(Counter(stops))
        if any(value < 0 for value in remaining.values()):
            raise LookupError("diff stops instances that are not running; refusing to apply")

        next_state = list(self.actual)
        for stop in stops:
            next_state.remove(stop)
        next_state.extend(starts)

        # Final validation is a last fail-closed guard before commit.
        for item in next_state:
            self._validate_instance(item, allow_unknown_host=False)
        self.actual = next_state
        self._record(
            "diff_applied",
            {
                "start": [list(x) for x in starts],
                "stop": [list(x) for x in stops],
                "result_count": len(self.actual),
            },
        )

    def reconcile(self, component: str) -> Diff:
        component = _validate_identifier(component, "component")
        try:
            state = self.desired[component]
        except KeyError as exc:
            raise LookupError(f"no desired state stored for component {component!r}") from exc
        if not isinstance(state, DesiredState) or state.component != component:
            raise ValueError(f"stored desired state for {component!r} is invalid")
        result = self.diff(state.component, state.version, state.count, state.spread)
        self.apply(result)
        return result

    def rollout(self, component: str, version: str, max_unavailable: int = 1) -> tuple[int, int]:
        """Replace old instances in bounded batches.

        Returns ``(batch_count, worst_unavailable)``.  Unrelated components are
        untouched.  This reference engine models a successful start after each
        stop; production integration still needs start-failure/rollback logic.
        """
        self._validate_runtime_state()
        component = _validate_identifier(component, "component")
        version = _validate_identifier(version, "version")
        max_unavailable = _validate_positive_int(max_unavailable, "max_unavailable")

        batches = 0
        worst_unavailable = 0
        while True:
            old = [a for a in self.actual if a[0] == component and a[1] != version][:max_unavailable]
            if not old:
                return batches, worst_unavailable

            total_before = sum(1 for a in self.actual if a[0] == component)
            next_state = list(self.actual)
            for item in old:
                next_state.remove(item)
            unavailable = total_before - sum(1 for a in next_state if a[0] == component)
            worst_unavailable = max(worst_unavailable, unavailable)

            replacements = [(component, version, item[2]) for item in old]
            next_state.extend(replacements)
            self.actual = next_state
            batches += 1
            self._record(
                "rollout_batch",
                {
                    "component": component,
                    "version": version,
                    "batch": batches,
                    "max_unavailable": max_unavailable,
                    "replaced": [list(x) for x in old],
                    "started": [list(x) for x in replacements],
                    "unavailable": unavailable,
                },
            )
