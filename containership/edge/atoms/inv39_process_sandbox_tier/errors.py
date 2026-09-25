"""MC-005 / MC-016 — outcome semantics and stable error-code taxonomy.

Every refusal or failure crossing a public boundary carries a stable code from
``ERROR_CODES``.  Each code maps to exactly one outcome class from ``OUTCOMES``
and a retryability flag; callers branch on the code, never on message text.
Payloads validate against ``schemas/PK_SANDBOX_ERROR-1.schema.json``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

OUTCOMES = ("success", "partial", "degraded", "retryable", "terminal")

# code -> (outcome, retryable, http-ish category, description)
ERROR_CODES: dict[str, tuple[str, bool, str]] = {
    "E_PROFILE_INVALID": ("terminal", False, "profile violates policy or schema"),
    "E_SCHEMA_INVALID": ("terminal", False, "payload fails its public schema"),
    "E_VERSION_UNSUPPORTED": ("terminal", False, "no mutually supported schema/protocol version"),
    "E_UNAUTHENTICATED": ("terminal", False, "caller identity could not be authenticated"),
    "E_UNAUTHORIZED": ("terminal", False, "caller lacks the capability for this operation"),
    "E_APPLY_FAILED": ("terminal", False, "a mandatory isolation control could not be applied"),
    "E_NOT_APPLIED": ("terminal", False, "applied-state read-back absent or mismatched"),
    "E_ATTESTATION_FAILED": ("terminal", False, "evidence signature, binding or freshness failed"),
    "E_BACKEND_UNSUPPORTED": ("terminal", False, "required backend/kernel feature unavailable"),
    "E_STATE_TRANSITION": ("terminal", False, "illegal lifecycle transition"),
    "E_LIMIT_EXCEEDED": ("terminal", False, "request exceeds a hard interface limit"),
    "E_QUOTA_EXCEEDED": ("retryable", True, "tenant quota or concurrency ceiling reached"),
    "E_OVERLOADED": ("retryable", True, "admission control shed the request"),
    "E_CIRCUIT_OPEN": ("retryable", True, "backend circuit breaker is open"),
    "E_TIMEOUT": ("retryable", True, "operation deadline exceeded"),
    "E_CANCELLED": ("terminal", False, "operation cancelled by caller"),
    "E_DEPENDENCY_UNAVAILABLE": ("retryable", True, "a trust dependency is unavailable; failing closed"),
    "E_CONFLICT": ("terminal", False, "idempotency key reused with a different request"),
    "E_OWNERSHIP_LOST": ("terminal", False, "controller lease is stale or held by another owner"),
    "E_QUARANTINED": ("terminal", False, "workload or node is quarantined"),
    "E_CONFIG_INVALID": ("terminal", False, "configuration failed validation; previous config kept"),
    "E_INTERNAL": ("terminal", False, "software defect; see diagnostic record"),
}


class SandboxError(Exception):
    """Structured, code-bearing error.  ``str()`` never includes secrets."""

    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None):
        if code not in ERROR_CODES:
            code, message = "E_INTERNAL", f"unregistered error code {code!r}: {message}"
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details = dict(details or {})

    @property
    def outcome(self) -> str:
        return ERROR_CODES[self.code][0]

    @property
    def retryable(self) -> bool:
        return ERROR_CODES[self.code][1]

    def payload(self, *, trace_id: str | None = None) -> dict[str, Any]:
        return {
            "schema": "PK_SANDBOX_ERROR/1",
            "code": self.code,
            "outcome": self.outcome,
            "retryable": self.retryable,
            "message": self.message[:1024],
            "details": {k: str(v)[:256] for k, v in list(self.details.items())[:32]},
            "trace_id": trace_id,
        }


@dataclass(frozen=True)
class Outcome:
    status: str
    code: str | None = None
    detail: str = ""

    def __post_init__(self) -> None:
        if self.status not in OUTCOMES:
            raise ValueError(f"unknown outcome {self.status!r}")
