"""INV-30 - Capability hardware sandbox."""
from __future__ import annotations

__version__ = "4.2.0"

from .core import (
    ACCESS_SCHEMA,
    CAPABILITY_SCHEMA,
    Amplification,
    BoundsViolation,
    Capability,
    CapabilityError,
    Invalidated,
    PermissionViolation,
)


def __getattr__(name: str):
    """Lazily load the pk_core adapter so dependency-free semantics stay usable."""
    if name in {"COMPONENT", "CapabilityHardwareSandboxComponent"}:
        from .component import COMPONENT, CapabilityHardwareSandboxComponent
        return {"COMPONENT": COMPONENT, "CapabilityHardwareSandboxComponent": CapabilityHardwareSandboxComponent}[name]
    if name in {"ELEMENT_ID", "ELEMENT_NAME", "build_contract"}:
        from .contract import ELEMENT_ID, ELEMENT_NAME, build
        return {"ELEMENT_ID": ELEMENT_ID, "ELEMENT_NAME": ELEMENT_NAME, "build_contract": build}[name]
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ACCESS_SCHEMA",
    "CAPABILITY_SCHEMA",
    "Capability",
    "CapabilityError",
    "BoundsViolation",
    "PermissionViolation",
    "Amplification",
    "Invalidated",
    "COMPONENT",
    "CapabilityHardwareSandboxComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
