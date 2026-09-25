"""INV-37 - Bulk data plane.

The integrity/resume primitives are dependency-free.  The optional Post-Kubernetes
`pk_core` adapter is exposed when `pk_core` is installed.
"""
from __future__ import annotations

__version__ = "4.3.0"
ELEMENT_ID = "INV-37"
ELEMENT_NAME = "Bulk data plane"

from .data_plane import (
    CHUNK,
    CHUNK_SCHEMA,
    MANIFEST_SCHEMA,
    RESUME_SCHEMA,
    BoundedTransferPool,
    Receiver,
    TransferLimits,
    TransferState,
    manifest,
    validate_manifest,
    verify_object,
)
from .errors import (
    CodedError,
    ConfigError,
    IllegalTransition,
    SecurityRejected,
    AdmissionRejected,
    BulkDataPlaneError,
    DigestMismatch,
    InvalidManifest,
    TransferClosed,
    TransferIncomplete,
)
from .outcomes import ERROR_CODES, Outcome, classify
from .lifecycle import Event, Lifecycle, StateMachine
from . import config, checkpoint, security, quota, retry, telemetry, shm_transport
from .service import BulkDataPlane, negotiate


def build_contract():
    """Build the optional pk_core contract, raising a clear error if unavailable."""
    try:
        from .contract import build
    except ModuleNotFoundError as exc:
        if exc.name and exc.name.startswith("pk_core"):
            raise RuntimeError("pk_core is required to build the INV-37 governance contract") from exc
        raise
    return build()


try:
    from .component import COMPONENT, BulkDataPlaneComponent
except ModuleNotFoundError as exc:
    if exc.name and exc.name.startswith("pk_core"):
        COMPONENT = None
        BulkDataPlaneComponent = None
    else:
        raise

__all__ = [
    "__version__",
    "ELEMENT_ID",
    "ELEMENT_NAME",
    "CHUNK",
    "CHUNK_SCHEMA",
    "MANIFEST_SCHEMA",
    "RESUME_SCHEMA",
    "TransferLimits",
    "TransferState",
    "Receiver",
    "BoundedTransferPool",
    "manifest",
    "validate_manifest",
    "verify_object",
    "BulkDataPlaneError",
    "InvalidManifest",
    "DigestMismatch",
    "TransferIncomplete",
    "AdmissionRejected",
    "TransferClosed",
    "COMPONENT",
    "BulkDataPlaneComponent",
    "build_contract",
    "CodedError",
    "ConfigError",
    "IllegalTransition",
    "SecurityRejected",
    "ERROR_CODES",
    "Outcome",
    "classify",
    "Event",
    "Lifecycle",
    "StateMachine",
    "BulkDataPlane",
    "negotiate",
    "config",
    "checkpoint",
    "security",
    "quota",
    "retry",
    "telemetry",
    "shm_transport",
]
