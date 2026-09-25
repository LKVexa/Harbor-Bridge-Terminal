"""Dependency-independent scheduler engine for SCH-01.

This module contains the production decision logic and intentionally has no dependency
on ``pk_core``.  The ``component`` module is the pk_core conformance adapter.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Iterable, Mapping

TRUST_ORDER = ("trusted", "first-party", "third-party", "untrusted", "hostile")
REQUIRED_TIER = {
    "trusted": "process",
    "first-party": "wasm",
    "third-party": "unikernel",
    "untrusted": "microvm",
    "hostile": "vm",
}
TIER_ORDER = ("process", "wasm", "unikernel", "microvm", "vm")
FRESHNESS_BOUND = 30

_PLACEMENT_LOCK = RLock()


class Unplaceable(RuntimeError):
    """Raised when a workload cannot be placed without violating a hard constraint.

    ``code`` is stable and machine-readable.  ``details`` is deliberately aggregate
    rather than node-by-node so callers do not accidentally disclose placement state
    belonging to other tenants.
    """

    def __init__(self, message: str, *, code: str = "NO_CANDIDATE", details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "PK_SCHEDULER_ERROR/1",
            "code": self.code,
            "message": str(self),
            "details": dict(self.details),
        }


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _nonempty_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value


def _string_set(values: Iterable[str], field_name: str) -> frozenset[str]:
    if isinstance(values, (str, bytes)):
        raise ValueError(f"{field_name} must be an iterable of strings, not a scalar string")
    try:
        normalized = frozenset(values)
    except TypeError as exc:
        raise ValueError(f"{field_name} must be an iterable of strings") from exc
    if any(not isinstance(value, str) or not value.strip() for value in normalized):
        raise ValueError(f"{field_name} entries must be non-empty strings")
    return normalized


@dataclass(frozen=True, slots=True)
class Workload:
    name: str
    tenant: str
    provenance: str
    latency_sensitive: bool = False
    needs: frozenset[str] = field(default_factory=frozenset)
    site_affinity: str | None = None

    def __post_init__(self) -> None:
        _nonempty_text(self.name, "workload name")
        _nonempty_text(self.tenant, "tenant")
        _nonempty_text(self.provenance, "provenance")
        if not isinstance(self.latency_sensitive, bool):
            raise ValueError("latency_sensitive must be a bool")
        object.__setattr__(self, "needs", _string_set(self.needs, "needs"))
        if self.site_affinity is not None:
            _nonempty_text(self.site_affinity, "site_affinity")


@dataclass(slots=True)
class NodeReport:
    name: str
    site: str
    tiers: frozenset[str]
    capabilities: frozenset[str] = field(default_factory=frozenset)
    free_slots: int = 1
    reported_at: int = 0
    thermally_excluded: bool = False
    occupants: dict[str, str] = field(default_factory=dict)  # workload -> tenant

    def __post_init__(self) -> None:
        self.validate()

    def validate(self) -> None:
        """Validate mutable report state at a decision boundary.

        ``NodeReport`` must remain mutable because ``place`` updates free capacity and
        occupants.  Revalidation prevents a caller from bypassing constructor checks by
        mutating fields after creation.
        """
        _nonempty_text(self.name, "node name")
        _nonempty_text(self.site, "site")
        self.tiers = _string_set(self.tiers, "tiers")
        unknown_tiers = sorted(self.tiers.difference(TIER_ORDER))
        if unknown_tiers:
            raise ValueError(f"tiers contains unsupported values: {unknown_tiers}")
        if not self.tiers:
            raise ValueError("tiers must contain at least one supported isolation tier")
        self.capabilities = _string_set(self.capabilities, "capabilities")
        if not _is_int(self.free_slots) or self.free_slots < 0:
            raise ValueError("free_slots must be a non-negative int")
        if not _is_int(self.reported_at) or self.reported_at < 0:
            raise ValueError("reported_at must be a non-negative int")
        if not isinstance(self.thermally_excluded, bool):
            raise ValueError("thermally_excluded must be a bool")
        if not isinstance(self.occupants, dict):
            raise ValueError("occupants must be a workload-to-tenant dict")
        cleaned: dict[str, str] = {}
        for workload_name, tenant in self.occupants.items():
            cleaned[_nonempty_text(workload_name, "occupant workload")] = _nonempty_text(tenant, "occupant tenant")
        self.occupants = cleaned


def _validate_now(now: int) -> None:
    if not _is_int(now) or now < 0:
        raise ValueError("now must be a non-negative int")


def classify(workload: Workload) -> dict[str, Any]:
    """Derive the canonical workload class from provenance and immutable inputs."""
    if not isinstance(workload, Workload):
        raise TypeError("workload must be a Workload")
    trust_by_provenance = {
        "internal": "trusted",
        "first-party": "first-party",
        "partner": "third-party",
        "public": "untrusted",
        "quarantined": "hostile",
    }
    trust = trust_by_provenance.get(workload.provenance)
    if trust is None:
        raise Unplaceable(
            f"{workload.name}: unknown provenance {workload.provenance!r}",
            code="UNKNOWN_PROVENANCE",
            details={"provenance": workload.provenance},
        )
    return {
        "schema": "PK_WORKLOAD_CLASS/1",
        "workload": workload.name,
        "trust_class": trust,
        "required_tier": REQUIRED_TIER[trust],
        "latency_class": "interactive" if workload.latency_sensitive else "batch",
        "hardware": sorted(workload.needs),
    }


def _validate_classification(workload: Workload, klass: Mapping[str, Any]) -> None:
    if not isinstance(klass, Mapping):
        raise ValueError("classification must be a mapping")
    canonical = classify(workload)
    keys = ("schema", "workload", "trust_class", "required_tier", "latency_class", "hardware")
    mismatches = [key for key in keys if klass.get(key) != canonical[key]]
    if mismatches:
        raise ValueError(f"classification is not canonical for workload; mismatched fields: {mismatches}")


def rejection_reasons(workload: Workload, klass: Mapping[str, Any], node: NodeReport, now: int) -> tuple[str, ...]:
    """Return stable hard-constraint rejection codes for one node.

    An empty tuple means the node is viable.  This function performs no mutation.
    """
    _validate_now(now)
    _validate_classification(workload, klass)
    if not isinstance(node, NodeReport):
        raise TypeError("node must be a NodeReport")
    node.validate()

    reasons: list[str] = []
    if node.thermally_excluded:
        reasons.append("THERMALLY_EXCLUDED")
    if node.free_slots <= 0:
        reasons.append("NO_FREE_SLOTS")
    if node.reported_at > now:
        reasons.append("REPORT_FROM_FUTURE")
    elif now - node.reported_at > FRESHNESS_BOUND:
        reasons.append("STALE_REPORT")
    if workload.site_affinity and node.site != workload.site_affinity:
        reasons.append("SITE_MISMATCH")
    if not workload.needs <= node.capabilities:
        reasons.append("MISSING_CAPABILITY")

    floor = TIER_ORDER.index(str(klass["required_tier"]))
    if not any(tier in node.tiers for tier in TIER_ORDER[floor:]):
        reasons.append("INSUFFICIENT_TIER")

    # NodeReport does not carry occupant trust/tier metadata, so allowing a
    # cross-tenant placement cannot prove the contract's isolation boundary.
    # Fail closed until richer occupancy metadata exists.
    if any(occupant_tenant != workload.tenant for occupant_tenant in node.occupants.values()):
        reasons.append("TENANT_ISOLATION")

    return tuple(reasons)


def candidates(workload: Workload, klass: Mapping[str, Any], nodes: Iterable[NodeReport], now: int) -> list[NodeReport]:
    """Return nodes satisfying every hard constraint, preserving input order."""
    _validate_now(now)
    _validate_classification(workload, klass)
    out: list[NodeReport] = []
    for node in nodes:
        if not rejection_reasons(workload, klass, node, now):
            out.append(node)
    return out


def score(node: NodeReport, klass: Mapping[str, Any]) -> tuple[int, int, str]:
    """Prefer the weakest sufficient tier, then most free slots; tie-break by name."""
    if not isinstance(node, NodeReport):
        raise TypeError("node must be a NodeReport")
    trust_class = klass.get("trust_class") if isinstance(klass, Mapping) else None
    required_tier = klass.get("required_tier") if isinstance(klass, Mapping) else None
    if trust_class not in REQUIRED_TIER or REQUIRED_TIER[trust_class] != required_tier:
        raise ValueError("classification trust/tier combination is invalid")
    floor = TIER_ORDER.index(str(required_tier))
    sufficient = [tier for tier in TIER_ORDER[floor:] if tier in node.tiers]
    if not sufficient:
        raise ValueError("node does not offer a sufficient tier for this classification")
    tier = sufficient[0]
    return (TIER_ORDER.index(tier), -node.free_slots, node.name)


def _validate_nodes(nodes: list[NodeReport]) -> None:
    if any(not isinstance(node, NodeReport) for node in nodes):
        raise TypeError("nodes must contain only NodeReport instances")
    for node in nodes:
        node.validate()
    names = [node.name for node in nodes]
    if len(names) != len(set(names)):
        raise ValueError("node names must be unique within one placement decision")


def place(workload: Workload, nodes: Iterable[NodeReport], now: int = 0, lease_ticks: int = 60) -> dict[str, Any]:
    """Classify and place atomically within this process, or fail closed.

    The process-local lock prevents concurrent callers from oversubscribing the same
    mutable ``NodeReport`` objects.  Distributed ownership still belongs to the
    external execution/control plane and is called out as a remaining dependency.
    """
    if not isinstance(workload, Workload):
        raise TypeError("workload must be a Workload")
    _validate_now(now)
    if not _is_int(lease_ticks) or lease_ticks <= 0:
        raise ValueError("lease_ticks must be a positive int")
    node_list = list(nodes)
    _validate_nodes(node_list)
    klass = classify(workload)

    with _PLACEMENT_LOCK:
        if any(workload.name in node.occupants for node in node_list):
            raise Unplaceable(
                f"{workload.name} already holds a placement lease",
                code="DUPLICATE_LEASE",
                details={"workload": workload.name},
            )

        viable = candidates(workload, klass, node_list, now)
        if not viable:
            counts: Counter[str] = Counter()
            for node in node_list:
                counts.update(rejection_reasons(workload, klass, node, now))
            raise Unplaceable(
                f"{workload.name}: no node satisfies the hard placement constraints",
                code="NO_CANDIDATE",
                details={
                    "required_tier": klass["required_tier"],
                    "hardware": list(klass["hardware"]),
                    "site": workload.site_affinity,
                    "candidate_count": len(node_list),
                    "rejection_counts": dict(sorted(counts.items())),
                },
            )

        chosen = min(viable, key=lambda node: score(node, klass))
        chosen_score = score(chosen, klass)
        floor = TIER_ORDER.index(klass["required_tier"])
        tier = next(tier for tier in TIER_ORDER[floor:] if tier in chosen.tiers)

        # Mutation is inside the same critical section as candidate selection.
        chosen.free_slots -= 1
        chosen.occupants[workload.name] = workload.tenant

        return {
            "schema": "PK_PLACEMENT/1",
            "workload": workload.name,
            "tenant": workload.tenant,
            "node": chosen.name,
            "site": chosen.site,
            "tier": tier,
            "trust_class": klass["trust_class"],
            "lease_issued_at": now,
            "lease_expires": now + lease_ticks,
            "candidates_total": len(node_list),
            "candidates_considered": len(viable),
            "decision": {
                "strategy": "weakest-sufficient-tier/most-free-slots/name",
                "score": list(chosen_score),
            },
        }
