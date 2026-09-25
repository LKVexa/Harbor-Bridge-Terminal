"""INV-38 - Kernel-bypass transport.

The transport reference model is intentionally importable without ``pk_core``.
Production contract/component integration remains explicitly unavailable until
that external dependency is installed.
"""
from __future__ import annotations

__version__ = "4.2.0"
ELEMENT_ID = "INV-38"
ELEMENT_NAME = "Kernel-bypass transport"

from .transport import (
    BypassError,
    BypassQueue,
    CompletionRingFull,
    NotRegistered,
    OutOfBounds,
    RegionBusy,
    RegionLimitReached,
    RingFull,
)


class CoreUnavailableError(RuntimeError):
    """Raised when a pk_core-backed operation is requested without pk_core."""


try:
    from .component import COMPONENT, KernelBypassTransportComponent
    from .contract import build as build_contract
except ModuleNotFoundError as exc:
    # Do not mask arbitrary missing dependencies.  Only degrade cleanly when the
    # external Post-Kubernetes core itself is the unavailable module.
    if exc.name != "pk_core" and not (exc.name or "").startswith("pk_core."):
        raise
    PK_CORE_AVAILABLE = False
    _CORE_IMPORT_ERROR = exc
    COMPONENT = None
    KernelBypassTransportComponent = None

    def build_contract():
        """Raise an explicit error rather than pretending conformance is available."""
        raise CoreUnavailableError(
            "pk_core is required for the INV-38 contract/component conformance layer"
        ) from _CORE_IMPORT_ERROR
else:
    PK_CORE_AVAILABLE = True


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "PK_CORE_AVAILABLE",
    "CoreUnavailableError",
    "COMPONENT",
    "KernelBypassTransportComponent",
    "build_contract",
    "BypassQueue",
    "BypassError",
    "CompletionRingFull",
    "NotRegistered",
    "OutOfBounds",
    "RegionBusy",
    "RegionLimitReached",
    "RingFull",
]
