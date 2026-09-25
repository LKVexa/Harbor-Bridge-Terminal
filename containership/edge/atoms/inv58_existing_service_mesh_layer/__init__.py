"""INV-58 - Existing service-mesh layer (master-applied component).

Framework-bound exports are loaded lazily so version metadata and the
standalone mesh logic remain importable when the external ``pk_core`` package is
not installed. Accessing ``COMPONENT``, the component class, or contract exports
still requires ``pk_core`` as expected.
"""
from __future__ import annotations

from .mesh_logic import (
    BypassDetector,
    RoutePolicyRegistry,
    Unmappable,
    effective_attempts,
    map_identity,
    reconcile,
)

__version__ = "4.3.0"

__all__ = [
    "__version__",
    "BypassDetector",
    "RoutePolicyRegistry",
    "Unmappable",
    "effective_attempts",
    "map_identity",
    "reconcile",
    "COMPONENT",
    "ExistingServiceMeshLayerComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "MeshLayerService",
    "MeshError",
]


def __getattr__(name: str):
    if name in {"COMPONENT", "ExistingServiceMeshLayerComponent"}:
        from .component import COMPONENT, ExistingServiceMeshLayerComponent

        return {
            "COMPONENT": COMPONENT,
            "ExistingServiceMeshLayerComponent": ExistingServiceMeshLayerComponent,
        }[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build

        return {
            "ELEMENT_ID": ELEMENT_ID,
            "ELEMENT_NAME": ELEMENT_NAME,
            "build_contract": build,
        }[name]
    if name == "MeshLayerService":
        from .service import MeshLayerService

        return MeshLayerService
    if name == "MeshError":
        from .errors import MeshError

        return MeshError
    raise AttributeError(name)
