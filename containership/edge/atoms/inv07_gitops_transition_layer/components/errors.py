"""INV-07 machine-readable error model (component 14).

Every error carries a *stable* code (``PKG-<CATEGORY>-<NNN>``), a category, a
retryability class, a severity, safe details and an optional correlation id.
The meaning of a code never changes across versions; codes are only ever
added, and a retired code stays reserved (see ``RESERVED``).  ``envelope()``
renders the ``PK_GITOPS_ERROR/1`` wire form validated by
``schemas/PK_GITOPS_ERROR_1.schema.json``.

Details are passed through ``redact.scrub`` so a caller that hands a token,
key, password or credential-bearing URL to an exception never leaks it into a
log line, trace attribute, API response or evidence file.
"""
from __future__ import annotations

from typing import Any

from .redact import scrub

TERMINAL = "terminal"          # retrying cannot help: fix input/trust/policy
RETRYABLE = "retryable"        # transient: bounded retry with backoff is safe
OPERATOR = "operator"          # needs a human action (unfreeze, rotate key, restore)

ERROR_SCHEMA = "PK_GITOPS_ERROR/1"


class GitOpsError(Exception):
    code = "PKG-INTERNAL-001"
    category = "internal"
    retry = TERMINAL
    severity = "error"

    def __init__(self, message: str, *, correlation_id: str | None = None, cause: str | None = None,
                 **details: Any) -> None:
        super().__init__(message)
        self.message = str(scrub(message))
        self.details = scrub(details)
        self.correlation_id = correlation_id
        self.cause = cause

    def envelope(self) -> dict:
        return {"schema": ERROR_SCHEMA, "code": self.code, "category": self.category, "retry": self.retry,
                "severity": self.severity, "message": self.message, "details": self.details,
                "correlation_id": self.correlation_id, "cause": self.cause}


def _e(name: str, code: str, category: str, retry: str, severity: str, *bases) -> type:
    return type(name, (GitOpsError, *bases), {"code": code, "category": category, "retry": retry,
                                              "severity": severity, "__doc__": f"{code} ({category}, {retry})"})


