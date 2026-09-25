"""INV-22 structured error model (MC-16).

Stable, namespaced, machine-readable error codes.  Codes are additive-only:
an existing code is never repurposed.  Every code carries retryability, a CLI
exit mapping, disclosure level, operator action, and whether it is terminal
for certification.  Raw Python exceptions are internal details only.
"""
from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping

ERROR_SCHEMA = "PK_BRANCH_ERROR/1"
_MAX_DETAIL_KEYS = 16
_MAX_DETAIL_TEXT = 256


@dataclass(frozen=True)
class CodeSpec:
    code: str
    category: str
    retryable: bool
    exit_code: int
    disclosure: str          # "public" | "operator"
    operator_action: str
    cert_terminal: bool
    slo_counted: bool        # counts toward error-rate SLOs (expected refusals do not)


def _spec(code, category, retryable, exit_code, disclosure, action, terminal, slo):
    return code, CodeSpec(code, category, retryable, exit_code, disclosure, action, terminal, slo)


REGISTRY: Mapping[str, CodeSpec] = MappingProxyType(dict([
    _spec("INV22.VALIDATION.INVALID_INPUT", "validation", False, 2, "public", "fix the request", True, False),
    _spec("INV22.VALIDATION.SCHEMA", "validation", False, 2, "public", "fix the document to match the schema", True, False),
    _spec("INV22.VALIDATION.LIMIT", "resource_limit", False, 2, "public", "reduce payload size/depth/count", True, False),
    _spec("INV22.CLASSIFY.UNCLASSIFIED", "classification", False, 3, "public", "classify the interface in the matrix", True, False),
    _spec("INV22.CLASSIFY.INVALID", "classification", False, 3, "public", "correct the classification value", True, False),
    _spec("INV22.CLASSIFY.NEEDS_REVIEW", "classification", False, 3, "public", "approve a reviewed override", True, False),
    _spec("INV22.TRANSLATE.DIVERGENT", "translation", False, 4, "public", "none; semantics cannot be shimmed", True, False),
    _spec("INV22.TRANSLATE.NO_TRANSLATOR", "translation", False, 4, "public", "register a proven translator", True, False),
    _spec("INV22.TRANSLATE.NOT_REPRESENTABLE", "translation", False, 4, "public", "input outside the translator domain", False, False),
    _spec("INV22.TRANSLATE.UNSUPPORTED_DIRECTION", "translation", False, 4, "public", "use a supported branch pair", True, False),
    _spec("INV22.TRANSLATE.CAPABILITY_ESCALATION", "security", False, 4, "operator", "investigate translator; it widened rights", True, True),
    _spec("INV22.TRANSLATE.INTERNAL", "internal", False, 70, "operator", "inspect protected diagnostics", True, True),
    _spec("INV22.CERT.UNCERTIFIED_BRANCH", "certification", False, 5, "public", "certify the component for this branch", True, False),
    _spec("INV22.CERT.INVALID_SIGNATURE", "integrity", False, 5, "public", "reject; certificate tampered or wrong key", True, False),
    _spec("INV22.CERT.UNKNOWN_ISSUER", "integrity", False, 5, "public", "add issuer to trust store via approved change", True, False),
    _spec("INV22.CERT.EXPIRED", "certification", False, 5, "public", "renew certification", True, False),
    _spec("INV22.CERT.NOT_YET_VALID", "certification", False, 5, "public", "check clocks / wait for validity", True, False),
    _spec("INV22.CERT.REVOKED", "certification", False, 5, "public", "recertify; this certificate is revoked", True, False),
    _spec("INV22.CERT.SUPERSEDED", "certification", False, 5, "public", "use the successor certificate", True, False),
    _spec("INV22.CERT.SUSPENDED", "certification", False, 5, "public", "resolve the suspension", True, False),
    _spec("INV22.CERT.DIGEST_MISMATCH", "integrity", False, 5, "public", "artifact differs from the certified artifact", True, False),
    _spec("INV22.CERT.STALE_REVOCATION", "certification", True, 5, "public", "refresh revocation data", True, False),
    _spec("INV22.AUTH.UNAUTHENTICATED", "authentication", False, 6, "public", "present valid credentials", True, False),
    _spec("INV22.AUTH.FORBIDDEN", "authorization", False, 6, "public", "request the capability through policy", True, False),
    _spec("INV22.AUTH.SEPARATION_OF_DUTIES", "authorization", False, 6, "public", "a different principal must approve", True, False),
    _spec("INV22.VERSION.UNSUPPORTED", "compatibility", False, 7, "public", "negotiate a supported contract version", True, False),
    _spec("INV22.DEPENDENCY.UNAVAILABLE", "dependency", True, 8, "operator", "restore the dependency", True, True),
    _spec("INV22.DEPENDENCY.INCOMPATIBLE", "dependency", False, 8, "operator", "pin a compatible dependency", True, False),
    _spec("INV22.TIMEOUT.DEADLINE_EXCEEDED", "timeout", True, 9, "public", "retry with a larger budget if idempotent", False, True),
    _spec("INV22.TIMEOUT.CANCELLED", "timeout", False, 9, "public", "none; caller cancelled", False, False),
    _spec("INV22.RESOURCE.OVERLOADED", "resource_limit", True, 10, "public", "back off and retry", False, True),
    _spec("INV22.STORAGE.CONFLICT", "storage", True, 11, "public", "re-read and retry with current revision", False, False),
    _spec("INV22.STORAGE.FAILURE", "storage", True, 11, "operator", "check the store", True, True),
    _spec("INV22.INTEGRITY.CORRUPT", "integrity", False, 12, "operator", "restore from verified backup", True, True),
    _spec("INV22.CONFIG.INVALID", "validation", False, 2, "public", "fix configuration", True, False),
    _spec("INV22.STATE.ILLEGAL_TRANSITION", "state", False, 13, "public", "use a permitted transition", False, False),
    _spec("INV22.STATE.STALE_FENCE", "state", False, 13, "public", "controller is stale; re-read state", False, False),
    _spec("INV22.SITE.FROZEN", "state", False, 13, "public", "site admissions are frozen", False, False),
    _spec("INV22.POLICY.DENIED", "policy", False, 14, "public", "see decision explanation", True, False),
    _spec("INV22.WAIVER.INVALID", "governance", False, 15, "public", "waiver expired, unscoped, or unapproved", True, False),
    _spec("INV22.INTERNAL", "internal", False, 70, "operator", "inspect protected diagnostics", True, True),
]))

