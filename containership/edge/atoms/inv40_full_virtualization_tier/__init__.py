"""INV-40 - Full virtualization tier.

The standalone runtime is importable without ``pk_core``. Integration objects
are loaded lazily and therefore require ``pk_core`` only when requested.
"""
from __future__ import annotations

from importlib import import_module

from .runtime import (
    BOOT_BUDGET_MS,
    FOOTPRINT_CEILING_MIB,
    FULL_DEVICE_MODEL,
    DeviceConflict,
    DeviceLeaseRegistry,
    FootprintExceeded,
    FullVm,
    FullVmError,
    InvalidVmState,
    PrimitiveRequired,
    device_conflict,
)

__version__ = "4.3.0"

_INTEGRATION_EXPORTS = {
    "COMPONENT",
    "FullVirtualizationTierComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
}


def __getattr__(name: str):
    """Load pk_core-backed integration symbols only when they are requested."""
    if name in {"COMPONENT", "FullVirtualizationTierComponent"}:
        module = import_module(f"{__name__}.component")
        return getattr(module, name)
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        module = import_module(f"{__name__}.contract")
        if name == "build_contract":
            return module.build
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "__version__",
    "BOOT_BUDGET_MS",
    "FOOTPRINT_CEILING_MIB",
    "FULL_DEVICE_MODEL",
    "DeviceConflict",
    "DeviceLeaseRegistry",
    "FootprintExceeded",
    "FullVm",
    "FullVmError",
    "InvalidVmState",
    "PrimitiveRequired",
    "device_conflict",
    "COMPONENT",
    "FullVirtualizationTierComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
