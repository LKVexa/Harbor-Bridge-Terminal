"""Structured failure taxonomy (INV-40-C014, C026).

Every operational failure carries a stable code, a class that tells the caller
what to do next, and machine-readable details.  Classes:

* ``retryable``  - transient; the same request may be retried with backoff
* ``terminal``   - retrying the same request can never succeed
* ``rejected``   - policy/authz/admission refusal; retry only after a change
* ``degraded``   - the operation succeeded with a stated SLO miss (not raised)
"""
from __future__ import annotations

from ._rt import runtime

RETRYABLE, TERMINAL, REJECTED = "retryable", "terminal", "rejected"

#: code -> (class, http-like status, one-line meaning).  Stable: codes are never
#: renamed or reused (C016); new codes are additive.
CATALOG: dict[str, tuple[str, int, str]] = {
    "PK_FULL_VM_PRIMITIVE_REQUIRED": (TERMINAL, 412, "host lacks hardware virtualization; never emulated"),
    "PK_FULL_VM_FOOTPRINT_EXCEEDED": (REJECTED, 422, "resident footprint above ceiling"),
    "PK_FULL_VM_INVALID_STATE": (REJECTED, 409, "operation illegal for lifecycle state"),
    "PK_FULL_VM_DEVICE_CONFLICT": (REJECTED, 409, "device instance leased by another live guest"),
    "PK_FULL_VM_UNAUTHENTICATED": (REJECTED, 401, "caller credential missing, invalid, expired or replayed"),
    "PK_FULL_VM_FORBIDDEN": (REJECTED, 403, "caller lacks the capability for this operation/tenant"),
    "PK_FULL_VM_INVALID_REQUEST": (REJECTED, 400, "request failed schema validation"),
    "PK_FULL_VM_CONFIG_INVALID": (REJECTED, 422, "configuration failed validation; not activated"),
    "PK_FULL_VM_OVERLOADED": (RETRYABLE, 429, "admission control shed the request"),
    "PK_FULL_VM_QUOTA_EXCEEDED": (REJECTED, 429, "tenant quota exhausted"),
    "PK_FULL_VM_CIRCUIT_OPEN": (RETRYABLE, 503, "provider circuit open after repeated failures"),
    "PK_FULL_VM_PROVIDER_UNAVAILABLE": (RETRYABLE, 503, "hypervisor provider transiently unavailable"),
    "PK_FULL_VM_PROVIDER_FAILED": (TERMINAL, 500, "provider reported a non-retryable failure"),
    "PK_FULL_VM_TIMEOUT": (RETRYABLE, 504, "deadline exceeded; outcome reconciled before retry"),
    "PK_FULL_VM_CANCELLED": (TERMINAL, 499, "caller cancelled the operation"),
    "PK_FULL_VM_STALE_OWNER": (REJECTED, 409, "fencing token older than current lease epoch"),
    "PK_FULL_VM_QUARANTINED": (REJECTED, 423, "guest or tier is quarantined/frozen/disabled"),
    "PK_FULL_VM_TRUST_UNAVAILABLE": (RETRYABLE, 503, "identity/key/time service unavailable; failing closed"),
    "PK_FULL_VM_INTEGRITY_FAILED": (TERMINAL, 422, "artifact digest/signature/version verification failed"),
    "PK_FULL_VM_VERSION_UNSUPPORTED": (REJECTED, 426, "peer protocol version outside supported window"),
    "PK_FULL_VM_GUEST_START_FAILED": (TERMINAL, 500, "guest OS failed to start"),
}


class OpError(runtime.FullVmError):
    """Service-layer operational error with class and details."""

    code = "PK_FULL_VM_ERROR"

    def __init__(self, code: str, message: str, **details: object) -> None:
        if code not in CATALOG:
            raise KeyError(f"unregistered failure code {code}")
        super().__init__(message)
        self.code = code
        self.details = dict(details)

    @property
    def klass(self) -> str:
        return CATALOG[self.code][0]

    @property
    def retryable(self) -> bool:
        return self.klass == RETRYABLE

    def as_dict(self) -> dict[str, object]:
        return {"schema": "PK_FULL_VM_ERROR/1", "code": self.code, "message": str(self),
                "class": self.klass, "status": CATALOG[self.code][1],
                "retryable": self.retryable, "details": self.details}


def classify(exc: BaseException) -> dict[str, object]:
    """Map any runtime/service exception to a PK_FULL_VM_ERROR/1 document."""
    if isinstance(exc, OpError):
        return exc.as_dict()
    if isinstance(exc, runtime.FullVmError) and exc.code in CATALOG:
        return OpError(exc.code, str(exc)).as_dict()
    if isinstance(exc, (TypeError, ValueError)):
        return OpError("PK_FULL_VM_INVALID_REQUEST", str(exc)).as_dict()
    return OpError("PK_FULL_VM_PROVIDER_FAILED", f"unclassified: {type(exc).__name__}").as_dict()
