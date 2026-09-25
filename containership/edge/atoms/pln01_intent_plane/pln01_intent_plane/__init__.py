"""PLN-01 - Intent plane.

The graph/planner API is importable with only the Python standard library.
``pk_core`` integration objects are imported lazily when requested.
"""
from __future__ import annotations

__version__ = "4.3.0"

from .graph import (
    AdmissionRejectedError,
    AuditEvent,
    CycleError,
    DependencyInUseError,
    HistoryUnavailableError,
    IntentGraph,
    ReplayError,
    ValidationError,
    VersionConflictError,
    plan,
)
from .metadata import ELEMENT_ID, ELEMENT_NAME


def __getattr__(name: str):
    if name in {"COMPONENT", "IntentPlaneComponent"}:
        from .component import COMPONENT, IntentPlaneComponent
        return {"COMPONENT": COMPONENT, "IntentPlaneComponent": IntentPlaneComponent}[name]
    if name == "IntentPlaneService":
        from .service import IntentPlaneService
        return IntentPlaneService
    if name == "build_contract":
        from .contract import build
        return build
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "IntentGraph",
    "plan",
    "AuditEvent",
    "CycleError",
    "ValidationError",
    "VersionConflictError",
    "DependencyInUseError",
    "AdmissionRejectedError",
    "ReplayError",
    "HistoryUnavailableError",
    "COMPONENT",
    "IntentPlaneComponent",
    "build_contract",
    "IntentPlaneService",
]
