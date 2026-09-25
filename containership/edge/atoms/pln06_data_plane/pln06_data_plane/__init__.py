"""PLN-06 - Data plane.

The dependency-free runtime is importable without ``pk_core``.  Certification
adapter objects are loaded lazily when requested.
"""
from __future__ import annotations

from .data_plane import (
    CONTROL_INLINE_LIMIT,
    LOCALITY_FLOOR,
    TRANSPORT_TIERS,
    Backpressure,
    DataPlane,
    InvalidCompletion,
    InvalidRequest,
    NoTransportTier,
    ResidencyViolation,
)
from .metadata import ELEMENT_ID, ELEMENT_NAME, VERSION

__version__ = VERSION


_LAZY_MODULES = ("security", "integrity", "transports", "lifecycle", "resilience", "scheduling",
                 "precedence", "config", "observability", "integrations", "service")


def build_contract():
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "DataPlaneComponent"}:
        from .component import COMPONENT, DataPlaneComponent
        return {"COMPONENT": COMPONENT, "DataPlaneComponent": DataPlaneComponent}[name]
    if name == "GovernedDataPlane":
        from .service import GovernedDataPlane
        return GovernedDataPlane
    if name in _LAZY_MODULES:
        import importlib
        return importlib.import_module(f".{name}", __name__)
    raise AttributeError(name)


__all__ = [
    "__version__", "ELEMENT_ID", "ELEMENT_NAME", "build_contract",
    "DataPlane", "TRANSPORT_TIERS", "CONTROL_INLINE_LIMIT", "LOCALITY_FLOOR",
    "InvalidRequest", "InvalidCompletion", "ResidencyViolation",
    "NoTransportTier", "Backpressure", "COMPONENT", "DataPlaneComponent", "GovernedDataPlane",
]
