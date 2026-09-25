"""Stable, machine-readable error model (MC-016).

Every denial or failure is an :class:`Error` carrying a stable ``code`` from
:data:`CATALOG`.  Codes are append-only: a code is never renamed or reused with
a different meaning (see ``docs/COMPATIBILITY.md``).  Free-text ``message``
values are informative only; clients must branch on ``code`` and ``retryable``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

ERROR_SCHEMA = "PK_ECP_ERROR/1"

# code -> (category, http_status, retryable, remediation)
CATALOG: dict[str, tuple[str, int, bool, str]] = {
    "AUTHN_MISSING": ("authentication", 401, False, "Present a bearer token issued by a trusted issuer."),
    "AUTHN_INVALID": ("authentication", 401, False, "Token signature, issuer, audience or lifetime invalid; re-authenticate."),
    "AUTHN_REPLAY": ("authentication", 401, False, "Token id (jti) already used; obtain a fresh token."),
    "AUTHZ_DENIED": ("authorization", 403, False, "Request the required capability on the target tenant/lattice."),
    "AUTHZ_EXPLICIT_DENY": ("authorization", 403, False, "An explicit deny binding applies; contact the tenant admin."),
    "SCHEMA_INVALID": ("validation", 400, False, "Fix the request so it validates against the published schema."),
    "PROTOCOL_UNSUPPORTED": ("validation", 400, False, "Use a protocol version listed in docs/COMPATIBILITY.md."),
    "MANIFEST_TOO_LARGE": ("validation", 413, False, "Reduce manifest size below the configured limit."),
    "MANIFEST_EMPTY": ("validation", 400, False, "Include at least one component."),
    "MANIFEST_TOO_MANY_COMPONENTS": ("validation", 400, False, "Split the manifest or request a higher limit."),
    "COMPONENT_DUPLICATE": ("validation", 400, False, "Component names must be unique."),
    "IMAGE_MALFORMED": ("validation", 400, False, "Use registry/repo@sha256:<64 hex> image references."),
    "IMAGE_NOT_PINNED": ("provenance", 400, False, "Pin the image by immutable sha256 digest."),
    "REGISTRY_NOT_APPROVED": ("policy", 403, False, "Use an approved registry or request policy change."),
    "SIGNER_NOT_APPROVED": ("provenance", 403, False, "Sign with an approved signer key."),
    "SIGNATURE_INVALID": ("provenance", 403, False, "Signature does not verify over the artifact digest."),
    "ATTESTATION_MISSING": ("provenance", 403, False, "Attach the required provenance/SBOM attestation."),
    "POLICY_DENIED": ("policy", 403, False, "Organisation policy rejected the request; see details.rule."),
    "POLICY_UNAVAILABLE": ("dependency", 503, True, "Policy engine unreachable; admission fails closed. Retry later."),
    "QUOTA_EXCEEDED": ("capacity", 429, True, "Tenant/lattice quota exhausted; retry after the window resets."),
    "OVERLOADED": ("capacity", 503, True, "Control plane shedding load; retry with backoff."),
    "DEADLINE_EXCEEDED": ("capacity", 504, True, "Request deadline elapsed; retry with a longer deadline."),
    "FROZEN": ("administrative", 423, False, "Scope is frozen/quarantined by an operator; see freeze record."),
    "IDEMPOTENCY_CONFLICT": ("validation", 409, False, "Idempotency key reused with a different request body."),
    "NOT_LEADER": ("availability", 503, True, "Write sent to a follower or fenced instance; retry against the leader."),
    "STORE_UNAVAILABLE": ("dependency", 503, True, "Durable store unavailable; admission fails closed."),
    "DEPLOY_FAILED": ("dependency", 502, True, "Deployment manager did not acknowledge; delivery will be retried from the outbox."),
    "CONFIG_INVALID": ("configuration", 400, False, "Fix the configuration document; see details."),
    "ILLEGAL_TRANSITION": ("lifecycle", 409, False, "Requested lifecycle transition is not permitted from the current state."),
    "STALE_REVISION": ("validation", 409, False, "Your precondition does not match the active revision; re-read and retry."),
    "PRIVILEGE_ESCALATION": ("authorization", 403, False, "You may only grant roles whose capabilities you hold on that scope."),
    "NOT_FOUND": ("validation", 404, False, "Referenced object does not exist."),
    "INTERNAL": ("internal", 500, False, "Unexpected failure; admission failed closed. Escalate per runbook."),
}


@dataclass(frozen=True)
class Error:
    code: str
    message: str = ""
    target: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.code not in CATALOG:
            raise ValueError(f"unregistered error code {self.code!r}")

    @property
    def category(self) -> str:
        return CATALOG[self.code][0]

    @property
    def http_status(self) -> int:
        return CATALOG[self.code][1]

    @property
    def retryable(self) -> bool:
        return CATALOG[self.code][2]

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
            "message": self.message,
            "target": self.target,
            "retryable": self.retryable,
            "remediation": CATALOG[self.code][3],
            "details": dict(self.details),
        }


class ControlPlaneError(Exception):
    """Raised for request-level failures that abort processing."""

    def __init__(self, error: Error):
        super().__init__(f"{error.code}: {error.message}")
        self.error = error


def fail(code: str, message: str = "", target: str | None = None, **details: Any) -> ControlPlaneError:
    return ControlPlaneError(Error(code, message, target, details))
