"""Machine-readable outcome and error model (checklist #6, #21).

Every public failure is an :class:`INV55Error` carrying a stable code from
:data:`ERROR_CATALOG`.  ``to_wire()`` is the only serialisation used at the
boundary; it never carries secret values, provider payloads or stack traces.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"          # served under a declared degraded policy (e.g. cached)
    RETRYABLE = "RETRYABLE"        # transient; caller may retry after retry_after_ms
    TERMINAL = "TERMINAL"          # will not succeed without a change of input/state
    DENIED = "DENIED"              # security decision; never retry automatically


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    outcome: Outcome
    http_status: int
    retry_after_ms: int | None
    public_message: str


ERROR_CATALOG: dict[str, ErrorSpec] = {s.code: s for s in [
    ErrorSpec("INV55-E-DENIED", Outcome.DENIED, 403, None, "secret is unavailable or caller is not authorized"),
    ErrorSpec("INV55-E-UNAUTHENTICATED", Outcome.DENIED, 401, None, "caller identity could not be established"),
    ErrorSpec("INV55-E-INVALID-REQUEST", Outcome.TERMINAL, 400, None, "request does not match the protocol schema"),
    ErrorSpec("INV55-E-UNSUPPORTED-VERSION", Outcome.TERMINAL, 426, None, "no mutually supported protocol version"),
    ErrorSpec("INV55-E-LEASE-EXPIRED", Outcome.TERMINAL, 410, None, "lease ended; resolve again"),
    ErrorSpec("INV55-E-LEASE-REVOKED", Outcome.DENIED, 410, None, "lease was revoked"),
    ErrorSpec("INV55-E-LEASE-CONTEXT", Outcome.DENIED, 403, None, "lease does not match caller context"),
    ErrorSpec("INV55-E-VERSION-RETIRED", Outcome.TERMINAL, 410, None, "secret version is retired"),
    ErrorSpec("INV55-E-QUOTA", Outcome.RETRYABLE, 429, 1000, "quota exhausted for this workload"),
    ErrorSpec("INV55-E-OVERLOADED", Outcome.RETRYABLE, 503, 250, "admission refused under load"),
    ErrorSpec("INV55-E-CIRCUIT-OPEN", Outcome.RETRYABLE, 503, 1000, "provider circuit is open"),
    ErrorSpec("INV55-E-PROVIDER-UNAVAILABLE", Outcome.RETRYABLE, 503, 500, "secret provider is unavailable"),
    ErrorSpec("INV55-E-DEADLINE", Outcome.RETRYABLE, 504, 100, "deadline exceeded"),
    ErrorSpec("INV55-E-FROZEN", Outcome.DENIED, 423, None, "operation is frozen by an operator control"),
    ErrorSpec("INV55-E-CLOCK", Outcome.TERMINAL, 500, None, "clock integrity check failed"),
    ErrorSpec("INV55-E-CONFIG", Outcome.TERMINAL, 500, None, "configuration invalid or not activated"),
    ErrorSpec("INV55-E-CONFLICT", Outcome.TERMINAL, 409, None, "idempotency key reused with a different request"),
    ErrorSpec("INV55-E-INTERNAL", Outcome.TERMINAL, 500, None, "internal error"),
]}


class INV55Error(Exception):
    """Public failure with a stable code.  ``detail`` is operator-only and redacted."""

    def __init__(self, code: str, detail: str = "", *, reason: str | None = None):
        if code not in ERROR_CATALOG:
            code = "INV55-E-INTERNAL"
        self.code = code
        self.spec = ERROR_CATALOG[code]
        self.reason = reason or code.rsplit("-E-", 1)[-1].lower()
        self.detail = detail
        super().__init__(f"{code}: {self.spec.public_message}")

    @property
    def outcome(self) -> Outcome:
        return self.spec.outcome

    def to_wire(self, request_id: str | None = None) -> dict:
        body = {
            "error": {
                "code": self.code,
                "outcome": self.spec.outcome.value,
                "message": self.spec.public_message,
                "reason": self.reason,
            }
        }
        if self.spec.retry_after_ms is not None:
            body["error"]["retry_after_ms"] = self.spec.retry_after_ms
        if request_id:
            body["error"]["request_id"] = request_id
        return body


def from_reference_exception(exc: BaseException) -> INV55Error:
    """Map the 4.2.0 reference-model exceptions onto stable codes."""
    from .. import reference as ref
    mapping = {
        ref.SecretDenied: "INV55-E-DENIED",
        ref.SecretNotFound: "INV55-E-DENIED",       # no existence oracle at the boundary
        ref.LeaseExpired: "INV55-E-LEASE-EXPIRED",
        ref.LeaseRevoked: "INV55-E-LEASE-REVOKED",
        ref.LeaseContextMismatch: "INV55-E-LEASE-CONTEXT",
        ref.VersionRetired: "INV55-E-VERSION-RETIRED",
        ref.ClockRollbackError: "INV55-E-CLOCK",
        ref.InvalidSecretReference: "INV55-E-INVALID-REQUEST",
    }
    for cls, code in mapping.items():
        if isinstance(exc, cls):
            return INV55Error(code)
    return INV55Error("INV55-E-INTERNAL")
