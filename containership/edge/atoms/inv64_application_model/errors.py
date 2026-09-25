"""Versioned error envelope for every INV-64 public boundary (MC-06, PK_APP_ERROR/1).

No public error path returns free text alone: every refusal carries a stable
``code`` from :data:`CATALOG`, a ``retryable`` flag, the boundary's
``correlation_id``, and optional bounded ``details``. Messages never echo raw
manifest values (MC-14); callers branch on ``code``.
"""
from __future__ import annotations

from typing import Any, Mapping

ERROR_ENVELOPE_VERSION = "PK_APP_ERROR/1"
MAX_DETAILS = 64

# code -> (retryable, http-like class, description). Adding a code is a minor
# (additive) contract change; removing or re-meaning one is a major change.
CATALOG: dict[str, tuple[bool, int, str]] = {
    # authentication (MC-07)
    "auth.missing": (False, 401, "no credential presented"),
    "auth.malformed": (False, 401, "credential is not a well-formed token"),
    "auth.algorithm": (False, 401, "credential algorithm not allowed"),
    "auth.signature": (False, 401, "credential signature invalid or unknown key id"),
    "auth.expired": (False, 401, "credential expired"),
    "auth.not_yet_valid": (False, 401, "credential not yet valid"),
    "auth.lifetime": (False, 401, "credential lifetime exceeds policy maximum"),
    "auth.issuer": (False, 401, "credential issuer not trusted"),
    "auth.audience": (False, 401, "credential audience mismatch"),
    "auth.revoked": (False, 401, "credential or subject revoked"),
    "auth.replay": (False, 401, "credential already used (replay)"),
    "auth.rate_limited": (True, 429, "too many failed authentications from this source"),
    "auth.trust_unavailable": (True, 503, "trust material unavailable; new trust cannot be established"),
    # authorization (MC-08) and tenancy (MC-16)
    "authz.denied": (False, 403, "no policy grants this capability on this resource"),
    "authz.policy_invalid": (False, 503, "authorization policy failed verification; denying"),
    "tenant.mismatch": (False, 403, "request tenant differs from authenticated tenant"),
    "tenant.cross_reference": (False, 403, "manifest references another tenant's resource"),
    # admission / semantics (MC-09)
    "admission.overloaded": (True, 429, "admission queue full"),
    "admission.tenant_quota": (True, 429, "tenant concurrency quota exhausted"),
    "deadline.exceeded": (True, 504, "deadline exceeded"),
    "deadline.invalid": (False, 400, "deadline missing, non-positive or above maximum"),
    "request.cancelled": (False, 499, "request cancelled by caller"),
    "idempotency.conflict": (False, 409, "idempotency key reused with a different request"),
    "idempotency.invalid": (False, 400, "idempotency key malformed"),
    "version.unsupported": (False, 400, "no mutually supported protocol version"),
    "version.downgrade_refused": (False, 400, "negotiation would drop a required security feature"),
    # request / manifest
    "request.invalid": (False, 400, "request envelope failed its schema"),
    "manifest.parse": (False, 400, "manifest is not valid JSON"),
    "manifest.too_large": (False, 413, "manifest exceeds the byte ceiling"),
    "manifest.too_deep": (False, 400, "manifest nesting exceeds the depth ceiling"),
    "manifest.duplicate_key": (False, 400, "manifest has a duplicate object key"),
    "manifest.invalid": (False, 422, "manifest failed semantic validation (see issues)"),
    "secret.inline": (False, 422, "inline secret material is prohibited; use a secretref"),
    # configuration / activation (MC-12/13)
    "overlay.invalid": (False, 422, "overlay failed its schema"),
    "overlay.scope": (False, 403, "overlay scope does not match target"),
    "overlay.immutable": (False, 403, "overlay attempts to change an immutable field"),
    "overlay.conflict": (False, 409, "two overlays set the same field at the same precedence"),
    "overlay.stale_parent": (False, 409, "overlay parent revision is not the current base"),
    "activation.conflict": (True, 409, "revision precondition failed (concurrent writer)"),
    "activation.quarantined": (False, 409, "candidate revision is quarantined"),
    "activation.no_known_good": (False, 409, "no known-good revision to roll back to"),
    "activation.state": (False, 409, "illegal lifecycle transition"),
    # supply chain (MC-15)
    "artifact.digest": (False, 422, "artifact digest mismatch"),
    "artifact.signature": (False, 422, "artifact signature missing or not from a trusted signer"),
    "artifact.version": (False, 422, "artifact version not approved or below floor"),
    "artifact.revoked": (False, 422, "artifact or signer revoked"),
    "artifact.provenance": (False, 422, "provenance subject/builder mismatch"),
    # crypto (MC-17)
    "crypto.unavailable": (True, 503, "encryption backend or key unavailable; refusing plaintext"),
    "crypto.key_retired": (False, 422, "object encrypted under a retired key outside its window"),
    # operations
    "service.disabled": (True, 503, "INV-64 is emergency-disabled by an operator"),
    # internal
    "internal": (True, 500, "unexpected internal error (defect)"),
}


class Inv64Error(Exception):
    """Base class; ``code`` must be a CATALOG key."""

    def __init__(self, code: str, *, details: Mapping[str, Any] | None = None,
                 correlation_id: str | None = None):
        if code not in CATALOG:
            code = "internal"
        self.code = code
        self.details = dict(list((details or {}).items())[:MAX_DETAILS])
        self.correlation_id = correlation_id
        super().__init__(f"{code}: {CATALOG[code][2]}")

    @property
    def retryable(self) -> bool:
        return CATALOG[self.code][0]

    def envelope(self, correlation_id: str | None = None) -> dict:
        return error_envelope(self.code, correlation_id or self.correlation_id, self.details)


def error_envelope(code: str, correlation_id: str | None, details: Mapping[str, Any] | None = None) -> dict:
    if code not in CATALOG:
        code = "internal"
    retryable, status, message = CATALOG[code]
    return {
        "version": ERROR_ENVELOPE_VERSION,
        "code": code,
        "status": status,
        "message": message,
        "retryable": retryable,
        "correlation_id": correlation_id,
        "details": dict(list((details or {}).items())[:MAX_DETAILS]),
    }


class Outcome:
    """Formal outcome classes (SPECIFICATION.md §4, REQ-OUT-*)."""

    SUCCESS = "success"
    PARTIAL = "partial_success"
    DEGRADED = "degraded"
    RETRYABLE = "retryable_failure"
    TERMINAL = "terminal_failure"
    REJECTED = "rejected_before_activation"
    ALL = ("success", "partial_success", "degraded", "retryable_failure",
           "terminal_failure", "rejected_before_activation")


def outcome_for(code: str | None) -> str:
    if code is None:
        return Outcome.SUCCESS
    retryable, status, _ = CATALOG.get(code, CATALOG["internal"])
    if retryable:
        return Outcome.RETRYABLE
    if status in (400, 401, 403, 409, 413, 422, 499):
        return Outcome.REJECTED
    return Outcome.TERMINAL
