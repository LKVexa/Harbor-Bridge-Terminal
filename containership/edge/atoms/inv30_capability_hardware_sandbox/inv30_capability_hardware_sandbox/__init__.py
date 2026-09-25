# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""INV-30 - Capability hardware sandbox."""
from __future__ import annotations

__version__ = "4.3.0"

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


# Eager adapter import when pk_core is present. The 4.2.0 lazy-only import hid the
# component class from pk_core.Registry (which scans module attributes), so
# ``python -m pk_core run INV-30`` reported "unknown element" in a full estate.
# Regression: tests/test_framework_integration.py::test_registry_discovers_inv30.
try:  # pragma: no branch
    import pk_core as _pk  # noqa: F401
except ModuleNotFoundError:
    _pk = None
from .deps import pk_core_status as _pk_status  # noqa: E402
if _pk is not None and _pk_status()["state"] == "ok":
    from .component import COMPONENT, CapabilityHardwareSandboxComponent  # noqa: E402,F401


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
