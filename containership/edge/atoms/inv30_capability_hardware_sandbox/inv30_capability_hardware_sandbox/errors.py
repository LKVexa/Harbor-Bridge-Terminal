# SPDX-License-Identifier: LicenseRef-LinearFinance-Proprietary
"""PK_FAILURE/1 — the machine-readable failure envelope for every INV-30 boundary (GAP-019).

Every refusal crossing a boundary is rendered as one envelope. ``retryable`` and
``terminal`` are mutually exclusive and derived from the code table, never from
caller input, so a client cannot be told to retry a security refusal.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass

FAILURE_SCHEMA = "PK_FAILURE/1"

#: code -> (category, retryable, terminal, http-ish status)
CODES: dict[str, tuple[str, bool, bool, int]] = {
    "BOUNDS_VIOLATION":        ("security", False, True, 403),
    "PERMISSION_VIOLATION":    ("security", False, True, 403),
    "AMPLIFICATION":           ("security", False, True, 403),
    "INVALIDATED":             ("security", False, True, 410),
    "UNAUTHENTICATED":         ("security", False, True, 401),
    "UNAUTHORIZED":            ("security", False, True, 403),
    "REPLAY":                  ("security", False, True, 409),
    "TENANT_MISMATCH":         ("security", False, True, 403),
    "PROVENANCE_INVALID":      ("security", False, True, 403),
    "SCHEMA_INVALID":          ("input", False, True, 400),
    "UNSUPPORTED_VERSION":     ("compatibility", False, True, 426),
    "LIMIT_EXCEEDED":          ("capacity", False, True, 413),
    "OVERLOADED":              ("capacity", True, False, 429),
    "CIRCUIT_OPEN":            ("dependency", True, False, 503),
    "DEADLINE_EXCEEDED":       ("timeout", True, False, 504),
    "CANCELLED":               ("timeout", False, True, 499),
    "BACKEND_UNAVAILABLE":     ("dependency", True, False, 503),
    "HARDWARE_REQUIRED":       ("policy", False, True, 412),
    "QUARANTINED":             ("policy", False, True, 423),
    "DISABLED":                ("policy", False, True, 423),
    "CONFIG_INVALID":          ("config", False, True, 500),
    "DEPENDENCY_INCOMPATIBLE": ("dependency", False, True, 500),
    "IDEMPOTENCY_CONFLICT":    ("input", False, True, 409),
    "NOT_FOUND":               ("input", False, True, 404),
    "INTERNAL":                ("internal", False, True, 500),
}


class Inv30Error(Exception):
    """Base for non-capability INV-30 refusals; carries a stable code."""

    code = "INTERNAL"

    def __init__(self, message: str = "", *, code: str | None = None):
        super().__init__(message)
        if code is not None:
            if code not in CODES:
                raise ValueError(f"unregistered failure code {code!r}")
            self.code = code

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


def _mk(name: str, code: str):
    return type(name, (Inv30Error,), {"code": code, "__doc__": f"Refusal with code {code}."})


Unauthenticated = _mk("Unauthenticated", "UNAUTHENTICATED")
Unauthorized = _mk("Unauthorized", "UNAUTHORIZED")
Replay = _mk("Replay", "REPLAY")
TenantMismatch = _mk("TenantMismatch", "TENANT_MISMATCH")
ProvenanceInvalid = _mk("ProvenanceInvalid", "PROVENANCE_INVALID")
SchemaInvalid = _mk("SchemaInvalid", "SCHEMA_INVALID")
UnsupportedVersion = _mk("UnsupportedVersion", "UNSUPPORTED_VERSION")
LimitExceeded = _mk("LimitExceeded", "LIMIT_EXCEEDED")
Overloaded = _mk("Overloaded", "OVERLOADED")
CircuitOpen = _mk("CircuitOpen", "CIRCUIT_OPEN")
DeadlineExceeded = _mk("DeadlineExceeded", "DEADLINE_EXCEEDED")
Cancelled = _mk("Cancelled", "CANCELLED")
BackendUnavailable = _mk("BackendUnavailable", "BACKEND_UNAVAILABLE")
HardwareRequired = _mk("HardwareRequired", "HARDWARE_REQUIRED")
Quarantined = _mk("Quarantined", "QUARANTINED")
Disabled = _mk("Disabled", "DISABLED")
ConfigInvalid = _mk("ConfigInvalid", "CONFIG_INVALID")
DependencyIncompatible = _mk("DependencyIncompatible", "DEPENDENCY_INCOMPATIBLE")
IdempotencyConflict = _mk("IdempotencyConflict", "IDEMPOTENCY_CONFLICT")
NotFound = _mk("NotFound", "NOT_FOUND")


@dataclass(frozen=True)
class FailureEnvelope:
    code: str
    message: str
    correlation_id: str
    element: str = "INV-30"
    component_version: str = ""

    def to_dict(self) -> dict:
        category, retryable, terminal, status = CODES.get(self.code, CODES["INTERNAL"])
        return {
            "schema": FAILURE_SCHEMA,
            "element": self.element,
            "component_version": self.component_version,
            "code": self.code if self.code in CODES else "INTERNAL",
            "category": category,
            "status": status,
            "retryable": retryable,
            "terminal": terminal,
            "message": self.message,
            "correlation_id": self.correlation_id,
        }


def envelope(exc: BaseException, correlation_id: str | None = None, version: str = "") -> dict:
    """Render any exception as PK_FAILURE/1. Unknown exceptions become INTERNAL with a generic message."""
    code = getattr(exc, "code", None)
    if code in CODES:
        message = str(exc)
    else:
        code, message = "INTERNAL", "internal error (details withheld; see correlated log)"
    return FailureEnvelope(code, message, correlation_id or uuid.uuid4().hex, component_version=version).to_dict()
