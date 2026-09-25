"""Versioned structured error registry for INV-66 (MC-016, C026).

Every public failure is an :class:`EcpError` carrying a stable code from
``REGISTRY``.  A code is never reused for a different meaning; the registry
digest is pinned in ``schemas/ERROR_REGISTRY.pin`` and checked by the contract
suite.  Unknown future codes must be handled by ``category``/``retryable``; an
unknown category is terminal and non-retryable.

Details pass through an allowlist so secrets, tokens and raw exception text
never reach an error envelope or a log line.

Pattern donor: sibling shop car ``inv45_sfi_mechanisms`` v4.3.0
``production/errors.py`` (same owner, no licence selected; adapted, not copied).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any

ERROR_SCHEMA = "PK_ECP_ERROR/1"
REGISTRY_VERSION = "1.0.0"


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    wire: int
    category: str  # input|policy|security|auth|resource|dependency|internal|compatibility
    severity: str  # low|medium|high|critical
    retryable: bool
    http: int
    guidance: str


_SPECS = [
    ErrorSpec("ECP_SCHEMA_INVALID", 1001, "input", "medium", False, 400, "Request does not match its versioned schema; fix the producer."),
    ErrorSpec("ECP_MANIFEST_INVALID", 1002, "input", "medium", False, 422, "Manifest is structurally invalid (components, names, image references)."),
    ErrorSpec("ECP_RESOURCE_LIMIT", 1003, "resource", "medium", False, 413, "Input exceeds a configured size/count limit; do not retry unchanged."),
    ErrorSpec("ECP_UNSUPPORTED_VERSION", 1004, "compatibility", "medium", False, 409, "Protocol/schema version not in the supported matrix; negotiate a supported version."),
    ErrorSpec("ECP_UNAUTHENTICATED", 2001, "auth", "high", False, 401, "Caller credential missing, malformed, expired, wrong issuer/audience or replayed."),
    ErrorSpec("ECP_FORBIDDEN", 2002, "auth", "high", False, 403, "Authenticated principal lacks the capability for this scope."),
    ErrorSpec("ECP_DUAL_AUTH_REQUIRED", 2003, "auth", "high", False, 403, "High-impact change needs a second distinct approver."),
    ErrorSpec("ECP_REGISTRY_NOT_APPROVED", 3001, "policy", "high", False, 403, "Image registry is not on the active approved list."),
    ErrorSpec("ECP_SIGNER_NOT_APPROVED", 3002, "policy", "high", False, 403, "Signer identity is not approved for this scope."),
    ErrorSpec("ECP_SIGNATURE_INVALID", 3003, "security", "critical", False, 403, "Artifact signature missing, malformed, from an unknown/revoked key, or not over this digest."),
    ErrorSpec("ECP_DIGEST_REQUIRED", 3004, "security", "high", False, 422, "Image must be pinned by an immutable sha256 digest."),
    ErrorSpec("ECP_PROVENANCE_INVALID", 3005, "security", "high", False, 403, "Provenance attestation missing, unverifiable, or does not match policy."),
    ErrorSpec("ECP_POLICY_DENIED", 3006, "policy", "high", False, 403, "Organisation policy denied the request."),
    ErrorSpec("ECP_QUARANTINED", 3007, "policy", "high", False, 423, "Target tenant/lattice/global scope is frozen or quarantined."),
    ErrorSpec("ECP_REPLAY_DETECTED", 3008, "security", "high", False, 409, "Token nonce or request reused with different content."),
    ErrorSpec("ECP_QUOTA_EXCEEDED", 4001, "resource", "medium", True, 429, "Tenant/lattice quota exhausted; retry after retry_after_ms."),
    ErrorSpec("ECP_OVERLOADED", 4002, "resource", "medium", True, 503, "Load shed; retry with exponential backoff and jitter."),
    ErrorSpec("ECP_DEADLINE_EXCEEDED", 4003, "resource", "medium", True, 504, "Deadline elapsed; no admission was recorded."),
    ErrorSpec("ECP_CANCELLED", 4004, "resource", "low", True, 499, "Caller cancelled; no admission was recorded."),
    ErrorSpec("ECP_DEPENDENCY_UNAVAILABLE", 5001, "dependency", "high", True, 503, "A required dependency is unhealthy; admission fails closed."),
    ErrorSpec("ECP_CIRCUIT_OPEN", 5002, "dependency", "high", True, 503, "Circuit breaker open for the dependency; retry after cool-down."),
    ErrorSpec("ECP_NOT_LEADER", 5003, "dependency", "medium", True, 421, "This replica is not the leader or its lease/epoch is stale; redirect."),
    ErrorSpec("ECP_DELIVERY_FAILED", 5004, "dependency", "high", True, 502, "Deployment manager did not acknowledge; manifest remains admitted-pending."),
    ErrorSpec("ECP_CONFIG_INVALID", 6001, "input", "high", False, 400, "Configuration failed validation; previous generation stays active."),
    ErrorSpec("ECP_CONFIG_CONFLICT", 6002, "input", "medium", True, 409, "Generation changed concurrently (CAS failed); re-read and retry."),
    ErrorSpec("ECP_ILLEGAL_TRANSITION", 6003, "internal", "high", False, 409, "Lifecycle transition not permitted by the state machine."),
    ErrorSpec("ECP_IDEMPOTENCY_CONFLICT", 6004, "input", "medium", False, 409, "Idempotency key reused with a different request body."),
    ErrorSpec("ECP_NOT_FOUND", 6005, "input", "low", False, 404, "Requested object does not exist."),
    ErrorSpec("ECP_AUDIT_TAMPERED", 7001, "security", "critical", False, 500, "Audit chain or anchor verification failed; preserve evidence and page security."),
    ErrorSpec("ECP_AUDIT_UNAVAILABLE", 7002, "dependency", "critical", True, 503, "Audit append failed; nothing is admitted without an audit record."),
    ErrorSpec("ECP_STORE_CORRUPT", 7003, "internal", "critical", False, 500, "Durable store failed integrity check; restore from backup."),
    ErrorSpec("ECP_INTERNAL", 9001, "internal", "critical", False, 500, "Internal invariant failed; fail closed and file a defect."),
]

REGISTRY: dict[str, ErrorSpec] = {s.code: s for s in _SPECS}

SAFE_DETAIL_KEYS = frozenset({
    "component", "field", "limit", "observed", "registry", "signer", "tenant", "lattice", "org",
    "capability", "scope", "key_id", "digest", "expected_version", "observed_version", "dependency",
    "retry_after_ms", "generation", "from_state", "to_state", "state", "rule", "reason", "index",
    "epoch", "leader", "count", "request_id",
})


def registry_digest() -> str:
    rows = [asdict(s) for s in sorted(_SPECS, key=lambda s: s.code)]
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class EcpError(Exception):
    """Operator-safe structured error. ``str(err)`` never contains secrets."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        if code not in REGISTRY:
            code, message, details = "ECP_INTERNAL", f"unregistered error code {code!r}", {}
        super().__init__(message)
        self.code = code
        self.spec = REGISTRY[code]
        self.message = message
        self.details = {k: v for k, v in details.items() if k in SAFE_DETAIL_KEYS and _safe(v)}

    def envelope(self, request_id: str | None = None) -> dict[str, Any]:
        s = self.spec
        env = {"schema": ERROR_SCHEMA, "code": s.code, "wire": s.wire, "category": s.category,
               "severity": s.severity, "retryable": s.retryable, "http": s.http,
               "message": self.message, "guidance": s.guidance, "details": dict(self.details)}
        if request_id:
            env["request_id"] = request_id
        return env


def _safe(v: Any) -> bool:
    if isinstance(v, (bool, int, float)) or v is None:
        return True
    if isinstance(v, str):
        return len(v) <= 512
    if isinstance(v, (list, tuple)):
        return len(v) <= 64 and all(_safe(x) for x in v)
    return False


def reason(code: str, message: str, **details: Any) -> dict[str, Any]:
    """A denial reason as data (admission collects many; errors raise one)."""
    e = EcpError(code, message, **details)
    return {"code": e.code, "message": e.message, "details": e.details}
