"""Runtime primitives for GAP-03 topology-aware scheduling.

This module intentionally has no ``pk_core`` dependency.  It contains the
runtime topology, fair-share, and candidate-scoring logic; ``component.py`` is
only the conformance/gate adapter used by the wider Post-Kubernetes suite.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from threading import RLock
from types import MappingProxyType
from typing import Iterable, Mapping

# Locality classes are deliberately sparse so future measured-latency
# refinement can fit between the static classes without changing their order.
LEVEL_COST: Mapping[str, int] = MappingProxyType({"rack": 1, "site": 10, "region": 100})
MAX_LOCALITY_COST = 1 + LEVEL_COST["region"]
# A used failure domain must always sort behind any unused domain when spreading
# is requested, even when the unused domain is cross-region.
SPREAD_PENALTY = MAX_LOCALITY_COST + 1


class NotInTopology(KeyError):
    """Raised when a node is absent from the declared topology."""


class TopologyConflict(ValueError):
    """Raised when a node is silently re-parented without explicit replacement."""


class ShareViolation(PermissionError):
    """Raised when a claim would violate capacity or another tenant's reservation."""


class ReservationOversubscribed(ShareViolation):
    """Raised when declared reservations cannot fit in the configured capacity."""


class StaleFairShare(ShareViolation):
    """Raised when a commit uses a fairness verdict from an obsolete ledger state."""


