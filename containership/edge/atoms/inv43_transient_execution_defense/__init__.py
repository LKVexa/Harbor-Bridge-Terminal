"""INV-43 - Transient-execution defense.

The core policy model can be imported without the external ``pk_core`` registry
runtime.  Registry/contract objects are loaded lazily when requested.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

__version__ = "4.3.0"

from .defense import (
    ACTIVE,
    INACTIVE,
    UNKNOWN,
    NOT_AFFECTED,
    VALID_STATUSES,
    SATISFYING_STATUSES,
    ELEMENT_ID,
    ELEMENT_NAME,
    REQUIRED_FOR_COTENANCY,
    MitigationMissing,
    MitigationState,
)

if TYPE_CHECKING:  # pragma: no cover
    from .component import COMPONENT, TransientExecutionDefenseComponent


def __getattr__(name: str):
    """Lazily load objects that require the external ``pk_core`` runtime."""
    if name == "build_contract":
        from .contract import build
        return build
    if name in {"COMPONENT", "TransientExecutionDefenseComponent"}:
        from .component import COMPONENT, TransientExecutionDefenseComponent
        return {"COMPONENT": COMPONENT, "TransientExecutionDefenseComponent": TransientExecutionDefenseComponent}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "ACTIVE",
    "INACTIVE",
    "UNKNOWN",
    "NOT_AFFECTED",
    "VALID_STATUSES",
    "SATISFYING_STATUSES",
    "REQUIRED_FOR_COTENANCY",
    "MitigationMissing",
    "MitigationState",
    "COMPONENT",
    "TransientExecutionDefenseComponent",
]
