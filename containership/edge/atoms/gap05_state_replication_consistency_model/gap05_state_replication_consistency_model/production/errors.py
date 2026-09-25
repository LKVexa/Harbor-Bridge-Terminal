"""Stable reason codes and error hierarchy for the GAP-05 production layer.

Every refusal raised by the production layer is a ``Gap05Error`` carrying a stable
``code`` so operators, metrics and audit records can distinguish correctness failures
(``CORR_*``), security failures (``SEC_*``), capacity failures (``CAP_*``) and
dependency failures (``DEP_*``) without parsing messages.
"""
from __future__ import annotations


class Gap05Error(Exception):
    code = "GAP05_ERROR"
    retryable = False

    def __init__(self, message: str, *, code: str | None = None, retryable: bool | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code
        if retryable is not None:
            self.retryable = retryable

    def as_record(self) -> dict:
        return {"code": self.code, "retryable": self.retryable, "message": str(self)}


class SecurityError(Gap05Error):
    code = "SEC_DENIED"


class AuthenticationError(SecurityError):
    code = "SEC_UNAUTHENTICATED"


class AuthorizationError(SecurityError):
    code = "SEC_FORBIDDEN"


class ProvenanceError(SecurityError):
    code = "SEC_BAD_PROVENANCE"


class CounterViolation(SecurityError):
    code = "SEC_COUNTER_VIOLATION"


class FencedError(SecurityError):
    code = "SEC_FENCED"


class NamespaceError(SecurityError):
    code = "SEC_NAMESPACE"


class SchemaError(Gap05Error):
    code = "CORR_SCHEMA"


class IncompatibleVersion(Gap05Error):
    code = "CORR_INCOMPATIBLE_VERSION"


class IntegrityError(Gap05Error):
    code = "CORR_INTEGRITY"


class CapacityError(Gap05Error):
    code = "CAP_EXHAUSTED"
    retryable = True


class LimitExceeded(Gap05Error):
    code = "CAP_LIMIT"


class DependencyUnavailable(Gap05Error):
    code = "DEP_UNAVAILABLE"
    retryable = True


class ConfigError(Gap05Error):
    code = "CORR_CONFIG"


class ConflictStillOpen(Gap05Error):
    code = "CORR_CONFLICT_OPEN"
