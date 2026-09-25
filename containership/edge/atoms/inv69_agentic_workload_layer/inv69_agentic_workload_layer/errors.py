"""Stable, machine-readable failure taxonomy for INV-69 (C026).

Every public boundary of the governed runtime reports failures as an
``AgentError`` carrying an immutable code from ``REGISTRY``.  Codes are never
reused: a retired code stays in the registry with ``retired=True`` and new
semantics get a new code.  ``translate`` maps any exception to a code without
copying the exception message or traceback (which may carry secrets) into
caller- or audit-visible fields.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping
import secrets

REGISTRY_VERSION = "PK_AGENT_ERRORS/1.0.0"

CATEGORIES = (
    "validation", "authorization", "approval", "policy", "lifecycle", "dependency",
    "sandbox", "timeout", "cancellation", "capacity", "integrity", "configuration",
    "compatibility", "trust", "internal",
)


@dataclass(frozen=True)
class ErrorCode:
    code: str
    category: str
    retryable: bool
    severity: str          # info | warning | error | critical
    rpc_status: str        # gRPC-style canonical status name
    http_status: int
    hint: str
    retired: bool = False


def _c(code, category, retryable, severity, rpc, http, hint):
    return ErrorCode(code, category, retryable, severity, rpc, http, hint)


_CODES = [
    _c("AGT-VAL-001", "validation", False, "warning", "INVALID_ARGUMENT", 400, "Fix the request shape; see schema."),
    _c("AGT-VAL-002", "validation", False, "warning", "INVALID_ARGUMENT", 400, "Input exceeds depth/size/count limits."),
    _c("AGT-AUTHZ-001", "authorization", False, "warning", "PERMISSION_DENIED", 403, "Tool not in agent allowlist."),
    _c("AGT-AUTHZ-002", "authorization", False, "warning", "PERMISSION_DENIED", 403, "Authorization layer (INV-59) denied the principal."),
    _c("AGT-APR-001", "approval", False, "info", "FAILED_PRECONDITION", 409, "Awaiting one-use approval for exact arguments."),
    _c("AGT-APR-002", "approval", False, "warning", "PERMISSION_DENIED", 403, "Approver is not permitted (self/unknown/irrelevant)."),
    _c("AGT-POL-001", "policy", False, "warning", "FAILED_PRECONDITION", 409, "A hard constraint won; see decision trace."),
    _c("AGT-POL-002", "policy", False, "warning", "FAILED_PRECONDITION", 409, "Waiver missing, expired or out of scope."),
    _c("AGT-LCY-001", "lifecycle", False, "warning", "FAILED_PRECONDITION", 409, "Illegal state transition."),
    _c("AGT-LCY-002", "lifecycle", False, "info", "ALREADY_EXISTS", 200, "Duplicate transition request; original result returned."),
    _c("AGT-DEP-001", "dependency", True, "error", "UNAVAILABLE", 503, "A dependency is unavailable; retry after backoff."),
    _c("AGT-DEP-002", "dependency", False, "error", "UNAVAILABLE", 503, "Critical dependency unavailable; failing closed."),
    _c("AGT-SBX-001", "sandbox", True, "error", "UNAVAILABLE", 503, "Sandbox tier unavailable."),
    _c("AGT-SBX-002", "sandbox", False, "critical", "FAILED_PRECONDITION", 409, "Sandbox tier weaker than policy requires."),
    _c("AGT-TMO-001", "timeout", True, "warning", "DEADLINE_EXCEEDED", 504, "Deadline exceeded."),
    _c("AGT-CAN-001", "cancellation", False, "info", "CANCELLED", 499, "Caller cancelled; side effects may be indeterminate if a tool had started."),
    _c("AGT-CAP-001", "capacity", False, "warning", "RESOURCE_EXHAUSTED", 429, "Step budget exhausted."),
    _c("AGT-CAP-002", "capacity", False, "warning", "RESOURCE_EXHAUSTED", 429, "Cost budget exhausted."),
    _c("AGT-CAP-003", "capacity", True, "warning", "RESOURCE_EXHAUSTED", 429, "Admission queue full (backpressure); retry later."),
    _c("AGT-CAP-004", "capacity", False, "critical", "RESOURCE_EXHAUSTED", 507, "Audit stream capacity exhausted; agent sealed."),
    _c("AGT-INT-001", "integrity", False, "critical", "DATA_LOSS", 500, "Transcript/provenance chain verification failed."),
    _c("AGT-INT-002", "integrity", False, "critical", "FAILED_PRECONDITION", 409, "Artifact digest/signature/provenance verification failed."),
    _c("AGT-INT-003", "integrity", False, "critical", "FAILED_PRECONDITION", 409, "Stale fencing token; another executor owns the run."),
    _c("AGT-CFG-001", "configuration", False, "error", "INVALID_ARGUMENT", 400, "Configuration rejected by schema/strict parser."),
    _c("AGT-CFG-002", "configuration", False, "error", "PERMISSION_DENIED", 403, "Overlay attempted to override a locked field."),
    _c("AGT-CFG-003", "configuration", True, "warning", "ABORTED", 409, "Concurrent configuration writer; generation changed."),
    _c("AGT-CMP-001", "compatibility", False, "error", "FAILED_PRECONDITION", 409, "Peer major version or capability unsupported."),
    _c("AGT-TRU-001", "trust", False, "critical", "UNAVAILABLE", 503, "Trust service unavailable or stale beyond freshness bound."),
    _c("AGT-INTERNAL-001", "internal", False, "critical", "INTERNAL", 500, "Internal defect; details withheld. Use correlation id."),
]
REGISTRY: Mapping[str, ErrorCode] = {c.code: c for c in _CODES}

# Mapping of the kernel's (runtime.py) stable reason strings to codes.  The
# PK_AGENT_STEP/1 wire schema is closed (additionalProperties: false) so the
# code is attached to the *returned* result and to the governed runtime's
# PK_AGENT_RUN_EVENT/1 stream rather than to the v1 transcript event.
REASON_CODES = {
    "policy checks passed": None,
    "one-use approval recorded": None,
    "awaiting one-use approval": "AGT-APR-001",
    "step budget exhausted": "AGT-CAP-001",
    "cost budget exhausted": "AGT-CAP-002",
    "audit stream sealed": "AGT-CAP-004",
    "argument exceeds input limits": "AGT-VAL-002",
    "audit stream capacity exhausted": "AGT-CAP-004",
}


def code_for_reason(reason: str) -> str | None:
    if reason in REASON_CODES:
        return REASON_CODES[reason]
    if reason.endswith("not in allowlist"):
        return "AGT-AUTHZ-001"
    return "AGT-INTERNAL-001"


def new_correlation_id() -> str:
    return "corr-" + secrets.token_hex(8)


@dataclass
class AgentError(Exception):
    code: str
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=new_correlation_id)
    cause: "AgentError | None" = None

    def __post_init__(self) -> None:
        if self.code not in REGISTRY:
            raise ValueError(f"unregistered error code {self.code!r}")
        if REGISTRY[self.code].retired:
            raise ValueError(f"retired error code {self.code!r}")
        if not self.message:
            self.message = REGISTRY[self.code].hint
        Exception.__init__(self, f"{self.code}: {self.message}")

    @property
    def spec(self) -> ErrorCode:
        return REGISTRY[self.code]

    @property
    def retryable(self) -> bool:
        return self.spec.retryable

    def to_dict(self) -> dict[str, Any]:
        from .redaction import redact
        out = {
            "schema": "PK_AGENT_ERROR/1",
            "registry": REGISTRY_VERSION,
            "code": self.code,
            "category": self.spec.category,
            "severity": self.spec.severity,
            "retryable": self.spec.retryable,
            "rpc_status": self.spec.rpc_status,
            "http_status": self.spec.http_status,
            "message": self.message,
            "details": redact(self.details),
            "correlation_id": self.correlation_id,
        }
        if self.cause is not None:
            out["cause"] = self.cause.to_dict()
        return out


def translate(exc: BaseException, correlation_id: str | None = None) -> AgentError:
    """Centralised exception -> AgentError translation.

    Unknown exceptions map to AGT-INTERNAL-001 with only the exception *type*
    retained; the message is dropped because it may embed secrets.
    """
    cid = correlation_id or new_correlation_id()
    if isinstance(exc, AgentError):
        return exc
    if isinstance(exc, TimeoutError):
        return AgentError("AGT-TMO-001", correlation_id=cid)
    if isinstance(exc, PermissionError):
        return AgentError("AGT-APR-002", correlation_id=cid, details={"exception_type": "PermissionError"})
    if isinstance(exc, (ValueError, TypeError)):
        return AgentError("AGT-VAL-001", correlation_id=cid, details={"exception_type": type(exc).__name__})
    if isinstance(exc, RecursionError):
        return AgentError("AGT-VAL-002", correlation_id=cid)
    return AgentError("AGT-INTERNAL-001", correlation_id=cid, details={"exception_type": type(exc).__name__})
