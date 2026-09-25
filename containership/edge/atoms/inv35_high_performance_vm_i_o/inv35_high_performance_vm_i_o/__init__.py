"""INV-35 - High-performance VM I/O."""
from __future__ import annotations

from .io_model import (
    MAX_CHAIN,
    QUEUE_DEPTH,
    Descriptor,
    DescriptorInvalid,
    MemoryRegion,
    QueueFull,
    VirtQueue,
)

__version__ = "4.3.0"

__all__ = [
    "__version__",
    "MAX_CHAIN",
    "QUEUE_DEPTH",
    "Descriptor",
    "DescriptorInvalid",
    "MemoryRegion",
    "QueueFull",
    "VirtQueue",
    "COMPONENT",
    "HighPerformanceVmIOComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]


def __getattr__(name: str):
    """Load the optional pk_core binding only when a caller requests it."""
    if name in {"COMPONENT", "HighPerformanceVmIOComponent"}:
        from .component import COMPONENT, HighPerformanceVmIOComponent

        return {"COMPONENT": COMPONENT, "HighPerformanceVmIOComponent": HighPerformanceVmIOComponent}[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build

        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    raise AttributeError(name)
