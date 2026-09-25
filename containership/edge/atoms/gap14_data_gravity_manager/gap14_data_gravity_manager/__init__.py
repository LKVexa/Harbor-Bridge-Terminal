"""GAP-14 - Data-gravity manager."""
from __future__ import annotations

from .engine import (
    COMPUTE_MOVE_COST,
    EGRESS_PER_GB,
    SCHEMA_VERSION,
    CostModelError,
    Dataset,
    GravityDecisionError,
    GravityManager,
    NoLegalOption,
)

__version__ = "4.3.0"

# Keep the production decision engine importable without the optional pk_core
# conformance framework.  Component symbols are loaded only when requested.
def __getattr__(name: str):
    if name in {"COMPONENT", "DataGravityManagerComponent"}:
        from .component import COMPONENT, DataGravityManagerComponent
        return {"COMPONENT": COMPONENT, "DataGravityManagerComponent": DataGravityManagerComponent}[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    if name == "DecisionService":
        from .service import DecisionService
        return DecisionService
    raise AttributeError(name)


__all__ = [
    "__version__",
    "SCHEMA_VERSION",
    "EGRESS_PER_GB",
    "COMPUTE_MOVE_COST",
    "Dataset",
    "GravityManager",
    "GravityDecisionError",
    "NoLegalOption",
    "CostModelError",
    "COMPONENT",
    "DataGravityManagerComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "DecisionService",
]
