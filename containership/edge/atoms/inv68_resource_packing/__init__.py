"""INV-68 - Resource packing.

The pure packing API is always importable.  ``pk_core`` integration objects are
loaded lazily so an unavailable control-plane framework does not make the core
engine unusable or untestable.
"""
from __future__ import annotations

from importlib import import_module
from typing import Any

from .packing import (
    DIMENSIONS,
    OVERCOMMIT,
    Host,
    PackingResult,
    PlacementDecision,
    capacity_report,
    effective_capacity,
    fragmentation,
    lower_bound,
    pack,
    pack_detailed,
)

__version__ = "4.3.0"


def _integration_module(module_name: str):
    try:
        return import_module(module_name, __name__)
    except ModuleNotFoundError as exc:
        if exc.name == "pk_core" or (exc.name and exc.name.startswith("pk_core.")):
            raise ModuleNotFoundError(
                "pk_core is required for INV-68 control-plane/checklist integration; "
                "the pure packing API remains available without it",
                name="pk_core",
            ) from exc
        raise


def __getattr__(name: str) -> Any:
    if name in {"COMPONENT", "ResourcePackingComponent"}:
        module = _integration_module(".component")
        return getattr(module, name)
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        module = _integration_module(".contract")
        if name == "build_contract":
            return module.build
        return getattr(module, name)
    raise AttributeError(name)


__all__ = [
    "__version__",
    "DIMENSIONS",
    "OVERCOMMIT",
    "Host",
    "PackingResult",
    "PlacementDecision",
    "capacity_report",
    "effective_capacity",
    "fragmentation",
    "lower_bound",
    "pack",
    "pack_detailed",
    "COMPONENT",
    "ResourcePackingComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
