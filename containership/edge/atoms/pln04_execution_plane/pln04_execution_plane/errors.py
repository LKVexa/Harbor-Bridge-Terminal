"""M43 - Stable, machine-readable PLN-04 error taxonomy and retryability contract.

Every error that crosses a PLN-04 boundary (Python facade, HTTP transport,
event export) is expressed as a :class:`PlaneError` carrying a stable
``code``.  Retryability is a property of the *code*, never inferred from a
generic exception class at the transport boundary.  Codes are append-only:
a code is never renamed or re-purposed; deprecation is recorded in
``ERROR_CODES[code].deprecated`` and ``docs/ERRORS.md``.
"""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

ERROR_TAXONOMY_VERSION = "PK_PLN04_ERRORS/1"


@dataclass(frozen=True, slots=True)
class ErrorSpec:
    code: str
    category: str
    retryable: bool
    http_status: int
    summary: str
    retry_after_allowed: bool = False
    deprecated: bool = False


_SPECS = [
    # validation
    ErrorSpec("PLN04-VAL-001", "validation", False, 400, "request failed schema or field validation"),
    ErrorSpec("PLN04-VAL-002", "validation", False, 413, "request exceeds size or depth bounds"),
    ErrorSpec("PLN04-VAL-003", "validation", False, 415, "unsupported schema version or content type"),
    # authentication / authorization
    ErrorSpec("PLN04-AUTHN-001", "authentication", False, 401, "actor credential missing, malformed, expired or not verifiable"),
    ErrorSpec("PLN04-AUTHZ-001", "authorization", False, 403, "actor lacks the capability for this operation"),
    ErrorSpec("PLN04-AUTHZ-002", "authorization", False, 403, "workload owned by another tenant"),
    # policy
    ErrorSpec("PLN04-POL-001", "policy", False, 422, "no attested tier satisfies the trust-class floor"),
    ErrorSpec("PLN04-POL-002", "policy", False, 422, "workload classification is unsigned, invalid or stale"),
    ErrorSpec("PLN04-POL-003", "policy", False, 422, "artifact digest, signature or allowlist check failed"),
    ErrorSpec("PLN04-POL-004", "policy", False, 422, "site/residency policy forbids placement"),
    ErrorSpec("PLN04-POL-005", "policy", False, 422, "co-residency policy forbids placement"),
    ErrorSpec("PLN04-POL-006", "policy", False, 503, "admission disabled by emergency switch or rollout stage", retry_after_allowed=True),
    # capacity
    ErrorSpec("PLN04-CAP-001", "capacity", True, 429, "node or tenant admission ceiling reached", retry_after_allowed=True),
    ErrorSpec("PLN04-CAP-002", "capacity", True, 429, "admission queue full (backpressure)", retry_after_allowed=True),
    # conflict
    ErrorSpec("PLN04-CONF-001", "conflict", False, 409, "live tier below new floor; teardown/recreate required"),
    ErrorSpec("PLN04-CONF-002", "conflict", False, 409, "idempotency key reused with a different request"),
    # attestation
    ErrorSpec("PLN04-ATT-001", "attestation", False, 409, "resident tier lost attestation; workload quarantined"),
    ErrorSpec("PLN04-ATT-002", "attestation", True, 503, "attestation evidence stale, replayed or unverifiable", retry_after_allowed=True),
    # provider / dependency
    ErrorSpec("PLN04-PROV-001", "provider", True, 502, "execution provider failed the operation", retry_after_allowed=True),
    ErrorSpec("PLN04-PROV-002", "provider", False, 500, "no approved provider registered for the tier"),
    ErrorSpec("PLN04-PROV-003", "provider", False, 500, "provider could not prove resource zeroization"),
    ErrorSpec("PLN04-DEP-001", "dependency", True, 503, "required dependency unavailable (circuit open)", retry_after_allowed=True),
    # timeout / cancellation
    ErrorSpec("PLN04-TIME-001", "timeout", True, 504, "operation deadline exceeded", retry_after_allowed=True),
    ErrorSpec("PLN04-TIME-002", "cancellation", False, 499, "operation cancelled by caller"),
    # state / fencing
    ErrorSpec("PLN04-STATE-001", "state", True, 409, "stale version or compare-and-swap conflict"),
    ErrorSpec("PLN04-STATE-002", "fencing", False, 409, "stale fencing epoch; ownership moved"),
    ErrorSpec("PLN04-STATE-003", "state", False, 500, "persistent state corrupt or failed integrity check"),
    ErrorSpec("PLN04-STATE-004", "state", False, 409, "illegal lifecycle transition"),
    # internal
    ErrorSpec("PLN04-INT-001", "internal", False, 500, "internal error"),
]

ERROR_CODES: Mapping[str, ErrorSpec] = MappingProxyType({spec.code: spec for spec in _SPECS})

_SAFE_DETAIL_KEYS = frozenset({
    "workload", "tenant", "tier", "trust_class", "minimum_tier", "attested", "site",
    "limit", "field", "reason", "provider", "epoch", "expected_epoch", "state",
    "from_state", "to_state", "retry_after_s", "queue_depth", "dependency",
})


class PlaneError(RuntimeError):
    """Typed PLN-04 error with a stable code and sanitised public details."""

    def __init__(
        self,
        code: str,
        message: str | None = None,
        *,
        details: Mapping[str, object] | None = None,
        request_id: str | None = None,
        retry_after_s: float | None = None,
        cause: BaseException | None = None,
    ) -> None:
        spec = ERROR_CODES.get(code)
        if spec is None:
            raise ValueError(f"unknown PLN-04 error code: {code!r}")
        if retry_after_s is not None and not spec.retry_after_allowed:
            raise ValueError(f"{code} does not permit retry-after guidance")
        super().__init__(message or spec.summary)
        self.code = code
        self.spec = spec
        self.request_id = request_id
        self.retry_after_s = retry_after_s
        self.details = {k: v for k, v in dict(details or {}).items() if k in _SAFE_DETAIL_KEYS}
        if cause is not None:
            self.__cause__ = cause

    def __str__(self) -> str:
        return f"{self.code}: {self.args[0] if self.args else self.spec.summary}"

    @property
    def retryable(self) -> bool:
        return self.spec.retryable

    def public(self) -> dict[str, object]:
        body: dict[str, object] = {
            "error_code": self.code,
            "category": self.spec.category,
            "retryable": self.spec.retryable,
            "message": self.spec.summary,
            "details": self.details,
        }
        if self.request_id:
            body["request_id"] = self.request_id
        if self.retry_after_s is not None:
            body["retry_after_s"] = self.retry_after_s
        return body


def from_exception(exc: BaseException, request_id: str | None = None) -> PlaneError:
    """Map legacy runtime exceptions onto stable codes (never guesses retryability)."""
    from . import runtime  # local import: runtime has no dependency on errors

    if isinstance(exc, PlaneError):
        return exc
    mapping = (
        (runtime.NoSufficientTier, "PLN04-POL-001"),
        (runtime.AdmissionConflict, "PLN04-CONF-001"),
        (runtime.CapacityExceeded, "PLN04-CAP-001"),
        (runtime.ResidentTierUnattested, "PLN04-ATT-001"),
        (PermissionError, "PLN04-AUTHZ-002"),
        (ValueError, "PLN04-VAL-001"),
        (TypeError, "PLN04-VAL-001"),
        (TimeoutError, "PLN04-TIME-001"),
    )
    for exc_type, code in mapping:
        if isinstance(exc, exc_type):
            return PlaneError(code, request_id=request_id, cause=exc)
    return PlaneError("PLN04-INT-001", request_id=request_id, cause=exc)