def _validate_label(kind: str, value: object, *, forbid_slash: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{kind} must be a string, got {type(value).__name__}")
    if not value or value != value.strip():
        raise ValueError(f"{kind} must be a non-empty, trimmed string: {value!r}")
    if forbid_slash and "/" in value:
        raise ValueError(f"{kind} cannot contain '/': {value!r}")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{kind} cannot contain control characters: {value!r}")
    return value


def _validate_non_negative_int(kind: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{kind} must be a non-negative integer, got {value!r}")
    return value


def _validate_positive_int(kind: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{kind} must be a positive integer, got {value!r}")
    return value


@dataclass(frozen=True)
class TopologySnapshot:
    """Immutable point-in-time topology used for deterministic scoring."""

    nodes: Mapping[str, tuple[str, str, str]]
    generation: int

    def path(self, node: str) -> tuple[str, str, str]:
        _validate_label("node", node)
        try:
            return self.nodes[node]
        except KeyError as exc:
            raise NotInTopology(f"{node} is not in the declared topology") from exc

    def cost(self, a: str, b: str) -> int:
        """Return deterministic locality cost.

        Ordering is strict: same node < same rack < same site < same region <
        cross-region.
        """
        pa = self.path(a)
        pb = self.path(b)
        if a == b:
            return 0
        ra, sa, ka = pa
        rb, sb, kb = pb
        if ra != rb:
            return 1 + LEVEL_COST["region"]
        if sa != sb:
            return 1 + LEVEL_COST["site"]
        if ka != kb:
            return 1 + LEVEL_COST["rack"]
        return 1

    def domain(self, node: str) -> str:
        region, site, _ = self.path(node)
        return f"{region}/{site}"


@dataclass
class Topology:
    """Mutable region/site/rack topology with explicit generation tracking."""

    nodes: dict[str, tuple[str, str, str]] = field(default_factory=dict)
    generation: int = 0
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        original = dict(self.nodes)
        self.nodes = {}
        for node, path in original.items():
            if not isinstance(path, (tuple, list)) or len(path) != 3:
                raise ValueError(f"topology path for {node!r} must be (region, site, rack)")
            self.place(node, path[0], path[1], path[2])
        # Construction is generation zero; only mutations after construction
        # advance it.
        self.generation = 0

    def place(
        self,
        node: str,
        region: str,
        site: str,
        rack: str,
        *,
        replace: bool = False,
    ) -> None:
        node = _validate_label("topology node", node)
        region = _validate_label("topology region", region, forbid_slash=True)
        site = _validate_label("topology site", site, forbid_slash=True)
        rack = _validate_label("topology rack", rack, forbid_slash=True)
        new_path = (region, site, rack)
        with self._lock:
            previous = self.nodes.get(node)
            if previous == new_path:
                return
            if previous is not None and not replace:
                raise TopologyConflict(
                    f"{node}: topology rewrite {previous!r} -> {new_path!r} requires replace=True"
                )
            self.nodes[node] = new_path
            self.generation += 1

    def path(self, node: str) -> tuple[str, str, str]:
        return self.snapshot().path(node)

    def cost(self, a: str, b: str) -> int:
        return self.snapshot().cost(a, b)

    def domain(self, node: str) -> str:
        return self.snapshot().domain(node)

    def snapshot(self) -> TopologySnapshot:
        with self._lock:
            validated: dict[str, tuple[str, str, str]] = {}
            for node, path in self.nodes.items():
                node = _validate_label("topology node", node)
                if not isinstance(path, (tuple, list)) or len(path) != 3:
                    raise ValueError(f"topology path for {node!r} must be (region, site, rack)")
                region = _validate_label("topology region", path[0], forbid_slash=True)
                site = _validate_label("topology site", path[1], forbid_slash=True)
                rack = _validate_label("topology rack", path[2], forbid_slash=True)
                validated[node] = (region, site, rack)
            return TopologySnapshot(MappingProxyType(validated), self.generation)


@dataclass(frozen=True)
class FairnessVerdict:
    """Explainable, non-mutating fair-share admission decision."""

    tenant: str
    requested_slots: int
    allowed: bool
    reason: str
    capacity: int
    total_used: int
    free_capacity: int
    reserved_slots: int
    held_slots: int
    own_reserved_headroom: int
    protected_for_other_tenants: int
    surplus_available: int
    state_token: str


@dataclass
class FairShare:
    """Thread-safe in-process fair-share ledger.

    Reservations may be declared above capacity so configuration can be loaded
    and diagnosed, but claims fail closed while the reservation set is
    oversubscribed.  This prevents the first claimant from consuming capacity
    that the configuration simultaneously promises to another tenant.
    """

    reserved: dict[str, int] = field(default_factory=dict)
    used: dict[str, int] = field(default_factory=dict)
    capacity: int = 0
    _lock: RLock = field(default_factory=RLock, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.capacity = _validate_non_negative_int("capacity", self.capacity)
        self.reserved = self._validated_ledger("reserved", self.reserved)
        self.used = self._validated_ledger("used", self.used)
        if sum(self.used.values()) > self.capacity:
            raise ValueError(
                f"used slots ({sum(self.used.values())}) exceed capacity ({self.capacity})"
            )

    @staticmethod
    def _validated_ledger(kind: str, values: Mapping[str, int]) -> dict[str, int]:
        if not isinstance(values, Mapping):
            raise ValueError(f"{kind} must be a mapping")
        result: dict[str, int] = {}
        for tenant, slots in values.items():
            tenant = _validate_label("tenant", tenant)
            result[tenant] = _validate_non_negative_int(f"{kind}[{tenant}]", slots)
        return result

    def _assert_state_locked(self) -> None:
        _validate_non_negative_int("capacity", self.capacity)
        self._validated_ledger("reserved", self.reserved)
        self._validated_ledger("used", self.used)
        total_used = sum(self.used.values())
        if total_used > self.capacity:
            raise ValueError(f"used slots ({total_used}) exceed capacity ({self.capacity})")

    def _state_token_locked(self) -> str:
        payload = {
            "capacity": self.capacity,
            "reserved": sorted(self.reserved.items()),
            "used": sorted(self.used.items()),
        }
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def state_token(self) -> str:
        """Return a deterministic token for optimistic score-to-commit validation."""
        with self._lock:
            self._assert_state_locked()
            return self._state_token_locked()

    def set_capacity(self, capacity: int) -> None:
        """Safely update local capacity without permitting used-capacity truncation."""
        capacity = _validate_non_negative_int("capacity", capacity)
        with self._lock:
            self._assert_state_locked()
            if sum(self.used.values()) > capacity:
                raise ValueError("capacity cannot be reduced below currently used slots")
            self.capacity = capacity

    def set_reservation(self, tenant: str, slots: int) -> None:
        """Safely update a tenant reservation; oversubscription remains diagnosable/fail-closed."""
        tenant = _validate_label("tenant", tenant)
        slots = _validate_non_negative_int("slots", slots)
        with self._lock:
            self._assert_state_locked()
            self.reserved[tenant] = slots

    def held(self, tenant: str) -> int:
        tenant = _validate_label("tenant", tenant)
        with self._lock:
            self._assert_state_locked()
            return self.used.get(tenant, 0)

    def total_used(self) -> int:
        with self._lock:
            self._assert_state_locked()
            return sum(self.used.values())

    def reservation_deficit(self) -> int:
        """Return slots by which configured reservations exceed total capacity."""
        with self._lock:
            self._assert_state_locked()
            return max(0, sum(self.reserved.values()) - self.capacity)

    def oversubscribed(self) -> bool:
        return self.reservation_deficit() > 0

    def starved(self) -> list[str]:
        with self._lock:
            self._assert_state_locked()
            return sorted(t for t, r in self.reserved.items() if self.used.get(t, 0) < r)

    def surplus(self) -> int:
        """Unreserved free capacity after protecting every unmet reservation."""
        with self._lock:
            self._assert_state_locked()
            unmet = sum(max(0, r - self.used.get(t, 0)) for t, r in self.reserved.items())
            return max(0, self.capacity - sum(self.used.values()) - unmet)

    def verdict(self, tenant: str, slots: int = 1) -> FairnessVerdict:
        """Return the fair-share verdict for a prospective claim without mutating state."""
        tenant = _validate_label("tenant", tenant)
        slots = _validate_positive_int("slots", slots)
        with self._lock:
            self._assert_state_locked()
            total_used = sum(self.used.values())
            free = self.capacity - total_used
            held = self.used.get(tenant, 0)
            reserved = self.reserved.get(tenant, 0)
            own_headroom = max(0, reserved - held)
            protected_others = sum(
                max(0, r - self.used.get(other, 0))
                for other, r in self.reserved.items()
                if other != tenant
            )
            surplus_available = max(0, free - own_headroom - protected_others)
            beyond_own = max(0, slots - own_headroom)

            if sum(self.reserved.values()) > self.capacity:
                allowed = False
                reason = "reservations_oversubscribed"
            elif slots > free:
                allowed = False
                reason = "capacity_exhausted"
            elif beyond_own > surplus_available:
                allowed = False
                reason = "protected_reservation"
            else:
                allowed = True
                reason = "within_reservation" if slots <= own_headroom else "surplus_available"

            return FairnessVerdict(
                tenant=tenant,
                requested_slots=slots,
                allowed=allowed,
                reason=reason,
                capacity=self.capacity,
                total_used=total_used,
                free_capacity=free,
                reserved_slots=reserved,
                held_slots=held,
                own_reserved_headroom=own_headroom,
                protected_for_other_tenants=protected_others,
                surplus_available=surplus_available,
                state_token=self._state_token_locked(),
            )

    def claim(
        self,
        tenant: str,
        slots: int = 1,
        *,
        expected_state_token: str | None = None,
    ) -> FairnessVerdict:
        """Atomically claim slots or raise ``ShareViolation``; return the admission verdict."""
        tenant = _validate_label("tenant", tenant)
        slots = _validate_positive_int("slots", slots)
        with self._lock:
            self._assert_state_locked()
            if expected_state_token is not None and expected_state_token != self._state_token_locked():
                raise StaleFairShare(f"{tenant}: fair-share state changed after scoring")
            verdict = self.verdict(tenant, slots)
            if not verdict.allowed:
                if verdict.reason == "reservations_oversubscribed":
                    raise ReservationOversubscribed(
                        f"reservation set exceeds capacity by {self.reservation_deficit()} slot(s)"
                    )
                raise ShareViolation(
                    f"{tenant}: claim of {slots} slot(s) denied ({verdict.reason}); "
                    f"free={verdict.free_capacity}, protected_for_others="
                    f"{verdict.protected_for_other_tenants}, surplus={verdict.surplus_available}"
                )
            self.used[tenant] = self.used.get(tenant, 0) + slots
            return verdict

    def release(self, tenant: str, slots: int = 1) -> int:
        """Atomically release held slots and return the tenant's new held count."""
        tenant = _validate_label("tenant", tenant)
        slots = _validate_positive_int("slots", slots)
        with self._lock:
            self._assert_state_locked()
            held = self.used.get(tenant, 0)
            if slots > held:
                raise ValueError(f"{tenant}: cannot release {slots} slot(s); only {held} held")
            remaining = held - slots
            if remaining:
                self.used[tenant] = remaining
            else:
                self.used.pop(tenant, None)
            return remaining


@dataclass(frozen=True)
class CandidateScore:
    """Explainable score for one candidate node."""

    node: str
    rank_score: int
    locality_cost: int
    spread_penalty: int
    failure_domain: str


@dataclass(frozen=True)
class ScoringResult:
    """Candidate scores plus the required fairness verdict."""

    topology_generation: int
    fairness: FairnessVerdict
    candidates: tuple[CandidateScore, ...]

    def ranked_nodes(self) -> list[str]:
        return [item.node for item in self.candidates]


def _score_snapshot(
    snapshot: TopologySnapshot,
    anchor: str,
    candidates: Iterable[str],
    *,
    spread_from: Iterable[str] = (),
) -> tuple[CandidateScore, ...]:
    snapshot.path(anchor)
    candidate_list = list(candidates)
    for node in candidate_list:
        _validate_label("candidate node", node)
    if len(candidate_list) != len(set(candidate_list)):
        raise ValueError("candidate list contains duplicate node identifiers")
    taken = {snapshot.domain(node) for node in spread_from}
    scored: list[CandidateScore] = []
    for node in candidate_list:
        locality = snapshot.cost(anchor, node)
        domain = snapshot.domain(node)
        penalty = SPREAD_PENALTY if domain in taken else 0
        scored.append(
            CandidateScore(
                node=node,
                rank_score=locality + penalty,
                locality_cost=locality,
                spread_penalty=penalty,
                failure_domain=domain,
            )
        )
    return tuple(sorted(scored, key=lambda item: (item.rank_score, item.node)))


def rank(
    topology: Topology,
    anchor: str,
    candidates: Iterable[str],
    *,
    spread_from: Iterable[str] = (),
) -> list[str]:
    """Rank candidates by locality with strict requested failure-domain spreading."""
    return [item.node for item in _score_snapshot(topology.snapshot(), anchor, candidates, spread_from=spread_from)]


def score_candidates(
    topology: Topology,
    anchor: str,
    candidates: Iterable[str],
    *,
    fair_share: FairShare,
    tenant: str,
    slots: int = 1,
    spread_from: Iterable[str] = (),
) -> ScoringResult:
    """Return deterministic candidate scores and the tenant fair-share verdict.

    The function never claims capacity and therefore never owns the placement
    decision.  The caller may select a candidate and then atomically call
    ``fair_share.claim`` as part of its placement commit path.
    """
    snapshot = topology.snapshot()
    fairness = fair_share.verdict(tenant, slots)
    candidates_scored = _score_snapshot(snapshot, anchor, candidates, spread_from=spread_from)
    return ScoringResult(snapshot.generation, fairness, candidates_scored)