Malformed = _e("Malformed", "PKG-INPUT-001", "input", TERMINAL, "error", ValueError)
LimitExceeded = _e("LimitExceeded", "PKG-INPUT-002", "input", TERMINAL, "error", ValueError)
Unauthenticated = _e("Unauthenticated", "PKG-AUTH-001", "auth", TERMINAL, "warning", PermissionError)
Unauthorized = _e("Unauthorized", "PKG-AUTH-002", "auth", TERMINAL, "warning", PermissionError)
Unsigned = _e("Unsigned", "PKG-TRUST-001", "trust", TERMINAL, "critical", PermissionError)
Untrusted = _e("Untrusted", "PKG-TRUST-002", "trust", TERMINAL, "critical", PermissionError)
Revoked = _e("Revoked", "PKG-TRUST-003", "trust", TERMINAL, "critical", PermissionError)
Expired = _e("Expired", "PKG-TRUST-004", "trust", TERMINAL, "error", PermissionError)
ProvenanceFailed = _e("ProvenanceFailed", "PKG-TRUST-005", "trust", TERMINAL, "critical", PermissionError)
RefNotApproved = _e("RefNotApproved", "PKG-REF-001", "ref_policy", TERMINAL, "critical", PermissionError)
NonFastForward = _e("NonFastForward", "PKG-REF-002", "ref_policy", TERMINAL, "critical", PermissionError)
StaleRef = _e("StaleRef", "PKG-REF-003", "freshness", TERMINAL, "critical", PermissionError)
RepositoryIdentity = _e("RepositoryIdentity", "PKG-REPO-001", "repository", TERMINAL, "critical", PermissionError)
RepositoryUnavailable = _e("RepositoryUnavailable", "PKG-REPO-002", "repository", RETRYABLE, "error", RuntimeError)
PolicyDenied = _e("PolicyDenied", "PKG-POLICY-001", "policy", TERMINAL, "warning", PermissionError)
PolicyUnavailable = _e("PolicyUnavailable", "PKG-POLICY-002", "policy", RETRYABLE, "error", RuntimeError)
Quarantined = _e("Quarantined", "PKG-OPS-001", "operations", OPERATOR, "warning", PermissionError)
NotLeader = _e("NotLeader", "PKG-OPS-002", "operations", RETRYABLE, "info", RuntimeError)
FencedOff = _e("FencedOff", "PKG-OPS-003", "operations", TERMINAL, "critical", RuntimeError)
Throttled = _e("Throttled", "PKG-OPS-004", "operations", RETRYABLE, "warning", RuntimeError)
CircuitOpen = _e("CircuitOpen", "PKG-OPS-005", "operations", RETRYABLE, "warning", RuntimeError)
DeadlineExceeded = _e("DeadlineExceeded", "PKG-OPS-006", "operations", RETRYABLE, "warning", TimeoutError)
Cancelled = _e("Cancelled", "PKG-OPS-007", "operations", TERMINAL, "info", RuntimeError)
ApplyFailed = _e("ApplyFailed", "PKG-APPLY-001", "apply", RETRYABLE, "error", RuntimeError)
PartialApply = _e("PartialApply", "PKG-APPLY-002", "apply", OPERATOR, "critical", RuntimeError)
Conflict = _e("Conflict", "PKG-APPLY-003", "apply", RETRYABLE, "warning", RuntimeError)
TargetUnavailable = _e("TargetUnavailable", "PKG-APPLY-004", "apply", RETRYABLE, "error", RuntimeError)
TenantViolation = _e("TenantViolation", "PKG-TENANT-001", "tenancy", TERMINAL, "critical", PermissionError)
ResidencyViolation = _e("ResidencyViolation", "PKG-TENANT-002", "tenancy", TERMINAL, "critical", PermissionError)
Corrupted = _e("Corrupted", "PKG-STATE-001", "state", OPERATOR, "critical", RuntimeError)
StateVersion = _e("StateVersion", "PKG-STATE-002", "state", OPERATOR, "error", RuntimeError)
ConfigRejected = _e("ConfigRejected", "PKG-CONFIG-001", "config", TERMINAL, "error", ValueError)
TimeUntrusted = _e("TimeUntrusted", "PKG-TIME-001", "time", RETRYABLE, "error", RuntimeError)
SecretUnavailable = _e("SecretUnavailable", "PKG-SECRET-001", "secrets", RETRYABLE, "error", RuntimeError)
NetworkPolicy = _e("NetworkPolicy", "PKG-NET-001", "network", TERMINAL, "critical", PermissionError)
NothingToSync = _e("NothingToSync", "PKG-SYNC-001", "sync", TERMINAL, "info", LookupError)
InternalError = GitOpsError

ALL = (Malformed, LimitExceeded, Unauthenticated, Unauthorized, Unsigned, Untrusted, Revoked, Expired,
       ProvenanceFailed, RefNotApproved, NonFastForward, StaleRef, RepositoryIdentity, RepositoryUnavailable,
       PolicyDenied, PolicyUnavailable, Quarantined, NotLeader, FencedOff, Throttled, CircuitOpen,
       DeadlineExceeded, Cancelled, ApplyFailed, PartialApply, Conflict, TargetUnavailable, TenantViolation,
       ResidencyViolation, Corrupted, StateVersion, ConfigRejected, TimeUntrusted, SecretUnavailable,
       NetworkPolicy, NothingToSync, GitOpsError)

# Frozen registry: code -> (name, category, retry).  tests/test_contracts.py
# pins it so a code can never silently change meaning between releases.
REGISTRY = {c.code: (c.__name__, c.category, c.retry) for c in ALL}
RESERVED: tuple[str, ...] = ()  # retired codes stay here forever


def from_exception(exc: BaseException, correlation_id: str | None = None) -> dict:
    """Map any exception to a safe envelope; unknown exceptions never leak text."""
    if isinstance(exc, GitOpsError):
        env = exc.envelope()
        if correlation_id and not env["correlation_id"]:
            env["correlation_id"] = correlation_id
        return env
    return InternalError("internal error", correlation_id=correlation_id, cause=type(exc).__name__).envelope()
