"""Stable, versioned error-code namespace and canonical outcome model (REQ-OUT-*).

Every public refusal maps one-to-one to an error code, an outcome, a
retryability flag and an operator action.  ``describe()`` never includes
exception text, so seals, tokens and policy internals cannot leak through the
public error surface.
"""
from __future__ import annotations

from typing import Final

from .capabilities import (
    CapabilityError, CrossAuthority, Forged, InvalidGrant, LimitExceeded, Revoked, Widening,
)

ERROR_NAMESPACE_VERSION: Final[str] = "INV41-ERR/1"

OUTCOMES: Final[dict] = {
    "success": {"retryable": False, "caller_action": "proceed"},
    "denied": {"retryable": False, "caller_action": "do not retry; request a proper grant"},
    "invalid": {"retryable": False, "caller_action": "fix the request"},
    "revoked": {"retryable": False, "caller_action": "discard the reference; obtain a new grant"},
    "stale": {"retryable": False, "caller_action": "refresh configuration/credential then resubmit"},
    "unavailable": {"retryable": True, "caller_action": "retry with bounded backoff"},
    "retryable": {"retryable": True, "caller_action": "retry with bounded backoff"},
    "degraded": {"retryable": True, "caller_action": "retry later; privileged work is refused while degraded"},
    "terminal": {"retryable": False, "caller_action": "stop; escalate to owner"},
    "internal-fault": {"retryable": False, "caller_action": "escalate; treated as denial"},
}

# code -> (exception class name, outcome, severity, public-safe message, operator action)
ERROR_CODES: Final[dict] = {
    "INV41-E000": ("CapabilityError", "denied", "high", "capability refused", "inspect audit event"),
    "INV41-E001": ("Forged", "denied", "high", "reference not held or not authentic", "investigate forgery attempt"),
    "INV41-E002": ("Widening", "denied", "high", "requested authority exceeds held authority", "review delegation"),
    "INV41-E003": ("Revoked", "revoked", "medium", "reference revoked", "none; expected after revocation"),
    "INV41-E004": ("InvalidGrant", "denied", "medium", "resource not declared in authority policy", "review policy"),
    "INV41-E005": ("CrossAuthority", "denied", "critical", "reference from another authority domain", "investigate cross-domain injection"),
    "INV41-E006": ("LimitExceeded", "invalid", "medium", "hard limit exceeded", "reduce request size"),
    "INV41-E010": ("ValueError", "invalid", "low", "malformed input", "fix the request"),
    "INV41-E011": ("TypeError", "invalid", "low", "wrong input type", "fix the request"),
    "INV41-E020": ("Overloaded", "retryable", "medium", "admission limit reached", "retry with backoff"),
    "INV41-E021": ("Unavailable", "unavailable", "high", "required dependency unavailable", "check dependency health"),
    "INV41-E022": ("Degraded", "degraded", "high", "component degraded; privileged work refused", "follow degraded-mode runbook"),
    "INV41-E023": ("StaleState", "stale", "high", "stale configuration or credential", "refresh and resubmit"),
    "INV41-E030": ("ConfigRejected", "invalid", "high", "configuration rejected", "fix configuration"),
    "INV41-E031": ("AuthenticationFailed", "denied", "high", "authentication failed", "check credential"),
    "INV41-E032": ("IncompatibleVersion", "terminal", "high", "incompatible version", "upgrade/downgrade peer"),
    "INV41-E099": ("InternalFault", "internal-fault", "critical", "internal fault; request denied", "escalate"),
}


class ServiceError(CapabilityError):
    code = "INV41-E099"
    outcome = "internal-fault"


class Overloaded(ServiceError):
    code = "INV41-E020"
    outcome = "retryable"


class Unavailable(ServiceError):
    code = "INV41-E021"
    outcome = "unavailable"


class Degraded(ServiceError):
    code = "INV41-E022"
    outcome = "degraded"


class StaleState(ServiceError):
    code = "INV41-E023"
    outcome = "stale"


class ConfigRejected(ServiceError, ValueError):
    code = "INV41-E030"
    outcome = "invalid"


class AuthenticationFailed(ServiceError):
    code = "INV41-E031"
    outcome = "denied"


class IncompatibleVersion(ServiceError):
    code = "INV41-E032"
    outcome = "terminal"


# Allowed outcomes per public operation (REQ-OUT-002).
OPERATION_OUTCOMES: Final[dict] = {
    "grant": {"success", "denied", "invalid"},
    "bind_holder": {"success", "denied", "invalid", "revoked"},
    "attenuate": {"success", "denied", "invalid", "revoked"},
    "wrap": {"success", "denied", "invalid", "revoked"},
    "revoke": {"success"},
    "use": {"success", "denied", "invalid", "revoked"},
    "broker.use": {"success", "denied", "invalid", "revoked", "retryable", "degraded", "unavailable", "internal-fault"},
    "config.activate": {"success", "invalid", "stale", "denied"},
    "identity.authenticate": {"success", "denied", "unavailable", "stale", "invalid"},
}


def code_for(exc: BaseException) -> str:
    """Map any exception to a stable code.  Unknown exceptions fail closed as E099."""
    if isinstance(exc, CapabilityError):
        return getattr(exc, "code", "INV41-E000")
    if isinstance(exc, TypeError):
        return "INV41-E011"
    if isinstance(exc, ValueError):
        return "INV41-E010"
    return "INV41-E099"


def describe(exc: BaseException) -> dict:
    """Public-safe error record; exception text is deliberately not included."""
    code = code_for(exc)
    _cls, outcome, severity, message, action = ERROR_CODES[code]
    return {
        "namespace": ERROR_NAMESPACE_VERSION,
        "code": code,
        "outcome": outcome,
        "severity": severity,
        "retryable": OUTCOMES[outcome]["retryable"],
        "message": message,
        "operator_action": action,
    }


__all__ = [
    "ERROR_NAMESPACE_VERSION", "OUTCOMES", "ERROR_CODES", "OPERATION_OUTCOMES", "code_for", "describe",
    "ServiceError", "Overloaded", "Unavailable", "Degraded", "StaleState", "ConfigRejected",
    "AuthenticationFailed", "IncompatibleVersion", "CapabilityError", "Forged", "Widening", "Revoked",
    "InvalidGrant", "CrossAuthority", "LimitExceeded",
]
