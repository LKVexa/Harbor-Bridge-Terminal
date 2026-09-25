"""INV-04 - Current orchestration.

The package exposes its dependency-free reference model even when the optional
estate conformance dependency (``pk_core``) is not installed.  Conformance
objects are imported lazily on first access.
"""
from __future__ import annotations

from .model import (
    BudgetBreach,
    Cluster,
    ConfigurationError,
    NoCapacity,
    OrchestrationError,
    StateIntegrityError,
    UnknownNode,
)

__version__ = "4.3.0"
ELEMENT_ID = "INV-04"
ELEMENT_NAME = "Current orchestration"


def build_contract():
    from .contract import build

    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "CurrentOrchestrationComponent"}:
        from .component import COMPONENT, CurrentOrchestrationComponent

        return COMPONENT if name == "COMPONENT" else CurrentOrchestrationComponent
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "COMPONENT",
    "CurrentOrchestrationComponent",
    "Cluster",
    "OrchestrationError",
    "ConfigurationError",
    "StateIntegrityError",
    "BudgetBreach",
    "UnknownNode",
    "NoCapacity",
]
