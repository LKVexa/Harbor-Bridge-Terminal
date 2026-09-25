"""GAP-03 - Topology-aware scheduler."""

__version__ = "4.3.0"

from .scheduler import (
    CandidateScore,
    FairShare,
    FairnessVerdict,
    MAX_LOCALITY_COST,
    NotInTopology,
    ReservationOversubscribed,
    SPREAD_PENALTY,
    ScoringResult,
    ShareViolation,
    StaleFairShare,
    Topology,
    TopologyConflict,
    TopologySnapshot,
    rank,
    score_candidates,
)

# The production-gate adapter depends on the suite-level pk_core package.  Keep
# the runtime scheduler usable without pk_core and load gate objects only when
# a caller actually asks for them.
def __getattr__(name):
    if name in {"COMPONENT", "TopologyAwareSchedulerComponent"}:
        from .component import COMPONENT, TopologyAwareSchedulerComponent
        return {"COMPONENT": COMPONENT, "TopologyAwareSchedulerComponent": TopologyAwareSchedulerComponent}[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "CandidateScore",
    "FairShare",
    "FairnessVerdict",
    "MAX_LOCALITY_COST",
    "NotInTopology",
    "ReservationOversubscribed",
    "SPREAD_PENALTY",
    "ScoringResult",
    "ShareViolation",
    "StaleFairShare",
    "Topology",
    "TopologyConflict",
    "TopologySnapshot",
    "rank",
    "score_candidates",
    "COMPONENT",
    "TopologyAwareSchedulerComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
