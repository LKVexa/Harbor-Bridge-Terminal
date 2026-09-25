"""G13-MC-016 structured error model.

Every refusal raised by GAP-13 carries a stable machine-readable ``code``, a
``retryable`` flag and a ``details`` mapping that never contains secrets or raw
request payloads.  Codes are part of the public contract (see
``docs/ERROR_CODES.md``) and are append-only: a code is never renamed or reused.
"""
from __future__ import annotations

from typing import Any, Mapping


class PolicyError(Exception):
    """Base class for every GAP-13 refusal."""

    code = "G13-E000"
    retryable = False
    fail_closed = True

    def __init__(self, message: str, *, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "PK_POLICY_ERROR/1",
            "code": self.code,
            "error": type(self).__name__,
            "message": self.message,
            "retryable": self.retryable,
            "details": self.details,
        }


def _make(name: str, code: str, base: type = PolicyError, retryable: bool = False, doc: str = "") -> type:
    cls = type(name, (base,), {"code": code, "retryable": retryable, "__doc__": doc})
    return cls


# PermissionError compatibility is kept for callers written against 4.x.
class BundleRejected(PolicyError, PermissionError):
    """A policy bundle failed validation/verification and was not loaded."""
    code = "G13-E100"


class ScopeEscalation(BundleRejected):
    """A tenant allow rule would widen estate-level authority."""
    code = "G13-E101"


BundleParseError = _make("BundleParseError", "G13-E110", BundleRejected, doc="Bundle bytes are not syntactically valid.")
BundleTooLarge = _make("BundleTooLarge", "G13-E111", BundleRejected, doc="Bundle exceeds a configured size/count/depth limit.")
SchemaMismatch = _make("SchemaMismatch", "G13-E112", BundleRejected, doc="Unsupported or unknown schema version.")
BundleSemanticError = _make("BundleSemanticError", "G13-E113", BundleRejected, doc="Bundle parsed but violates semantic rules.")
VerificationFailed = _make("VerificationFailed", "G13-E120", BundleRejected, doc="Cryptographic verification did not yield VERIFIED.")
ReplayRejected = _make("ReplayRejected", "G13-E130", BundleRejected, doc="Bundle generation is at/below the anti-rollback floor, or collides.")
AntiReplayStateUnavailable = _make("AntiReplayStateUnavailable", "G13-E131", BundleRejected, retryable=True, doc="Durable anti-replay state is corrupt or unreadable; activation refused.")
BundleQuarantined = _make("BundleQuarantined", "G13-E140", BundleRejected, doc="Bundle identity/digest/generation is quarantined.")
UpdateFrozen = _make("UpdateFrozen", "G13-E141", BundleRejected, retryable=True, doc="Bundle updates are frozen by operator control.")

RequestRejected = _make("RequestRejected", "G13-E200", doc="Evaluation request is malformed or not admissible.")
AttributeRejected = _make("AttributeRejected", "G13-E201", RequestRejected, doc="Attribute unknown, mistyped, or in a protected namespace.")
RequestTooLarge = _make("RequestTooLarge", "G13-E202", RequestRejected, doc="Request exceeds attribute count/size limits.")
ContextUnavailable = _make("ContextUnavailable", "G13-E210", RequestRejected, retryable=True, doc="Trusted attribute provider unavailable; fail closed.")

StalePolicyRefused = _make("StalePolicyRefused", "G13-E300", retryable=True, doc="Active bundle is past hard expiry and mode is FAIL_CLOSED.")
EvaluationDisabled = _make("EvaluationDisabled", "G13-E301", retryable=True, doc="Evaluation disabled by emergency control.")
NoActivePolicy = _make("NoActivePolicy", "G13-E302", retryable=True, doc="No verified bundle is active.")
Overloaded = _make("Overloaded", "G13-E310", retryable=True, doc="Admission control shed the request.")
DeadlineExceeded = _make("DeadlineExceeded", "G13-E311", retryable=True, doc="Request deadline elapsed before evaluation.")

Unauthorized = _make("Unauthorized", "G13-E400", doc="Principal lacks the capability or scope for this operation.")
Unauthenticated = _make("Unauthenticated", "G13-E401", doc="Credential missing, expired, replayed, revoked or wrong audience.")

DependencyUnavailable = _make("DependencyUnavailable", "G13-E500", retryable=True, doc="An upstream dependency (verifier, distribution, sink) is unavailable.")
AuditSinkUnavailable = _make("AuditSinkUnavailable", "G13-E501", DependencyUnavailable, retryable=True, doc="Audit sink unavailable and buffer exhausted; privileged action refused.")
CacheCorrupt = _make("CacheCorrupt", "G13-E510", doc="Persistent cache failed integrity check.")
ConfigRejected = _make("ConfigRejected", "G13-E600", doc="Configuration invalid or unsafe.")


def registry() -> dict[str, type]:
    """Return every error class keyed by stable code (used by docs/tests)."""
    out: dict[str, type] = {}
    stack = [PolicyError]
    while stack:
        cls = stack.pop()
        if cls.code in out and out[cls.code] is not cls:
            raise RuntimeError(f"duplicate error code {cls.code}")
        out[cls.code] = cls
        stack.extend(cls.__subclasses__())
    return dict(sorted(out.items()))
