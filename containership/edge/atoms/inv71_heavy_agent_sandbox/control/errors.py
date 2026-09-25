"""Stable, machine-readable outcome model and error-code namespace (C014, C026, C053).

Every failure the control layer can return is a registered ``ErrorCode``.  A code
never carries two materially different recovery actions; unknown internal
failures map to ``INTERNAL.UNCLASSIFIED`` externally while the privileged
diagnostic keeps the original exception type.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class Outcome(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    SECURITY_REJECTED = "SECURITY_REJECTED"


class RetryClass(str, Enum):
    NEVER = "never"                      # denials, integrity failures, validation
    IDEMPOTENT = "idempotent"            # safe to retry with the same idempotency key
    WITH_COMPENSATION = "with_compensation"  # retry only after compensation/reconcile


@dataclass(frozen=True)
class ErrorCode:
    code: str
    namespace: str
    outcome: Outcome
    retry: RetryClass
    http_status: int
    grpc_status: str
    operator_action: str
    user_message: str


def _c(code, outcome, retry, http, grpc, action, msg):
    return ErrorCode(code, code.split(".")[0], outcome, retry, http, grpc, action, msg)


_O, _R = Outcome, RetryClass
REGISTRY: Mapping[str, ErrorCode] = {e.code: e for e in [
    _c("VALIDATION.MALFORMED_REQUEST", _O.TERMINAL_FAILURE, _R.NEVER, 400, "INVALID_ARGUMENT", "none; fix caller", "The request is malformed."),
    _c("VALIDATION.LIMIT_EXCEEDED", _O.TERMINAL_FAILURE, _R.NEVER, 413, "INVALID_ARGUMENT", "none; caller must shrink request", "A request size or count limit was exceeded."),
    _c("VALIDATION.UNKNOWN_FIELD", _O.TERMINAL_FAILURE, _R.NEVER, 400, "INVALID_ARGUMENT", "check client version skew", "The request contains an unsupported field."),
    _c("AUTHN.MISSING_CREDENTIAL", _O.SECURITY_REJECTED, _R.NEVER, 401, "UNAUTHENTICATED", "none", "Authentication is required."),
    _c("AUTHN.INVALID_CREDENTIAL", _O.SECURITY_REJECTED, _R.NEVER, 401, "UNAUTHENTICATED", "investigate if repeated", "The credential is not valid."),
    _c("AUTHN.EXPIRED", _O.SECURITY_REJECTED, _R.NEVER, 401, "UNAUTHENTICATED", "caller must refresh credential", "The credential has expired."),
    _c("AUTHN.REPLAYED", _O.SECURITY_REJECTED, _R.NEVER, 401, "UNAUTHENTICATED", "security review: possible replay", "The credential was already used."),
    _c("AUTHN.REVOKED", _O.SECURITY_REJECTED, _R.NEVER, 401, "UNAUTHENTICATED", "security review", "The credential was revoked."),
    _c("AUTHN.WRONG_AUDIENCE", _O.SECURITY_REJECTED, _R.NEVER, 401, "UNAUTHENTICATED", "check caller configuration", "The credential is for another service."),
    _c("AUTHZ.DENIED", _O.SECURITY_REJECTED, _R.NEVER, 403, "PERMISSION_DENIED", "none unless unexpected", "The caller is not permitted to perform this action."),
    _c("AUTHZ.TENANT_MISMATCH", _O.SECURITY_REJECTED, _R.NEVER, 403, "PERMISSION_DENIED", "security review: tenant substitution", "The caller is not permitted to perform this action."),
    _c("POLICY.EGRESS_DENIED", _O.SECURITY_REJECTED, _R.NEVER, 403, "PERMISSION_DENIED", "none; update allowlist through review", "The destination is not allowed."),
    _c("POLICY.DESTINATION_UNVERIFIED", _O.SECURITY_REJECTED, _R.NEVER, 403, "PERMISSION_DENIED", "check resolver health", "The destination could not be verified."),
    _c("POLICY.CONSTRAINT_CONFLICT", _O.TERMINAL_FAILURE, _R.NEVER, 409, "FAILED_PRECONDITION", "resolve conflicting request constraints", "The request cannot satisfy its constraints."),
    _c("POLICY.EMERGENCY_DISABLED", _O.TERMINAL_FAILURE, _R.NEVER, 503, "UNAVAILABLE", "see incident; emergency disable active", "New sessions are disabled."),
    _c("CAPACITY.ADMISSION_REJECTED", _O.RETRYABLE_FAILURE, _R.IDEMPOTENT, 429, "RESOURCE_EXHAUSTED", "check capacity dashboard", "Capacity is temporarily unavailable."),
    _c("CAPACITY.TENANT_QUOTA", _O.TERMINAL_FAILURE, _R.NEVER, 429, "RESOURCE_EXHAUSTED", "tenant must reduce usage or request quota", "Your quota is exhausted."),
    _c("CAPACITY.SESSION_LIMIT", _O.TERMINAL_FAILURE, _R.NEVER, 413, "RESOURCE_EXHAUSTED", "none", "A session resource limit was reached."),
    _c("DEPENDENCY.UNAVAILABLE", _O.RETRYABLE_FAILURE, _R.IDEMPOTENT, 503, "UNAVAILABLE", "check dependency health", "A dependency is temporarily unavailable."),
    _c("DEPENDENCY.CIRCUIT_OPEN", _O.RETRYABLE_FAILURE, _R.IDEMPOTENT, 503, "UNAVAILABLE", "check dependency health; breaker open", "A dependency is temporarily unavailable."),
    _c("DEPENDENCY.TRUST_UNAVAILABLE", _O.SECURITY_REJECTED, _R.IDEMPOTENT, 503, "UNAVAILABLE", "restore identity/policy/key/time service", "A security dependency is unavailable; failing closed."),
    _c("DEPENDENCY.DEADLINE_EXCEEDED", _O.RETRYABLE_FAILURE, _R.WITH_COMPENSATION, 504, "DEADLINE_EXCEEDED", "reconcile operation before retry", "The operation timed out."),
    _c("ARTIFACT.DIGEST_MISMATCH", _O.SECURITY_REJECTED, _R.NEVER, 422, "FAILED_PRECONDITION", "security review: artifact tamper", "An artifact failed verification."),
    _c("ARTIFACT.SIGNATURE_INVALID", _O.SECURITY_REJECTED, _R.NEVER, 422, "FAILED_PRECONDITION", "security review: signature", "An artifact failed verification."),
    _c("ARTIFACT.UNAPPROVED_VERSION", _O.SECURITY_REJECTED, _R.NEVER, 422, "FAILED_PRECONDITION", "promote through approved manifest", "An artifact version is not approved."),
    _c("ARTIFACT.REVOKED", _O.SECURITY_REJECTED, _R.NEVER, 422, "FAILED_PRECONDITION", "roll forward to non-revoked artifact", "An artifact version was revoked."),
    _c("HYPERVISOR.START_FAILED", _O.RETRYABLE_FAILURE, _R.WITH_COMPENSATION, 500, "INTERNAL", "inspect node; reap resources before retry", "The session could not be started."),
    _c("GUEST.CRASHED", _O.TERMINAL_FAILURE, _R.NEVER, 500, "ABORTED", "inspect guest logs", "The session terminated unexpectedly."),
    _c("NETWORK.SETUP_FAILED", _O.RETRYABLE_FAILURE, _R.WITH_COMPENSATION, 500, "INTERNAL", "inspect node network helper", "Session networking could not be configured."),
    _c("LIFECYCLE.ILLEGAL_TRANSITION", _O.TERMINAL_FAILURE, _R.NEVER, 409, "FAILED_PRECONDITION", "none; caller used session out of order", "The session is not in a state that allows this."),
    _c("LIFECYCLE.STALE_EPOCH", _O.SECURITY_REJECTED, _R.NEVER, 409, "ABORTED", "check controller ownership/failover", "The controller no longer owns this session."),
    _c("LIFECYCLE.SESSION_CLOSED", _O.TERMINAL_FAILURE, _R.NEVER, 410, "FAILED_PRECONDITION", "none", "The session is closed."),
    _c("LIFECYCLE.QUARANTINED", _O.TERMINAL_FAILURE, _R.NEVER, 423, "FAILED_PRECONDITION", "see incident; session/node quarantined", "The session is quarantined."),
    _c("TEARDOWN.VERIFICATION_FAILED", _O.TERMINAL_FAILURE, _R.NEVER, 500, "DATA_LOSS", "quarantine node; manual reap", "Teardown could not be verified."),
    _c("TEARDOWN.TIMEOUT", _O.RETRYABLE_FAILURE, _R.WITH_COMPENSATION, 504, "DEADLINE_EXCEEDED", "reconcile node resources", "Teardown did not finish in time."),
    _c("CONFIG.INVALID", _O.TERMINAL_FAILURE, _R.NEVER, 422, "INVALID_ARGUMENT", "fix configuration", "The configuration is invalid."),
    _c("CONFIG.FORBIDDEN_OVERRIDE", _O.SECURITY_REJECTED, _R.NEVER, 403, "PERMISSION_DENIED", "security review of overlay", "The configuration change is not permitted."),
    _c("CONFIG.STALE_GENERATION", _O.TERMINAL_FAILURE, _R.NEVER, 409, "ABORTED", "rebase on latest generation", "The configuration is out of date."),
    _c("AUDIT.SINK_UNAVAILABLE", _O.RETRYABLE_FAILURE, _R.IDEMPOTENT, 503, "UNAVAILABLE", "restore audit sink; spool nearing limit", "Security audit delivery is unavailable."),
    _c("COMPAT.UNSUPPORTED_VERSION", _O.TERMINAL_FAILURE, _R.NEVER, 426, "FAILED_PRECONDITION", "upgrade peer within supported skew", "The peer version is not supported."),
    _c("INTERNAL.UNCLASSIFIED", _O.TERMINAL_FAILURE, _R.NEVER, 500, "INTERNAL", "open defect; see privileged diagnostic", "An internal error occurred."),
]}


class ControlError(Exception):
    """An error carrying a registered stable code plus safe diagnostic fields."""

    def __init__(self, code: str, detail: str = "", **fields: object) -> None:
        if code not in REGISTRY:
            raise KeyError(f"unregistered error code {code!r}")
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = REGISTRY[code]
        self.detail = detail
        self.fields = dict(fields)

    def to_record(self, *, correlation_id: str = "", operation_id: str = "",
                  session_id: str = "", config_digest: str = "") -> dict[str, object]:
        e = self.code
        return {
            "schema": "PK_HEAVYBOX_ERROR/1",
            "code": e.code,
            "namespace": e.namespace,
            "outcome": e.outcome.value,
            "retryable": e.retry is not RetryClass.NEVER,
            "retry_class": e.retry.value,
            "http_status": e.http_status,
            "grpc_status": e.grpc_status,
            "message": e.user_message,
            "correlation_id": correlation_id,
            "operation_id": operation_id,
            "session_id": session_id,
            "config_digest": config_digest,
        }


def map_exception(exc: BaseException) -> ControlError:
    """Map any exception to a registered code; never leak raw messages externally."""
    if isinstance(exc, ControlError):
        return exc
    from ..sandbox import EgressDenied, LimitExceeded, SessionClosed
    if isinstance(exc, EgressDenied):
        return ControlError("POLICY.EGRESS_DENIED")
    if isinstance(exc, LimitExceeded):
        return ControlError("CAPACITY.SESSION_LIMIT")
    if isinstance(exc, SessionClosed):
        return ControlError("LIFECYCLE.SESSION_CLOSED")
    if isinstance(exc, (ValueError, TypeError)):
        return ControlError("VALIDATION.MALFORMED_REQUEST")
    err = ControlError("INTERNAL.UNCLASSIFIED")
    err.fields["privileged_type"] = type(exc).__name__
    return err
