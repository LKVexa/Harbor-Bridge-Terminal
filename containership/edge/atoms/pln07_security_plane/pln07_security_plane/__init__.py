"""PLN-07 - Security plane.

The grant primitives are dependency-light and importable without ``pk_core``.
Framework integration is loaded lazily when ``COMPONENT`` or ``build_contract``
is requested.
"""
from __future__ import annotations

__version__ = "4.3.0"

from .grants import (
    Grant,
    GrantInvalid,
    MAX_DELEGATION_DEPTH,
    SecurityPlaneError,
    VerificationResult,
    Verifier,
    Widening,
)

ELEMENT_ID = "PLN-07"
ELEMENT_NAME = "Security plane"


def __getattr__(name: str):
    if name in {"COMPONENT", "SecurityPlaneComponent"}:
        from .component import COMPONENT, SecurityPlaneComponent
        return {"COMPONENT": COMPONENT, "SecurityPlaneComponent": SecurityPlaneComponent}[name]
    if name in {"SecurityPlaneService", "encode_grant", "decode_grant"}:
        from . import service
        return getattr(service, name)
    if name == "build_contract":
        from .contract import build
        return build
    raise AttributeError(name)


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "Grant",
    "GrantInvalid",
    "MAX_DELEGATION_DEPTH",
    "SecurityPlaneError",
    "VerificationResult",
    "Verifier",
    "Widening",
    "COMPONENT",
    "SecurityPlaneComponent",
    "build_contract",
    "SecurityPlaneService",
    "encode_grant",
    "decode_grant",
]
