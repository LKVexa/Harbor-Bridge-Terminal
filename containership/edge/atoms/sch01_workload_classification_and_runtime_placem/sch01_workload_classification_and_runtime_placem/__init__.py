"""SCH-01 - Workload Classification and Runtime Placement Engine."""
from __future__ import annotations

__version__ = "4.3.0"

from .engine import (
    FRESHNESS_BOUND,
    REQUIRED_TIER,
    TIER_ORDER,
    TRUST_ORDER,
    NodeReport,
    Unplaceable,
    Workload,
    candidates,
    classify,
    place,
    rejection_reasons,
    score,
)

# pk_core is an integration dependency, not an engine dependency.  Keep package
# import useful for direct scheduling/tests even when that framework is absent.
try:
    from .component import (
        COMPONENT,
        WorkloadClassificationAndRuntimePlacemenComponent,
        WorkloadClassificationAndRuntimePlacementComponent,
    )
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    if not (exc.name or "").startswith("pk_core"):
        raise
    COMPONENT = None
    WorkloadClassificationAndRuntimePlacementComponent = None
    WorkloadClassificationAndRuntimePlacemenComponent = None


def build_contract():
    """Build the pk_core contract, raising a clear import error if pk_core is absent."""
    from .contract import build
    return build()


__all__ = [
    "__version__",
    "COMPONENT",
    "WorkloadClassificationAndRuntimePlacementComponent",
    "WorkloadClassificationAndRuntimePlacemenComponent",
    "Workload",
    "NodeReport",
    "Unplaceable",
    "TRUST_ORDER",
    "REQUIRED_TIER",
    "TIER_ORDER",
    "FRESHNESS_BOUND",
    "classify",
    "candidates",
    "rejection_reasons",
    "score",
    "place",
    "build_contract",
]
