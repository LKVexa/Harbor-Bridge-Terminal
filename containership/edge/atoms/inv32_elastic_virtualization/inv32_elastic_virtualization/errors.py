"""Stable failure taxonomy, outcome codes and retry classification (WS 3, 9, 10).

Clients must branch on ``code`` / ``outcome`` / ``retry``; the human message is
never part of the contract.  Every public exception carries a stable code and a
redacted, JSON-safe ``details`` mapping.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from .model import _StructuredErrorMixin


class Outcome(str, Enum):
    """Machine-readable outcomes (WS 10 outcome taxonomy)."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    DEGRADED_SUCCESS = "degraded_success"
    REJECTED = "rejected"
    RETRYABLE_FAILURE = "retryable_failure"
    TERMINAL_FAILURE = "terminal_failure"
    UNKNOWN_OUTCOME = "unknown_outcome"
    ROLLED_BACK = "rolled_back"


class Retry(str, Enum):
    RETRYABLE = "retryable"
    CONDITIONAL = "conditional"  # only after re-reading state / new expected version
    TERMINAL = "terminal"


class Category(str, Enum):
    VALIDATION = "validation"
    POLICY = "policy"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DEPENDENCY = "dependency"
    TIMEOUT = "timeout"
    CONFLICT = "conflict"
    STALE_STATE = "stale_state"
    INTEGRITY = "integrity"
    OVERLOAD = "overload"
    UNAVAILABLE = "unavailable"
    INTERNAL = "internal"


class ControlError(_StructuredErrorMixin, RuntimeError):
    """Base for control-plane failures added in v4.3.0."""

    code = "internal_error"
    category = Category.INTERNAL
    outcome = Outcome.TERMINAL_FAILURE
    retry = Retry.TERMINAL

    def to_dict(self) -> dict[str, Any]:
        return error_envelope(self)


class ValidationFailed(ControlError):
    code, category, outcome, retry = "validation_failed", Category.VALIDATION, Outcome.REJECTED, Retry.TERMINAL


class SchemaVersionUnsupported(ControlError):
    code, category, outcome, retry = "schema_version_unsupported", Category.VALIDATION, Outcome.REJECTED, Retry.TERMINAL


class AuthenticationFailed(ControlError):
    code, category, outcome, retry = "authentication_failed", Category.AUTHENTICATION, Outcome.REJECTED, Retry.TERMINAL


class AuthorizationDenied(ControlError):
    code, category, outcome, retry = "authorization_denied", Category.AUTHORIZATION, Outcome.REJECTED, Retry.TERMINAL


class PolicyUnavailable(ControlError):
    code, category, outcome, retry = "policy_unavailable", Category.DEPENDENCY, Outcome.RETRYABLE_FAILURE, Retry.RETRYABLE


class Quarantined(ControlError):
    code, category, outcome, retry = "quarantined", Category.POLICY, Outcome.REJECTED, Retry.CONDITIONAL


class EmergencyDisabled(ControlError):
    code, category, outcome, retry = "emergency_disabled", Category.POLICY, Outcome.REJECTED, Retry.CONDITIONAL


class Overloaded(ControlError):
    code, category, outcome, retry = "overloaded", Category.OVERLOAD, Outcome.RETRYABLE_FAILURE, Retry.RETRYABLE


class QuotaExceeded(ControlError):
    code, category, outcome, retry = "quota_exceeded", Category.POLICY, Outcome.REJECTED, Retry.CONDITIONAL


class CircuitOpen(ControlError):
    code, category, outcome, retry = "circuit_open", Category.DEPENDENCY, Outcome.RETRYABLE_FAILURE, Retry.RETRYABLE


class DeadlineExceeded(ControlError):
    code, category, outcome, retry = "deadline_exceeded", Category.TIMEOUT, Outcome.RETRYABLE_FAILURE, Retry.CONDITIONAL


class Cancelled(ControlError):
    code, category, outcome, retry = "cancelled", Category.TIMEOUT, Outcome.REJECTED, Retry.CONDITIONAL


class StaleExpectedState(ControlError):
    code, category, outcome, retry = "stale_expected_state", Category.STALE_STATE, Outcome.REJECTED, Retry.CONDITIONAL


class FencingRejected(ControlError):
    code, category, outcome, retry = "fencing_rejected", Category.CONFLICT, Outcome.REJECTED, Retry.TERMINAL


class NotOwner(ControlError):
    code, category, outcome, retry = "not_owner", Category.CONFLICT, Outcome.REJECTED, Retry.CONDITIONAL


class GuestBusy(ControlError):
    code, category, outcome, retry = "guest_busy", Category.CONFLICT, Outcome.RETRYABLE_FAILURE, Retry.RETRYABLE


class UnknownOutcomeBlocked(ControlError):
    code, category, outcome, retry = "unknown_outcome_blocked", Category.INTEGRITY, Outcome.UNKNOWN_OUTCOME, Retry.TERMINAL


class CapabilityUnsupported(ControlError):
    code, category, outcome, retry = "capability_unsupported", Category.VALIDATION, Outcome.REJECTED, Retry.TERMINAL


