"""GAP-04 - Disconnected-operation controller.

The core controller can be imported without ``pk_core``. Contract and conformance
objects are loaded lazily only when requested.
"""
from __future__ import annotations

__version__ = "4.3.0"

from .metadata import ELEMENT_ID, ELEMENT_NAME
from .controller import (
    PERMITTED,
    TIERS,
    TIER_AT,
    AutonomyController,
    ControllerError,
    DecisionJournalFull,
    LeaseExpired,
    NotPartitioned,
    NotPermittedAtTier,
    PolicyStale,
    ReconciliationRequired,
)


def build_contract():
    """Lazily build the pk_core contract when the framework is installed."""
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "DisconnectedOperationControllerComponent"}:
        from .component import COMPONENT, DisconnectedOperationControllerComponent
        return {
            "COMPONENT": COMPONENT,
            "DisconnectedOperationControllerComponent": DisconnectedOperationControllerComponent,
        }[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "COMPONENT",
    "DisconnectedOperationControllerComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "AutonomyController",
    "ControllerError",
    "LeaseExpired",
    "NotPermittedAtTier",
    "NotPartitioned",
    "PolicyStale",
    "ReconciliationRequired",
    "DecisionJournalFull",
    "TIERS",
    "TIER_AT",
    "PERMITTED",
]
