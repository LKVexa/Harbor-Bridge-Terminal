"""INV-38-C015 — Lifecycle state machine for the kernel-bypass transport.

Formalises component, memory-region and provider lifecycle states and the legal
transitions between them.  Illegal transitions raise deterministically without
mutating state.  The model exposes a monotonic ``generation`` so stale observers
and stale region keys (C057/C058) can be detected.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from threading import RLock

LIFECYCLE_SCHEMA_VERSION = "lifecycle/1"


class CompState(str, enum.Enum):
    UNINITIALIZED = "UNINITIALIZED"
    BOOTSTRAPPING = "BOOTSTRAPPING"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DRAINING = "DRAINING"
    QUIESCED = "QUIESCED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"


class RegionState(str, enum.Enum):
    REGISTERING = "REGISTERING"
    ACTIVE = "ACTIVE"
    DRAINING = "DRAINING"
    DEREGISTERING = "DEREGISTERING"
    REVOKED = "REVOKED"
    FAILED = "FAILED"


# Legal component transitions (C015-T04). Any edge not listed is illegal.
_COMP_EDGES: dict[CompState, set[CompState]] = {
    CompState.UNINITIALIZED: {CompState.BOOTSTRAPPING, CompState.STOPPED},
    CompState.BOOTSTRAPPING: {CompState.READY, CompState.FAILED, CompState.STOPPED},
    CompState.READY: {CompState.DEGRADED, CompState.DRAINING, CompState.FAILED},
    CompState.DEGRADED: {CompState.READY, CompState.DRAINING, CompState.FAILED},
    CompState.DRAINING: {CompState.QUIESCED, CompState.FAILED},
    CompState.QUIESCED: {CompState.STOPPED, CompState.BOOTSTRAPPING},
    CompState.FAILED: {CompState.DRAINING, CompState.STOPPED},
    CompState.STOPPED: set(),
}

_REGION_EDGES: dict[RegionState, set[RegionState]] = {
    RegionState.REGISTERING: {RegionState.ACTIVE, RegionState.FAILED},
    RegionState.ACTIVE: {RegionState.DRAINING, RegionState.REVOKED, RegionState.FAILED},
    RegionState.DRAINING: {RegionState.DEREGISTERING, RegionState.FAILED},
    RegionState.DEREGISTERING: {RegionState.REVOKED, RegionState.FAILED},
    RegionState.REVOKED: set(),
    RegionState.FAILED: {RegionState.REVOKED},
}


class IllegalTransition(RuntimeError):
    code = "PK_BYPASS_ILLEGAL_TRANSITION"


@dataclass
class LifecycleMachine:
    state: CompState = CompState.UNINITIALIZED
    generation: int = 0
    _lock: RLock = field(default_factory=RLock, repr=False, compare=False)

    def can(self, target: CompState) -> bool:
        return target in _COMP_EDGES[self.state]

    def transition(self, target: CompState) -> int:
        with self._lock:
            if target not in _COMP_EDGES[self.state]:
                raise IllegalTransition(f"{self.state.value}->{target.value} is not a legal transition")
            self.state = target
            # Re-entering the active path after a restart-like edge bumps generation
            if target in (CompState.BOOTSTRAPPING, CompState.READY):
                self.generation += 1
            return self.generation


def region_transition(current: RegionState, target: RegionState) -> RegionState:
    """Pure helper used by region bookkeeping and model tests (C015-T02/T05)."""
    if target not in _REGION_EDGES[current]:
        raise IllegalTransition(f"region {current.value}->{target.value} illegal")
    return target


def legal_component_edges() -> dict[str, list[str]]:
    return {s.value: sorted(t.value for t in nxt) for s, nxt in _COMP_EDGES.items()}


def legal_region_edges() -> dict[str, list[str]]:
    return {s.value: sorted(t.value for t in nxt) for s, nxt in _REGION_EDGES.items()}
