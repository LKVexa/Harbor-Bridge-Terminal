"""Stable, machine-readable error model for INV-20 (checklist component 4, "Error model").

Every error raised across an INV-20 boundary carries:

* a stable ``code`` (never reworded once released; see docs/policy/SUPPORT_AND_VERSIONING.md),
* a ``category`` separating caller error, policy denial, resource exhaustion, timeout,
  cancellation, upstream error, protocol violation and internal defect,
* a documented ``retryable`` flag,
* a bounded, secret-free ``detail`` string (attacker-controlled input is truncated and
  escaped before it is stored).
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict

ERROR_SCHEMA = "INV20_ERROR/1"
MAX_DETAIL = 160


class Category(str, Enum):
    CALLER = "caller_error"
    POLICY = "policy_denial"
    EXHAUSTION = "resource_exhaustion"
    TIMEOUT = "timeout"
    CANCELLED = "cancellation"
    UPSTREAM = "upstream_error"
    PROTOCOL = "protocol_violation"
    INTERNAL = "internal_defect"
    UNAVAILABLE = "dependency_unavailable"


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    category: Category
    retryable: bool
    summary: str


# The registry is the single source of truth; tests assert that every raised code is here.
REGISTRY: Dict[str, ErrorSpec] = {s.code: s for s in (
    ErrorSpec("E_INVALID_HOST", Category.CALLER, False, "egress target is not a canonical host"),
    ErrorSpec("E_INVALID_METHOD", Category.CALLER, False, "method token invalid"),
    ErrorSpec("E_INVALID_SCHEME", Category.CALLER, False, "scheme unsupported"),
    ErrorSpec("E_INVALID_AUTHORITY", Category.CALLER, False, "authority malformed or contains userinfo"),
    ErrorSpec("E_INVALID_PATH", Category.CALLER, False, "path/query malformed"),
    ErrorSpec("E_INVALID_FIELD", Category.PROTOCOL, False, "header/trailer field name or value invalid"),
    ErrorSpec("E_FORBIDDEN_FIELD", Category.PROTOCOL, False, "field forbidden at this boundary"),
    ErrorSpec("E_FIELD_LIMIT", Category.EXHAUSTION, False, "field count or size limit exceeded"),
    ErrorSpec("E_INVALID_STATUS", Category.PROTOCOL, False, "status code out of range"),
    ErrorSpec("E_BODY_TOO_LARGE", Category.EXHAUSTION, False, "body exceeded configured limit"),
    ErrorSpec("E_NO_OUTGOING", Category.POLICY, False, "world imports no outgoing HTTP"),
    ErrorSpec("E_EGRESS_DENIED", Category.POLICY, False, "destination not authorised"),
    ErrorSpec("E_DNS_DENIED", Category.POLICY, False, "resolved address violates destination policy"),
    ErrorSpec("E_DNS_FAILURE", Category.UPSTREAM, True, "name resolution failed"),
    ErrorSpec("E_REDIRECT_LIMIT", Category.POLICY, False, "redirect depth or loop limit reached"),
    ErrorSpec("E_UNAUTHENTICATED", Category.POLICY, False, "principal could not be verified"),
    ErrorSpec("E_CAPABILITY_INVALID", Category.POLICY, False, "capability forged, expired, revoked or mis-bound"),
    ErrorSpec("E_POLICY_UNAVAILABLE", Category.UNAVAILABLE, True, "policy/identity service unavailable; failed closed"),
    ErrorSpec("E_CONFIG_INVALID", Category.CALLER, False, "configuration rejected by schema"),
    ErrorSpec("E_CONFIG_AUTHORITY", Category.POLICY, False, "overlay attempted to expand authority"),
    ErrorSpec("E_OVERLOADED", Category.EXHAUSTION, True, "admission rejected; load shed"),
    ErrorSpec("E_CIRCUIT_OPEN", Category.UNAVAILABLE, True, "upstream circuit open"),
    ErrorSpec("E_DEADLINE", Category.TIMEOUT, False, "deadline exceeded"),
    ErrorSpec("E_CANCELLED", Category.CANCELLED, False, "operation cancelled"),
    ErrorSpec("E_UPSTREAM_CONNECT", Category.UPSTREAM, True, "upstream connect failed"),
    ErrorSpec("E_UPSTREAM_RESET", Category.UPSTREAM, False, "upstream reset after response head committed"),
    ErrorSpec("E_HANDLER_TRAP", Category.INTERNAL, False, "handler trapped"),
    ErrorSpec("E_ILLEGAL_STATE", Category.INTERNAL, False, "illegal lifecycle transition"),
    ErrorSpec("E_ALREADY_RESOLVED", Category.PROTOCOL, False, "completion resolved more than once"),
    ErrorSpec("E_QUARANTINED", Category.POLICY, False, "tenant/workload quarantined"),
    ErrorSpec("E_NOT_READY", Category.UNAVAILABLE, True, "component not ready for traffic"),
    ErrorSpec("E_AUDIT_UNAVAILABLE", Category.UNAVAILABLE, True, "audit sink unavailable; critical action refused"),
)}


def safe_detail(text: object, limit: int = MAX_DETAIL) -> str:
    """Bound and escape attacker-controlled text before it enters an error or log."""
    s = str(text)
    s = s.encode("unicode_escape", "backslashreplace").decode("ascii", "replace")
    return s if len(s) <= limit else s[: limit - 3] + "..."


class Inv20Error(Exception):
    """Base class: every INV-20 failure has a registered, stable code."""

    code = "E_INTERNAL_UNREGISTERED"

    def __init__(self, detail: object = "", *, code: str | None = None) -> None:
        if code is not None:
            self.code = code
        if self.code not in REGISTRY:
            raise KeyError(f"unregistered error code {self.code}")
        self.detail = safe_detail(detail)
        super().__init__(f"{self.code}: {self.detail}")

    @property
    def spec(self) -> ErrorSpec:
        return REGISTRY[self.code]

    @property
    def retryable(self) -> bool:
        return self.spec.retryable

    @property
    def category(self) -> Category:
        return self.spec.category

    def to_dict(self) -> dict:
        return {"schema": ERROR_SCHEMA, "code": self.code, "category": self.category.value,
                "retryable": self.retryable, "detail": self.detail}


def error_from_dict(d: dict) -> Inv20Error:
    """Decode a structured error; unknown/malformed input decodes to an internal defect, never a pass."""
    if not isinstance(d, dict) or d.get("schema") != ERROR_SCHEMA or d.get("code") not in REGISTRY:
        return Inv20Error("undecodable error record", code="E_ILLEGAL_STATE")
    return Inv20Error(d.get("detail", ""), code=d["code"])
