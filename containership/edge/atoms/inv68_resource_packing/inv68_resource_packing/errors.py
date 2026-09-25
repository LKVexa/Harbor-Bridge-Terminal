"""Structured failure-code registry for INV-68 (MC-07; C014, C025-C028).

Every refusal or failure crossing the packing boundary is a :class:`PackError`
carrying a stable ``code`` from :data:`REGISTRY`.  Each code declares its
outcome class (``C014`` outcome model), whether the caller may retry, the
HTTP-equivalent status used by transport adapters, and whether the operation is
safe to retry with the *same* idempotency key.  ``to_dict()`` produces the
``PK_PACK_ERROR/1`` document (``schemas/PK_PACK_ERROR_1.schema.json``).
Messages are passed through :func:`redaction.redact_text` so no secret-looking
value is ever echoed back.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Final, Mapping

from .redaction import redact, redact_text

ERROR_SCHEMA: Final = "PK_PACK_ERROR/1"

# outcome classes (C014): success | partial | degraded | retryable | terminal | refused
OUTCOMES: Final = ("success", "partial", "degraded", "retryable", "terminal", "refused")


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    outcome: str
    retryable: bool
    status: int
    summary: str


REGISTRY: Final[Mapping[str, ErrorSpec]] = {
    spec.code: spec
    for spec in (
        ErrorSpec("INVALID_REQUEST", "terminal", False, 400, "request failed schema or semantic validation"),
        ErrorSpec("PAYLOAD_TOO_LARGE", "terminal", False, 413, "request exceeds a declared payload limit"),
        ErrorSpec("UNSUPPORTED_PROTOCOL", "terminal", False, 426, "no mutually supported PK_PACK protocol version"),
        ErrorSpec("UNAUTHENTICATED", "refused", False, 401, "no valid principal credential"),
        ErrorSpec("FORBIDDEN", "refused", False, 403, "principal lacks the required capability or tenant scope"),
        ErrorSpec("REPLAY_DETECTED", "refused", False, 409, "credential nonce was already used"),
        ErrorSpec("IDEMPOTENCY_CONFLICT", "terminal", False, 409, "idempotency key reused with a different request"),
        ErrorSpec("QUOTA_EXCEEDED", "refused", True, 429, "tenant quota or fairness budget exhausted"),
        ErrorSpec("OVERLOADED", "retryable", True, 503, "admission control shed the request"),
        ErrorSpec("CIRCUIT_OPEN", "retryable", True, 503, "a required dependency circuit is open"),
        ErrorSpec("DEADLINE_EXCEEDED", "retryable", True, 504, "the request deadline expired before completion"),
        ErrorSpec("CANCELLED", "terminal", False, 499, "the caller cancelled the request"),
        ErrorSpec("DEPENDENCY_UNAVAILABLE", "retryable", True, 503, "a required dependency call failed"),
        ErrorSpec("STALE_CAPACITY", "retryable", True, 503, "capacity data is older than the staleness bound"),
        ErrorSpec("FROZEN", "refused", True, 503, "packing is frozen/disabled by an operator control"),
        ErrorSpec("NOT_READY", "retryable", True, 503, "component is not ready (no active configuration)"),
        ErrorSpec("CONFIG_INVALID", "terminal", False, 422, "configuration failed validation; nothing activated"),
        ErrorSpec("CONFIG_CONFLICT", "terminal", False, 409, "configuration activation raced another activation"),
        ErrorSpec("AUDIT_UNAVAILABLE", "retryable", True, 503, "security audit sink unavailable; fail-closed op refused"),
        ErrorSpec("SECRET_IN_CONFIG", "terminal", False, 422, "inline secret material rejected; use a secret reference"),
        ErrorSpec("STALE_EPOCH", "refused", False, 409, "a newer controller epoch owns packing (split-brain fence)"),
        ErrorSpec("INTERNAL", "terminal", False, 500, "unexpected internal defect (see correlation id)"),
    )
}


class PackError(Exception):
    """Boundary failure with a registered code."""

    def __init__(self, code: str, message: str = "", *, details: Mapping[str, Any] | None = None,
                 correlation_id: str | None = None):
        if code not in REGISTRY:
            raise ValueError(f"unregistered INV-68 error code {code!r}")
        self.code = code
        self.spec = REGISTRY[code]
        self.message = redact_text(message or self.spec.summary)[:512]
        self.details = redact(dict(details or {}))
        self.correlation_id = correlation_id
        super().__init__(f"{code}: {self.message}")

    @property
    def retryable(self) -> bool:
        return self.spec.retryable

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": ERROR_SCHEMA,
            "code": self.code,
            "outcome": self.spec.outcome,
            "retryable": self.spec.retryable,
            "status": self.spec.status,
            "message": self.message,
            "details": self.details,
            "correlation_id": self.correlation_id,
        }


def registry_document() -> dict[str, Any]:
    """Machine-readable registry (written to ``ERRORS.json`` by the build)."""
    return {
        "schema": "PK_PACK_ERROR_REGISTRY/1",
        "outcomes": list(OUTCOMES),
        "codes": [
            {"code": s.code, "outcome": s.outcome, "retryable": s.retryable, "status": s.status, "summary": s.summary}
            for s in REGISTRY.values()
        ],
    }
