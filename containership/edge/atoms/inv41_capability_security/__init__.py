"""INV-41 - Capability security.

Security primitives are importable without the optional estate ``pk_core``
integration.  Integration objects are loaded lazily on access.
"""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "INV-41"
ELEMENT_NAME = "Capability security"

from .capabilities import (  # noqa: E402
    Authority,
    CapabilityError,
    CrossAuthority,
    Forged,
    Holder,
    InvalidGrant,
    LimitExceeded,
    Membrane,
    Reference,
    Revoked,
    Widening,
)


def __getattr__(name: str):
    if name in {"COMPONENT", "CapabilitySecurityComponent"}:
        from .component import COMPONENT, CapabilitySecurityComponent
        return {"COMPONENT": COMPONENT, "CapabilitySecurityComponent": CapabilitySecurityComponent}[name]
    if name == "build_contract":
        from .contract import build
        return build
    raise AttributeError(name)


__all__ = [
    "__version__", "ELEMENT_ID", "ELEMENT_NAME", "Authority", "CapabilityError",
    "CrossAuthority", "Forged", "Holder", "InvalidGrant", "LimitExceeded", "Membrane", "Reference",
    "Revoked", "Widening", "COMPONENT", "CapabilitySecurityComponent", "build_contract",
]
