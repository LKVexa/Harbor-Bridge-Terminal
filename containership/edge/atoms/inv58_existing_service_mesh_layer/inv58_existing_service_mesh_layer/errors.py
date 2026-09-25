"""Stable, machine-readable error envelope and codes for INV-58 (MC-006, INV-58-C026).

Every failure crossing a public INV-58 boundary is expressed as a ``MeshError``
carrying a stable ``code`` from :data:`ERROR_CODES`.  Codes are append-only:
a code is never renamed or re-purposed; retired codes stay listed with
``deprecated=True``.  ``to_envelope()`` never includes secret material or raw
untrusted input beyond a bounded, sanitised excerpt.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ENVELOPE_VERSION = "PK_MESH_ERROR/1"
_MAX_DETAIL_CHARS = 256

# code -> (outcome class, retryable, http-ish status, description)
ERROR_CODES: dict[str, tuple[str, bool, int, str]] = {
    "E_INVALID_ARGUMENT": ("terminal", False, 400, "Input failed validation."),
    "E_UNSUPPORTED_VERSION": ("terminal", False, 400, "Peer requested an unsupported interface version."),
    "E_PAYLOAD_TOO_LARGE": ("terminal", False, 413, "Payload exceeds a declared ceiling."),
    "E_UNAUTHENTICATED": ("terminal", False, 401, "Caller identity could not be established."),
    "E_PERMISSION_DENIED": ("terminal", False, 403, "Caller lacks the required capability."),
    "E_TENANT_SCOPE": ("terminal", False, 403, "Cross-tenant access was refused before state access."),
    "E_IDENTITY_UNMAPPABLE": ("terminal", False, 422, "Mesh identity cannot be mapped safely."),
    "E_BUDGET_EXCEEDED": ("terminal", False, 422, "Requested attempts exceed the total-attempt budget."),
    "E_CONFLICT": ("retryable", True, 409, "Optimistic-concurrency or idempotency conflict."),
    "E_STALE_FENCE": ("terminal", False, 409, "Mutation carried a stale fencing token (stale controller)."),
    "E_CAPACITY": ("retryable", True, 429, "A bounded registry/queue is full."),
    "E_OVERLOADED": ("retryable", True, 503, "Admission control shed the request."),
    "E_CIRCUIT_OPEN": ("retryable", True, 503, "Circuit breaker is open for the dependency."),
    "E_DEADLINE_EXCEEDED": ("retryable", True, 504, "Operation deadline elapsed."),
    "E_CANCELLED": ("terminal", False, 499, "Caller cancelled the operation."),
    "E_DEPENDENCY_UNAVAILABLE": ("retryable", True, 503, "A trust or noncritical dependency is unavailable."),
    "E_FROZEN": ("terminal", False, 423, "Component, tenant or route is frozen/quarantined."),
    "E_NOT_READY": ("retryable", True, 503, "Component lifecycle state does not accept this operation."),
    "E_CONFIG_INVALID": ("terminal", False, 422, "Configuration failed validation; nothing was activated."),
    "E_INTEGRITY": ("terminal", False, 422, "Artifact digest/signature/provenance verification failed."),
    "E_AUDIT_INTEGRITY": ("terminal", False, 500, "Audit chain verification failed."),
    "E_INTERNAL": ("terminal", False, 500, "Invariant violation; component fails closed."),
}


def _sanitise(text: str) -> str:
    text = "".join(ch if 0x20 <= ord(ch) < 0x7F else "?" for ch in str(text))
    return text[:_MAX_DETAIL_CHARS]


@dataclass
class MeshError(Exception):
    code: str
    message: str
    details: dict[str, Any] | None = None
    correlation_id: str | None = None

    def __post_init__(self) -> None:
        if self.code not in ERROR_CODES:
            raise ValueError(f"unknown error code {self.code!r}")
        super().__init__(f"{self.code}: {self.message}")

    @property
    def outcome(self) -> str:
        return ERROR_CODES[self.code][0]

    @property
    def retryable(self) -> bool:
        return ERROR_CODES[self.code][1]

    def to_envelope(self) -> dict[str, Any]:
        details = {}
        for k, v in (self.details or {}).items():
            if isinstance(v, (int, float, bool)) or v is None:
                details[_sanitise(k)] = v
            else:
                details[_sanitise(k)] = _sanitise(v)
        return {
            "envelope": ENVELOPE_VERSION,
            "code": self.code,
            "outcome": self.outcome,
            "retryable": self.retryable,
            "status": ERROR_CODES[self.code][2],
            "message": _sanitise(self.message),
            "details": details,
            "correlation_id": self.correlation_id,
        }
