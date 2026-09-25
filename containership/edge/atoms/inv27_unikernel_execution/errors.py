"""Structured failure model for INV-27 (MC-027; C014, C026).

Every refusal or error crossing PK_UNIKERNEL_IMAGE/1 or PK_UNIKERNEL_INSTANCE/1 carries a
stable code from ``REGISTRY``.  Codes are append-only (ops/COMPATIBILITY_POLICY.md): never
renamed or re-purposed, only deprecated.

Outcome classes:
  refused    - the image or request is not acceptable; retrying unchanged is useless
  terminal   - malformed input / policy violation / integrity failure; never retry unchanged
  retryable  - transient (deadline, overload, dependency); retry with backoff if idempotent
  degraded   - answered from a fallback path; correct but flagged
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

SCHEMA = "PK_UNIKERNEL_ERROR/1"
OUTCOMES = ("success", "refused", "retryable", "degraded", "terminal")


@dataclass(frozen=True)
class Code:
    code: str
    outcome: str
    http_like: int
    summary: str


_CODES = [
    # --- parser (MC-001) ---
    Code("UK_PARSE_TOO_LARGE", "terminal", 413, "image exceeds the admission byte budget"),
    Code("UK_PARSE_BAD_MAGIC", "terminal", 400, "not an ELF image"),
    Code("UK_PARSE_UNSUPPORTED_FORMAT", "terminal", 400, "ELF class/endianness/version/machine not supported"),
    Code("UK_PARSE_TRUNCATED", "terminal", 400, "a structure extends past the end of the image"),
    Code("UK_PARSE_MALFORMED", "terminal", 400, "a structure is internally inconsistent"),
    Code("UK_PARSE_OVERLAP", "terminal", 400, "sections or segments overlap illegally"),
    Code("UK_PARSE_LIMIT", "terminal", 413, "a structure count exceeds the parser budget"),
    Code("UK_PARSE_BUDGET", "terminal", 413, "parser CPU/work budget exhausted"),
    # --- seal facts (MC-002/003) ---
    Code("UK_SEAL_NOT_SAS", "refused", 409, "single-address-space could not be positively proven"),
    Code("UK_SEAL_DYNAMIC", "refused", 409, "image is dynamically linked or carries a program interpreter"),
    Code("UK_SEAL_MULTIPROCESS", "refused", 409, "image links process-creation or exec capability"),
    Code("UK_SEAL_DYNLOAD", "refused", 409, "image links a runtime code loader"),
    Code("UK_SEAL_DEBUG_SURFACE", "refused", 409, "image links a shell/debugger/ptrace surface"),
    Code("UK_SEAL_WX", "refused", 409, "image has a writable+executable segment"),
    Code("UK_SEAL_UNKNOWN_TOOLCHAIN", "refused", 409, "no verifier profile for the image's toolchain"),
    Code("UK_SEAL_NO_EVIDENCE", "refused", 409, "binary carries no evidence the verifier can use (stripped?)"),
    Code("UK_SEAL_DRIFT", "refused", 409, "manifest syscall set differs from the binary-derived set"),
    Code("UK_SEAL_SYSCALL_FORBIDDEN", "refused", 403, "binary-derived syscall outside the environment's permitted set"),
    Code("UK_SEAL_ARCH", "refused", 409, "image architecture not supported at this site"),
    # --- identity/trust (MC-004/005/024/025) ---
    Code("UK_DIGEST_MISMATCH", "terminal", 409, "image bytes do not match the bound digest"),
    Code("UK_SIG_MISSING", "refused", 401, "no signature envelope supplied"),
    Code("UK_SIG_INVALID", "terminal", 401, "signature does not verify"),
    Code("UK_SIG_UNTRUSTED_KEY", "refused", 401, "signing key not in the trust root, revoked or expired"),
    Code("UK_PROVENANCE_INVALID", "refused", 409, "provenance statement malformed or does not bind the image"),
    Code("UK_PROVENANCE_POLICY", "refused", 403, "builder/toolchain/source not approved by policy"),
    Code("UK_TRUST_UNAVAILABLE", "retryable", 503, "trust root unavailable or stale; admission fails closed"),
    Code("UK_UNAUTHENTICATED", "terminal", 401, "caller identity not established"),
    Code("UK_FORBIDDEN", "terminal", 403, "caller lacks the capability or tenant scope"),
    Code("UK_REPLAY", "terminal", 409, "request token already used"),
    # --- manifest/config (MC-006/029) ---
    Code("UK_MANIFEST_INVALID", "terminal", 400, "seal manifest failed strict schema validation"),
    Code("UK_UNSUPPORTED_VERSION", "terminal", 400, "schema version not supported"),
    Code("UK_CONFIG_INVALID", "terminal", 400, "configuration failed validation"),
    Code("UK_LIMIT_EXCEEDED", "terminal", 413, "payload exceeds a documented bound"),
    # --- boot/isolation/execution (MC-007..010) ---
    Code("UK_BOOT_CONTRACT", "refused", 409, "entry point / boot contract violated"),
    Code("UK_ISOLATION_POLICY", "refused", 403, "device/network/storage request outside the isolation policy"),
    Code("UK_VMM_UNSUPPORTED", "refused", 409, "no supported VMM backend available or version not approved"),
    Code("UK_VMM_LAUNCH_FAILED", "retryable", 503, "VMM failed to start the guest"),
    Code("UK_VMM_TIMEOUT", "retryable", 504, "guest did not reach ready within the boot deadline"),
    Code("UK_INSTANCE_DUPLICATE", "terminal", 409, "an instance with this idempotency key already exists"),
    Code("UK_UNKNOWN_INSTANCE", "terminal", 404, "no such instance"),
    Code("UK_ILLEGAL_TRANSITION", "terminal", 409, "lifecycle transition not permitted"),
    Code("UK_STALE_FENCE", "terminal", 409, "controller fencing token is stale"),
    Code("UK_QUARANTINED", "refused", 423, "image digest or tenant quarantined by an operator"),
    Code("UK_DISABLED", "terminal", 503, "component emergency-disabled by an operator"),
    Code("UK_QUOTA_EXCEEDED", "refused", 429, "tenant instance quota would be exceeded"),
    Code("UK_STATE_CORRUPT", "terminal", 500, "journal or snapshot failed integrity checks"),
    # --- transient ---
    Code("UK_DEADLINE_EXCEEDED", "retryable", 504, "deadline passed before a decision"),
    Code("UK_CANCELLED", "retryable", 499, "caller cancelled"),
    Code("UK_OVERLOADED", "retryable", 503, "admission control shed the request"),
    Code("UK_CIRCUIT_OPEN", "retryable", 503, "dependency circuit open"),
    Code("UK_DEPENDENCY_UNAVAILABLE", "retryable", 503, "a security-critical dependency is unavailable"),
    # --- legacy aliases kept for resilience.py donor compatibility ---
    Code("UK_INVALID_REQUIREMENT", "terminal", 400, "request malformed or unsafe"),
]

REGISTRY: dict[str, Code] = {c.code: c for c in _CODES}


class UkError(Exception):
    """An error carrying a registered code and machine-readable details."""

    def __init__(self, code: str, message: str = "", **details: Any) -> None:
        if code not in REGISTRY:
            raise KeyError(f"unregistered error code {code!r}")
        self.code = code
        self.message = message or REGISTRY[code].summary
        self.details = details
        super().__init__(f"{code}: {self.message}")

    @property
    def outcome(self) -> str:
        return REGISTRY[self.code].outcome

    @property
    def retryable(self) -> bool:
        return self.outcome == "retryable"

    def to_dict(self) -> dict:
        return {"schema": SCHEMA, "code": self.code, "outcome": self.outcome,
                "retryable": self.retryable, "message": self.message,
                "details": {k: (sorted(v) if isinstance(v, (set, frozenset)) else v) for k, v in self.details.items()}}


def describe(code: str) -> dict:
    c = REGISTRY[code]
    return {"code": c.code, "outcome": c.outcome, "http_like": c.http_like, "summary": c.summary}
