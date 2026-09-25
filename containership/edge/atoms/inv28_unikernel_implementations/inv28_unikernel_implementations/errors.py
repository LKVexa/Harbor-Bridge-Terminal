"""Stable reason codes and structured refusal/validation errors for INV-28 (MC-025, MC-026).

Every safety-relevant outcome carries a code from :class:`Reason`.  Codes are part of the public
interface (``schemas/PK_TOOLCHAIN_SELECTION-2.schema.json`` enumerates them); a code is never
renamed or reused - it is deprecated and a new one added (see docs/MIGRATION.md).  Human text is
advisory; tests and downstream consumers assert on ``code`` only.
"""
from __future__ import annotations

from enum import Enum


class Reason(str, Enum):
    # --- per-candidate elimination codes -------------------------------------------------------
    LANGUAGE_UNSUPPORTED = "TC_LANGUAGE_UNSUPPORTED"
    RUNTIME_UNSUPPORTED = "TC_RUNTIME_UNSUPPORTED"
    ARCH_UNSUPPORTED = "TC_ARCH_UNSUPPORTED"
    DEVICE_UNSUPPORTED = "TC_DEVICE_UNSUPPORTED"
    FEATURE_UNSUPPORTED = "TC_FEATURE_UNSUPPORTED"
    HYPERVISOR_UNSUPPORTED = "TC_HYPERVISOR_UNSUPPORTED"
    PROVIDER_UNSUPPORTED = "TC_PROVIDER_UNSUPPORTED"
    ABI_UNSUPPORTED = "TC_ABI_UNSUPPORTED"
    LIMITATION_CONFLICT = "TC_LIMITATION_CONFLICT"
    SITE_ARCH_UNSUPPORTED = "TC_SITE_ARCH_UNSUPPORTED"
    SITE_HYPERVISOR_UNSUPPORTED = "TC_SITE_HYPERVISOR_UNSUPPORTED"
    MATURITY_BELOW_POLICY = "TC_MATURITY_BELOW_POLICY"
    NO_SECURITY_CONTACT = "TC_NO_SECURITY_CONTACT"
    SECURITY_RESPONSE_INADEQUATE = "TC_SECURITY_RESPONSE_INADEQUATE"
    REVIEW_STALE = "TC_REVIEW_STALE"
    REVIEW_MISSING = "TC_REVIEW_MISSING"
    REVIEW_REJECTED = "TC_REVIEW_REJECTED"
    LIFECYCLE_NOT_SELECTABLE = "TC_LIFECYCLE_NOT_SELECTABLE"
    EOL = "TC_END_OF_LIFE"
    ADVISORY_OPEN = "TC_ADVISORY_OPEN"
    NOT_CERTIFIED = "TC_NOT_CERTIFIED"
    CERTIFICATION_INVALID = "TC_CERTIFICATION_INVALID"
    INTEGRITY_MISSING = "TC_INTEGRITY_MISSING"
    POLICY_DENIED = "TC_POLICY_DENIED"
    DISABLED = "TC_DISABLED"
    NOT_IN_ROLLOUT = "TC_NOT_IN_ROLLOUT"
    # --- whole-request outcomes ----------------------------------------------------------------
    NO_SUITABLE_TOOLCHAIN = "SEL_NO_SUITABLE_TOOLCHAIN"
    INVALID_REQUEST = "SEL_INVALID_REQUEST"
    LIMIT_EXCEEDED = "SEL_LIMIT_EXCEEDED"
    DEADLINE_EXCEEDED = "SEL_DEADLINE_EXCEEDED"
    CANCELLED = "SEL_CANCELLED"
    DEPENDENCY_UNAVAILABLE = "SEL_DEPENDENCY_UNAVAILABLE"
    CLOCK_UNTRUSTED = "SEL_CLOCK_UNTRUSTED"
    POLICY_INVALID = "SEL_POLICY_INVALID"
    # --- registry ------------------------------------------------------------------------------
    REGISTRY_CONFLICT = "REG_REVISION_CONFLICT"
    REGISTRY_DUPLICATE = "REG_DUPLICATE"
    REGISTRY_UNKNOWN = "REG_UNKNOWN_TOOLCHAIN"
    REGISTRY_INTEGRITY = "REG_INTEGRITY_FAILURE"
    REGISTRY_TRANSITION = "REG_ILLEGAL_TRANSITION"
    REGISTRY_UNAUTHORIZED = "REG_UNAUTHORIZED"
    REGISTRY_FULL = "REG_CAPACITY_EXCEEDED"
    # --- binding (anti-substitution, MC-098) --------------------------------------------------
    BINDING_MISMATCH = "BIND_ARTIFACT_MISMATCH"
    BINDING_TAMPERED = "BIND_TICKET_TAMPERED"
    BINDING_EXPIRED = "BIND_TICKET_EXPIRED"


#: Codes that always mean "not safe to proceed" - never mapped to success by any consumer.
ALL_CODES = tuple(r.value for r in Reason)


class Inv28Error(Exception):
    """Base error: always carries a stable code."""

    def __init__(self, code: Reason, message: str = "", **detail):
        self.code = Reason(code)
        self.detail = detail
        super().__init__(f"{self.code.value}: {message}" if message else self.code.value)

    def to_dict(self) -> dict:
        return {"code": self.code.value, "message": str(self), "detail": {k: _plain(v) for k, v in self.detail.items()}}


class ValidationError(Inv28Error, ValueError):
    """Malformed, ambiguous or unsupported input (fails closed)."""

    def __init__(self, message: str, *, code: Reason = Reason.INVALID_REQUEST, **detail):
        super().__init__(code, message, **detail)


class RegistryError(Inv28Error):
    pass


class BindingError(Inv28Error):
    pass


class RefusalError(Inv28Error, RuntimeError):
    """Raised when selection refuses; ``refusal`` is the structured :class:`selection.Refusal`."""

    def __init__(self, refusal):
        self.refusal = refusal
        super().__init__(Reason(refusal.code), refusal.summary)


def _plain(v):
    if isinstance(v, Enum):
        return v.value
    if isinstance(v, (list, tuple, set, frozenset)):
        return [_plain(x) for x in v]
    return v
