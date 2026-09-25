"""INV-72 - Accelerated workload requirement.

The pure matcher is importable without the external ``pk_core`` integration
framework. Contract/component objects are loaded lazily when requested.
"""
from __future__ import annotations

__version__ = "4.3.0"

from .matcher import (
    Device,
    InventoryValidationError,
    LimitExceededError,
    RequirementValidationError,
    decide,
    match,
)
from .errors import AccelError
from .metadata import ELEMENT_ID, ELEMENT_NAME


def build_contract():
    """Build the ``pk_core`` contract, importing that dependency only on demand."""
    from .contract import build

    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "AcceleratedWorkloadRequirementComponent"}:
        from .component import COMPONENT, AcceleratedWorkloadRequirementComponent

        return {
            "COMPONENT": COMPONENT,
            "AcceleratedWorkloadRequirementComponent": AcceleratedWorkloadRequirementComponent,
        }[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "COMPONENT",
    "AcceleratedWorkloadRequirementComponent",
    "Device",
    "RequirementValidationError",
    "InventoryValidationError",
    "match",
    "decide",
    "LimitExceededError",
    "AccelError",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
