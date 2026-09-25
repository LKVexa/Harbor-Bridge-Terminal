"""GAP-09 - Unified observability."""
from __future__ import annotations

__version__ = "5.0.0"

from .runtime import (
    ABSENT,
    STALENESS_BOUND,
    CapacityExceeded,
    CrossTenantQuery,
    HMACFixtureVerifier,
    InvalidBatch,
    InvalidSample,
    InvalidTime,
    ReplayDetected,
    ReporterAuthority,
    ReporterUntrusted,
    Sample,
    StoredSample,
    ScopeViolation,
    SignalError,
    SignalStore,
    TimestampConflict,
    TrustUnavailable,
    TrustVerifier,
    Unattributed,
)

# Keep the runtime importable and testable even when the orchestration package
# is intentionally installed separately.  Only swallow the known optional
# dependency; unrelated import failures must still surface.
try:
    from .component import COMPONENT, UnifiedObservabilityComponent
    from .contract import ELEMENT_ID, ELEMENT_NAME, build as build_contract
except ModuleNotFoundError as exc:
    if exc.name != "pk_core":
        raise
    COMPONENT = None
    UnifiedObservabilityComponent = None
    ELEMENT_ID = "GAP-09"
    ELEMENT_NAME = "Unified observability"
    build_contract = None

__all__ = [
    "__version__",
    "ABSENT",
    "STALENESS_BOUND",
    "Sample",
    "StoredSample",
    "SignalStore",
    "ReporterAuthority",
    "TrustVerifier",
    "HMACFixtureVerifier",
    "SignalError",
    "ReporterUntrusted",
    "Unattributed",
    "CrossTenantQuery",
    "InvalidSample",
    "InvalidBatch",
    "InvalidTime",
    "ReplayDetected",
    "ScopeViolation",
    "TimestampConflict",
    "TrustUnavailable",
    "CapacityExceeded",
    "COMPONENT",
    "UnifiedObservabilityComponent",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "build_contract",
]