class GuestStateIncompatible(ControlError):
    code, category, outcome, retry = "guest_state_incompatible", Category.POLICY, Outcome.REJECTED, Retry.CONDITIONAL


class IdentityMismatch(ControlError):
    code, category, outcome, retry = "identity_mismatch", Category.INTEGRITY, Outcome.REJECTED, Retry.TERMINAL


class ProviderUnavailable(ControlError):
    code, category, outcome, retry = "provider_unavailable", Category.DEPENDENCY, Outcome.RETRYABLE_FAILURE, Retry.RETRYABLE


class ProviderTimeout(ControlError):
    code, category, outcome, retry = "provider_timeout", Category.TIMEOUT, Outcome.UNKNOWN_OUTCOME, Retry.CONDITIONAL


class ProviderRejected(ControlError):
    code, category, outcome, retry = "provider_rejected", Category.DEPENDENCY, Outcome.REJECTED, Retry.TERMINAL


class ProviderInvariantViolation(ControlError):
    code, category, outcome, retry = "provider_invariant_violation", Category.INTEGRITY, Outcome.TERMINAL_FAILURE, Retry.TERMINAL


class CapacityUntrusted(ControlError):
    code, category, outcome, retry = "capacity_untrusted", Category.INTEGRITY, Outcome.REJECTED, Retry.CONDITIONAL


class StoreIntegrityError(ControlError):
    code, category, outcome, retry = "store_integrity_error", Category.INTEGRITY, Outcome.TERMINAL_FAILURE, Retry.TERMINAL


class ConfigInvalid(ControlError):
    code, category, outcome, retry = "config_invalid", Category.VALIDATION, Outcome.REJECTED, Retry.TERMINAL


class NotReady(ControlError):
    code, category, outcome, retry = "not_ready", Category.UNAVAILABLE, Outcome.RETRYABLE_FAILURE, Retry.RETRYABLE


class ShuttingDown(ControlError):
    code, category, outcome, retry = "shutting_down", Category.UNAVAILABLE, Outcome.RETRYABLE_FAILURE, Retry.RETRYABLE


# Codes emitted by the v4.2.0 model, classified for the retry policy.
LEGACY_CODES: dict[str, tuple[Category, Outcome, Retry]] = {
    "reserve_breach": (Category.POLICY, Outcome.REJECTED, Retry.CONDITIONAL),
    "floor_breach": (Category.POLICY, Outcome.REJECTED, Retry.TERMINAL),
    "unknown_guest": (Category.VALIDATION, Outcome.REJECTED, Retry.TERMINAL),
    "invalid_adjustment_record": (Category.VALIDATION, Outcome.REJECTED, Retry.TERMINAL),
    "stale_adjustment": (Category.STALE_STATE, Outcome.REJECTED, Retry.CONDITIONAL),
    "replay_conflict": (Category.CONFLICT, Outcome.REJECTED, Retry.TERMINAL),
    "state_integrity_error": (Category.INTEGRITY, Outcome.TERMINAL_FAILURE, Retry.TERMINAL),
    "audit_integrity_error": (Category.INTEGRITY, Outcome.TERMINAL_FAILURE, Retry.TERMINAL),
}

ERROR_CATALOG: dict[str, dict[str, str]] = {
    cls.code: {"category": cls.category.value, "outcome": cls.outcome.value, "retry": cls.retry.value}
    for cls in ControlError.__subclasses__()
}
ERROR_CATALOG.update(
    {code: {"category": c.value, "outcome": o.value, "retry": r.value} for code, (c, o, r) in LEGACY_CODES.items()}
)
ERROR_CATALOG["internal_error"] = {"category": "internal", "outcome": "terminal_failure", "retry": "terminal"}

_SAFE_DETAIL_TYPES = (str, int, float, bool, type(None))


def _safe_details(details: dict[str, Any]) -> dict[str, Any]:
    from .telemetry import redact  # local import avoids a cycle

    out: dict[str, Any] = {}
    for key, value in details.items():
        if key.startswith("_"):
            continue  # private diagnostics never leave the process
        out[str(key)] = value if isinstance(value, _SAFE_DETAIL_TYPES) else str(value)
    return redact(out)


def error_envelope(exc: BaseException, *, trace_id: str | None = None) -> dict[str, Any]:
    """Return the PK_ERROR/1 envelope for any exception, never leaking raw internals."""
    code = getattr(exc, "code", "internal_error")
    meta = ERROR_CATALOG.get(code, ERROR_CATALOG["internal_error"])
    known = code in ERROR_CATALOG and code != "internal_error"
    envelope = {
        "schema": "PK_ERROR/1",
        "code": code if known else "internal_error",
        "category": meta["category"],
        "outcome": meta["outcome"],
        "retry": meta["retry"],
        "message": str(exc) if known else "internal error",
        "details": _safe_details(getattr(exc, "details", {})) if known else {},
    }
    if trace_id:
        envelope["trace_id"] = trace_id
    from .telemetry import redact

    envelope["message"] = redact({"m": envelope["message"]})["m"]
    return envelope


def classify(exc: BaseException) -> Retry:
    code = getattr(exc, "code", "internal_error")
    return Retry(ERROR_CATALOG.get(code, ERROR_CATALOG["internal_error"])["retry"])
