"""INV-24 - MicroVM runtime.

The framework-independent runtime model is importable without ``pk_core``.
Framework integration objects are resolved lazily when requested.
"""
from __future__ import annotations

from .runtime import (
    BOOT_BUDGET_MS,
    MAX_MEMORY_MIB,
    MAX_VCPUS,
    MINIMAL_DEVICE_MODEL,
    MIN_MEMORY_MIB,
    MIN_VCPUS,
    BootBudgetExceeded,
    DeviceOutsideModel,
    MicroVM,
)

__version__ = "4.3.0"
ELEMENT_ID = "INV-24"
ELEMENT_NAME = "MicroVM runtime"


def build_contract():
    from .contract import build
    return build()


def __getattr__(name: str):
    if name in {"COMPONENT", "MicrovmRuntimeComponent"}:
        from .component import COMPONENT, MicrovmRuntimeComponent
        return {"COMPONENT": COMPONENT, "MicrovmRuntimeComponent": MicrovmRuntimeComponent}[name]
    raise AttributeError(name)


__all__ = [
    "__version__", "ELEMENT_ID", "ELEMENT_NAME", "build_contract",
    "COMPONENT", "MicrovmRuntimeComponent", "MicroVM",
    "DeviceOutsideModel", "BootBudgetExceeded", "MINIMAL_DEVICE_MODEL",
    "BOOT_BUDGET_MS", "MIN_VCPUS", "MAX_VCPUS", "MIN_MEMORY_MIB",
    "MAX_MEMORY_MIB",
]