_SECRETish = re.compile(r"(?i)(secret|token|password|passwd|private[_-]?key|api[_-]?key|credential|authorization)")


def _bounded(value: Any) -> Any:
    if isinstance(value, (bool, int)) or value is None:
        return value
    text = str(value)
    return text if len(text) <= _MAX_DETAIL_TEXT else text[:_MAX_DETAIL_TEXT] + "...[truncated]"


@dataclass
class Inv22Error(Exception):
    """Structured error.  ``to_dict`` is the external, redacted representation."""

    code: str
    message: str
    details: dict = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cause_code: str | None = None

    def __post_init__(self) -> None:
        if self.code not in REGISTRY:
            # Unknown codes are never emitted; they collapse to INTERNAL.
            self.details = {"unregistered_code": _bounded(self.code)}
            self.code = "INV22.INTERNAL"
        Exception.__init__(self, f"{self.code}: {self.message}")

    @property
    def spec(self) -> CodeSpec:
        return REGISTRY[self.code]

    def to_dict(self) -> dict:
        spec = self.spec
        details = {}
        for key in sorted(self.details)[:_MAX_DETAIL_KEYS]:
            details[str(key)] = "[REDACTED]" if _SECRETish.search(str(key)) else _bounded(self.details[key])
        message = self.message if spec.disclosure == "public" else "operation failed; see protected diagnostics"
        out = {"schema": ERROR_SCHEMA, "code": self.code, "category": spec.category,
               "retryable": spec.retryable, "message": _bounded(message),
               "correlation_id": self.correlation_id, "details": details}
        if self.cause_code in REGISTRY:
            out["cause_code"] = self.cause_code
        return out


def wrap(exc: BaseException, correlation_id: str | None = None) -> Inv22Error:
    """Map any exception to a structured error without serialising the exception."""
    if isinstance(exc, Inv22Error):
        return exc
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code in REGISTRY:
        err = Inv22Error(code, str(exc))
    elif isinstance(exc, (ValueError, TypeError)):
        err = Inv22Error("INV22.VALIDATION.INVALID_INPUT", "invalid input")
    else:
        err = Inv22Error("INV22.INTERNAL", "internal failure")
    if correlation_id:
        err.correlation_id = correlation_id
    return err
