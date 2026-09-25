"""PLN-03 - Distributed runtime plane.

The operational reference runtime remains importable even when the external
``pk_core`` conformance framework is not installed.  Conformance symbols are
populated when that dependency is available.
"""

__version__ = "4.3.0"

from .runtime import (
    Adapter,
    AdapterUnavailable,
    CapabilityDenied,
    DistributedRuntime,
    InvalidRuntimeInput,
    InvocationTargetUnavailable,
    PayloadTooLarge,
    RuntimePlaneError,
    SecretNotFound,
)

from .plane import GovernedRuntime, PublishResult
from .tokens import KeyRing, TokenIssuer, TokenVerifier
from .config import ConfigStore
from .audit_log import AuditLog, verify_chain

ELEMENT_ID = "PLN-03"
ELEMENT_NAME = "Distributed runtime plane"
PK_CORE_AVAILABLE = True

try:
    from .component import COMPONENT, DistributedRuntimePlaneComponent
    from .contract import build as build_contract
except ModuleNotFoundError as exc:
    if exc.name != "pk_core" and not (exc.name or "").startswith("pk_core."):
        raise
    PK_CORE_AVAILABLE = False
    COMPONENT = None
    DistributedRuntimePlaneComponent = None
    _PK_CORE_IMPORT_ERROR = exc

    def build_contract():
        raise ModuleNotFoundError(
            "pk_core is required to build the PLN-03 conformance contract; "
            "the operational runtime remains available without it"
        ) from _PK_CORE_IMPORT_ERROR


__all__ = [
    "__version__",
    "PK_CORE_AVAILABLE",
    "COMPONENT",
    "DistributedRuntimePlaneComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
    "Adapter",
    "AdapterUnavailable",
    "CapabilityDenied",
    "DistributedRuntime",
    "InvalidRuntimeInput",
    "InvocationTargetUnavailable",
    "PayloadTooLarge",
    "RuntimePlaneError",
    "SecretNotFound",
    "GovernedRuntime", "PublishResult", "KeyRing", "TokenIssuer", "TokenVerifier",
    "ConfigStore", "AuditLog", "verify_chain",
]
