"""INV-44 - Wasm hardening system.

The standalone runtime model is importable without the optional ``pk_core``
conformance framework. Framework-bound attributes are loaded lazily on access.
"""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "INV-44"
ELEMENT_NAME = "Wasm hardening system"

from .runtime import (
    MEMORY_PAGE_CEILING,
    REQUIRED_HARDENING,
    Engine,
    FuelExhausted,
    HardeningIncomplete,
    Instance,
    InstanceConstructionDenied,
    MemoryCeiling,
    OutputUnverified,
)


def build_contract():
    """Build the pk_core contract; requires the external pk_core framework."""
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "WasmHardeningSystemComponent"}:
        from .component import COMPONENT, WasmHardeningSystemComponent
        return {
            "COMPONENT": COMPONENT,
            "WasmHardeningSystemComponent": WasmHardeningSystemComponent,
        }[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "COMPONENT",
    "WasmHardeningSystemComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "REQUIRED_HARDENING",
    "MEMORY_PAGE_CEILING",
    "Engine",
    "Instance",
    "HardeningIncomplete",
    "OutputUnverified",
    "FuelExhausted",
    "MemoryCeiling",
    "InstanceConstructionDenied",
]
