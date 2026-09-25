"""GAP-01 - Edge Node Supervisor."""

__version__ = "5.0.0"

from .supervisor import (
    DRAIN_ORDER,
    HEALTH_STALENESS_BOUND,
    TRANSITIONS,
    DrainIncomplete,
    IllegalTransition,
    NodeSupervisor,
)

from .errors import ERROR_CATALOG, SupervisorError
from .client import make_request

# pk_core is an integration dependency, not a prerequisite for using or testing
# the dependency-free supervisor model. Export integration symbols when present.
try:
    from .component import COMPONENT, EdgeNodeSupervisorComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
except ModuleNotFoundError as exc:
    if exc.name != "pk_core" and not (exc.name or "").startswith("pk_core."):
        raise
    COMPONENT = None  # type: ignore[assignment,misc]
    EdgeNodeSupervisorComponent = None  # type: ignore[assignment,misc]
    ELEMENT_ID = "GAP-01"
    ELEMENT_NAME = "Edge Node Supervisor"
    build_contract = None  # type: ignore[assignment]

__all__ = [
    "__version__", "COMPONENT", "EdgeNodeSupervisorComponent", "ELEMENT_ID",
    "ELEMENT_NAME", "build_contract", "NodeSupervisor", "IllegalTransition",
    "DrainIncomplete", "SupervisorError", "ERROR_CATALOG", "make_request", "TRANSITIONS",
    "DRAIN_ORDER", "HEALTH_STALENESS_BOUND",
]
