"""Versioned structured error registry for the INV-45 production layer (C026).

Every public failure raises :class:`SfiError` (or a subclass) carrying a code from
``REGISTRY``.  Codes are stable: a code is never reused for a different meaning
(``tests/contract/test_errors.py`` pins the registry digest and checks uniqueness).
Consumers MUST treat an unknown future code by its ``category`` and ``retryable``
fields, and MUST treat an unknown category as a terminal, non-retryable failure.

Details are filtered through an allowlist: executable bytes, secrets, tokens and
raw exception text never reach an error envelope.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_SCHEMA = "PK_SFI_ERROR/1"
REGISTRY_VERSION = "1.0.0"


@dataclass(frozen=True)
class ErrorSpec:
    code: str
    wire: int
    category: str  # input | policy | security | auth | resource | dependency | internal | compatibility
    severity: str  # low | medium | high | critical
    retryable: bool
    http: int
    guidance: str


_SPECS = [
    ErrorSpec("SFI_SCHEMA_INVALID", 1001, "input", "medium", False, 400, "Request/config does not match its versioned schema; fix the producer."),
    ErrorSpec("SFI_MALFORMED_ARTIFACT", 1002, "input", "high", False, 422, "Binary is not a well-formed Wasm module; reject the artifact, do not retry."),
    ErrorSpec("SFI_INVALID_MODULE", 1003, "input", "high", False, 422, "Module fails Wasm type validation; reject the artifact."),
    ErrorSpec("SFI_UNSUPPORTED_FEATURE", 1004, "compatibility", "medium", False, 422, "Module uses a Wasm feature outside the pinned profile (ADR-0001)."),
    ErrorSpec("SFI_UNSUPPORTED_VERSION", 1005, "compatibility", "medium", False, 409, "Schema/profile/binary version not in the supported set; upgrade the peer or use a supported version."),
    ErrorSpec("SFI_UNMASKED_ACCESS", 2001, "security", "critical", False, 422, "A memory access is not confined by the canonical mask sequence; the artifact must be (re)written by the trusted rewriter."),
    ErrorSpec("SFI_BRANCH_OUTSIDE_TARGETS", 2002, "security", "critical", False, 403, "Indirect control transfer outside the permitted target set."),
    ErrorSpec("SFI_NOT_VERIFIED", 2003, "security", "critical", False, 403, "Execution attempted without a current verification seal."),
    ErrorSpec("SFI_SEAL_MISMATCH", 2004, "security", "critical", False, 403, "Sealed descriptor does not match the artifact, profile, config or tenant presented at load time."),
    ErrorSpec("SFI_DIGEST_MISMATCH", 2005, "security", "critical", False, 403, "Artifact bytes changed between verification and load (possible TOCTOU)."),
    ErrorSpec("SFI_SIGNATURE_INVALID", 2006, "security", "critical", False, 403, "Signature missing, malformed, from an untrusted/revoked key, or expired."),
    ErrorSpec("SFI_ROLLBACK_REJECTED", 2007, "security", "high", False, 409, "Artifact/policy version is older than the anti-rollback floor."),
    ErrorSpec("SFI_POLICY_REJECTED", 2008, "policy", "high", False, 403, "Artifact is valid but disallowed by policy (imports, memory layout, tables, grow)."),
    ErrorSpec("SFI_QUARANTINED", 2009, "policy", "high", False, 423, "Target (artifact, tenant or global) is quarantined/frozen/disabled by an operator."),
    ErrorSpec("SFI_REPLAY_DETECTED", 2010, "security", "high", False, 403, "Authorization token or descriptor nonce was already used."),
    ErrorSpec("SFI_UNAUTHENTICATED", 3001, "auth", "high", False, 401, "Caller identity missing, forged or expired."),
    ErrorSpec("SFI_UNAUTHORIZED", 3002, "auth", "high", False, 403, "Authenticated caller lacks the explicit capability for this operation/tenant/digest."),
    ErrorSpec("SFI_DUAL_AUTH_REQUIRED", 3003, "auth", "high", False, 403, "High-impact action needs a second, distinct authorized principal."),
    ErrorSpec("SFI_RESOURCE_LIMIT", 4001, "resource", "medium", False, 413, "Input exceeds a configured size/count/work limit; deterministic, do not retry unchanged."),
    ErrorSpec("SFI_OVERLOADED", 4002, "resource", "medium", True, 503, "Admission control shed the request; retry with backoff+jitter."),
    ErrorSpec("SFI_DEADLINE_EXCEEDED", 4003, "resource", "medium", True, 504, "Operation exceeded its deadline and was cancelled with no partial trust state."),
    ErrorSpec("SFI_CANCELLED", 4004, "resource", "low", True, 499, "Operation cancelled by caller; no partial trust state was created."),
    ErrorSpec("SFI_DEPENDENCY_UNAVAILABLE", 5001, "dependency", "high", True, 503, "A required dependency (engine, key service, config store) is unavailable; fail closed, retry later."),
    ErrorSpec("SFI_TRUST_STALE", 5002, "dependency", "high", True, 503, "Trust material (keys/revocations/config) exceeded its freshness window; refresh before trusting."),
    ErrorSpec("SFI_CONFIG_INVALID", 6001, "input", "high", False, 400, "Configuration failed validation; the previous active generation stays in force."),
    ErrorSpec("SFI_CONFIG_CONFLICT", 6002, "input", "medium", True, 409, "Configuration generation changed concurrently (compare-and-swap failed); re-read and retry."),
    ErrorSpec("SFI_ILLEGAL_TRANSITION", 6003, "internal", "high", False, 409, "Lifecycle transition not allowed by the state machine."),
    ErrorSpec("SFI_AUDIT_TAMPERED", 7001, "security", "critical", False, 500, "Audit chain verification failed; preserve evidence, page security owner."),
    ErrorSpec("SFI_INTERNAL_INVARIANT", 9001, "internal", "critical", False, 500, "Internal invariant failed; treated as terminal and fail-closed. File a defect."),
]

REGISTRY: dict[str, ErrorSpec] = {s.code: s for s in _SPECS}

#: Only these detail keys may appear in an error envelope (C026 / C075).
SAFE_DETAIL_KEYS = frozenset({
    "module", "function_index", "instruction_offset", "opcode", "section", "limit", "observed",
    "feature", "expected_version", "observed_version", "tenant", "workload", "capability",
    "operation", "artifact_sha256", "expected_sha256", "key_id", "state", "target",
    "from_state", "to_state", "field", "reason", "unmasked_count", "sample_offsets",
    "generation", "import", "floor", "retry_after_ms", "dependency", "scope", "count",
})


class SfiError(Exception):
    """Base production error.  ``str(err)`` is operator-safe; details are allowlisted."""

    def __init__(self, code: str, message: str, **details: Any) -> None:
        if code not in REGISTRY:  # internal defect: never invent codes at runtime
            details = {"reason": f"unregistered code {code!r}"}
            code = "SFI_INTERNAL_INVARIANT"
        super().__init__(message)
        self.code = code
        self.spec = REGISTRY[code]
        self.details = {k: _safe(v) for k, v in details.items() if k in SAFE_DETAIL_KEYS}

    @property
    def retryable(self) -> bool:
        return self.spec.retryable

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": ERROR_SCHEMA,
            "code": self.code,
            "wire": self.spec.wire,
            "category": self.spec.category,
            "severity": self.spec.severity,
            "retryable": self.spec.retryable,
            "message": str(self),
            "details": dict(self.details),
        }


def _safe(value: Any) -> Any:
    if isinstance(value, (bytes, bytearray, memoryview)):
        return f"<{len(value)} bytes redacted>"
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in list(value)[:8]]
    if isinstance(value, (bool, int, float)) or value is None:
        return value
    text = str(value)
    return text if len(text) <= 256 else text[:253] + "..."


def fail(code: str, message: str, **details: Any) -> SfiError:
    return SfiError(code, message, **details)


def registry_markdown() -> str:
    """Generate docs/security/ERROR_CATALOG.md from the registry (drift-proof)."""
    lines = [
        "# INV-45 error catalog",
        "",
        f"Generated from `production/errors.py` registry version {REGISTRY_VERSION}; do not edit by hand.",
        "",
        "| Code | Wire | Category | Severity | Retryable | HTTP | Operator guidance |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in _SPECS:
        lines.append(f"| `{s.code}` | {s.wire} | {s.category} | {s.severity} | {'yes' if s.retryable else 'no'} | {s.http} | {s.guidance} |")
    lines += [
        "",
        "Unknown future codes: consumers use `category`/`retryable`; an unknown category is terminal.",
        "Security and policy rejections are never retryable (deterministic verifier rejection is never retried).",
        "",
    ]
    return "\n".join(lines)
