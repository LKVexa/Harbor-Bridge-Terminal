"""INV-10 - Component composition system.

The deterministic linker is dependency-free. The checklist/evidence adapter is
loaded lazily so consumers can use composition primitives without installing
``pk_core``; accessing ``COMPONENT`` or the adapter class still requires it.
"""
from __future__ import annotations

from typing import Any

__version__ = "4.3.0"

from .metadata import ELEMENT_ID, ELEMENT_NAME
from .composition import (
    COMPOSITION_SCHEMA,
    DEFAULT_LIMITS,
    IDENTITY_PROFILE,
    AmbiguousExport,
    CompositionCycle,
    CompositionError,
    CompositionLimits,
    InvalidComposition,
    ResourceLimitExceeded,
    Unit,
    UnsatisfiedImport,
    compose,
)


def build_contract():
    """Build the pk_core contract; requires pk_core to be importable."""
    from .contract import build

    return build()


def __getattr__(name: str) -> Any:
    if name in {"COMPONENT", "ComponentCompositionSystemComponent"}:
        from .component import COMPONENT, ComponentCompositionSystemComponent

        return {
            "COMPONENT": COMPONENT,
            "ComponentCompositionSystemComponent": ComponentCompositionSystemComponent,
        }[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "COMPONENT",
    "ComponentCompositionSystemComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "COMPOSITION_SCHEMA",
    "DEFAULT_LIMITS",
    "IDENTITY_PROFILE",
    "CompositionLimits",
    "CompositionError",
    "InvalidComposition",
    "UnsatisfiedImport",
    "AmbiguousExport",
    "CompositionCycle",
    "ResourceLimitExceeded",
    "Unit",
    "compose",
]
