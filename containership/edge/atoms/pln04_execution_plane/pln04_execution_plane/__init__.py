"""PLN-04 - Execution plane."""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "PLN-04"
ELEMENT_NAME = "Execution plane"

from .runtime import (
    AdmissionConflict,
    AuditEvent,
    CapacityExceeded,
    ExecutionPlaneError,
    InstanceRecord,
    NoSufficientTier,
    Node,
    ResidentTierUnattested,
    TIERS,
    TRUST_CLASSES,
    admit,
    select_tier,
    teardown,
)
from .errors import ERROR_CODES, PlaneError
from .plane import ExecutionPlane
from .policy import PlaneConfig
from .providers import (CommandProvider, ExecutionProvider, ProcessProvider, ProviderRegistry,
                        ProviderRequest, ReferenceProvider, WasmProvider)

PK_CORE_AVAILABLE = True
try:
    from .component import COMPONENT, ExecutionPlaneComponent
    from .contract import build as build_contract
except ModuleNotFoundError as exc:
    if exc.name != "pk_core" and not (exc.name or "").startswith("pk_core."):
        raise
    _PK_CORE_IMPORT_ERROR = exc
    PK_CORE_AVAILABLE = False
    COMPONENT = None
    ExecutionPlaneComponent = None

    def build_contract():
        raise RuntimeError("pk_core is required to build the PLN-04 certification contract") from _PK_CORE_IMPORT_ERROR


__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "PK_CORE_AVAILABLE",
    "AdmissionConflict",
    "AuditEvent",
    "CapacityExceeded",
    "COMPONENT",
    "ExecutionPlaneComponent",
    "ExecutionPlaneError",
    "InstanceRecord",
    "NoSufficientTier",
    "Node",
    "ResidentTierUnattested",
    "TIERS",
    "TRUST_CLASSES",
    "admit",
    "select_tier",
    "teardown",
    "ERROR_CODES",
    "PlaneError",
    "ExecutionPlane",
    "PlaneConfig",
    "CommandProvider",
    "ExecutionProvider",
    "ProcessProvider",
    "ProviderRegistry",
    "ProviderRequest",
    "ReferenceProvider",
    "WasmProvider",
    "build_contract",
]
