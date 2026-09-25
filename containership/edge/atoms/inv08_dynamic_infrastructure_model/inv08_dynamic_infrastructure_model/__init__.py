"""INV-08 - Dynamic infrastructure model.

Identity metadata and the dependency-free pool model are importable without the
external ``pk_core`` framework.  The conformance adapter is loaded lazily.
"""
from __future__ import annotations

from .metadata import ELEMENT_ID, ELEMENT_NAME
from .model import NodeState, Pool, PoolInvariantError, TickResult

__version__ = "4.2.0"

__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "Pool",
    "PoolInvariantError",
    "NodeState",
    "TickResult",
    "COMPONENT",
    "DynamicInfrastructureModelComponent",
    "build_contract",
]


def __getattr__(name: str):
    if name in {"COMPONENT", "DynamicInfrastructureModelComponent"}:
        from .component import COMPONENT, DynamicInfrastructureModelComponent

        return {
            "COMPONENT": COMPONENT,
            "DynamicInfrastructureModelComponent": DynamicInfrastructureModelComponent,
        }[name]
    if name == "build_contract":
        from .contract import build

        return build
    raise AttributeError(name)
