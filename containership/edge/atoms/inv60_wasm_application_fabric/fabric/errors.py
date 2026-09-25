"""M09/M20 - result envelope and versioned error registry.

Every public operation returns a :class:`Result`. Codes are stable strings and
numbers independent of message text; messages are redacted and size-bounded
before serialization. Unknown codes decode to ``UNKNOWN`` (forward compatible).
"""
from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

ERROR_REGISTRY_VERSION = "1.0.0"
MAX_SERIALIZED_ERROR_BYTES = 4096
MAX_DETAIL_FIELDS = 16

# outcome classes (M09)
OUTCOMES = ("ok", "accepted", "partial", "degraded", "retryable", "permanent",
            "conflict", "unauthorized", "unavailable", "limit", "integrity", "invalid")

# code -> (number, category, outcome, retry hint, meaning)
REGISTRY: dict[str, tuple[int, str, str, str, str]] = {
    "OK":                    (0,   "none",        "ok",           "never", "operation succeeded"),
    "ACCEPTED":              (1,   "none",        "accepted",     "never", "accepted; completion observed via status"),
    "PARTIAL":               (2,   "none",        "partial",      "safe",  "fan-out operation succeeded on a subset; see per-target results"),
    "DEGRADED":              (3,   "none",        "degraded",     "never", "succeeded in a declared degraded mode"),
    "INVALID_ARGUMENT":      (100, "caller",      "invalid",      "never", "request failed validation"),
    "UNSUPPORTED_VERSION":   (101, "caller",      "invalid",      "never", "no mutually supported protocol version"),
    "PAYLOAD_TOO_LARGE":     (102, "limit",       "limit",        "never", "payload exceeds configured maximum"),
    "UNAUTHENTICATED":       (200, "auth",        "unauthorized", "never", "caller identity could not be established"),
    "PERMISSION_DENIED":     (201, "auth",        "unauthorized", "never", "policy denied the action"),
    "NOT_LINKED":            (202, "auth",        "unauthorized", "never", "capability link absent or revoked"),
    "REPLAY_DETECTED":       (203, "auth",        "unauthorized", "never", "credential or request nonce reused"),
    "ALREADY_EXISTS":        (300, "conflict",    "conflict",     "never", "resource already exists"),
    "ILLEGAL_TRANSITION":    (301, "conflict",    "conflict",     "never", "lifecycle transition not permitted from current state"),
    "STALE_GENERATION":      (302, "conflict",    "conflict",     "never", "configuration/lease generation is stale"),
    "FENCED":                (303, "conflict",    "conflict",     "never", "writer fenced by a newer lease epoch"),
    "IDEMPOTENCY_MISMATCH":  (304, "conflict",    "conflict",     "never", "idempotency key reused with a different request"),
    "QUOTA_EXCEEDED":        (400, "limit",       "limit",        "after", "quota exhausted for scope"),
    "RATE_LIMITED":          (401, "limit",       "limit",        "after", "rate limit exceeded"),
    "OVERLOADED":            (402, "limit",       "limit",        "after", "admission control shed the request"),
    "CIRCUIT_OPEN":          (403, "transient",   "retryable",    "after", "dependency circuit open"),
    "DEADLINE_EXCEEDED":     (500, "transient",   "retryable",    "unknown", "deadline expired before completion"),
    "CANCELLED":             (501, "transient",   "retryable",    "unknown", "operation cancelled by caller"),
    "UNAVAILABLE":           (502, "transient",   "unavailable",  "safe",  "target or dependency unavailable"),
    "NO_ELIGIBLE_TARGET":    (503, "placement",   "unavailable",  "after", "no host satisfies hard constraints"),
    "PARTITIONED":           (504, "transient",   "unavailable",  "after", "operation requires quorum/authority not held"),
    "QUARANTINED":           (505, "control",     "unavailable",  "never", "target quarantined or frozen by operator"),
    "NOT_FOUND":             (506, "caller",      "permanent",    "never", "resource not found"),
    "DIGEST_MISMATCH":       (600, "integrity",   "integrity",    "never", "artifact bytes do not hash to reference"),
    "SIGNATURE_INVALID":     (601, "integrity",   "integrity",    "never", "artifact signature/provenance verification failed"),
    "LEDGER_BROKEN":         (602, "integrity",   "integrity",    "never", "audit chain verification failed"),
    "PROVIDER_ERROR":        (700, "dependency",  "retryable",    "unknown", "capability provider raised"),
    "BACKEND_NOT_CONFIGURED":(701, "dependency",  "unavailable",  "never", "execution backend not configured"),
    "INTERNAL":              (900, "internal",    "permanent",    "unknown", "unexpected internal error"),
    "UNKNOWN":               (999, "unknown",     "permanent",    "unknown", "code not known to this client version"),
}
RETRY_HINTS = ("never", "safe", "after", "unknown")

_SECRET_PATTERNS = [
    re.compile(r"(?i)(secret|password|passwd|token|api[_-]?key|private[_-]?key|authorization)\s*[=:]\s*\S+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\b[A-Za-z0-9+/]{40,}={0,2}\b"),
]
_SENSITIVE_KEYS = re.compile(r"(?i)secret|password|token|key|credential|authorization|cookie")


def redact(text: str) -> str:
    out = str(text)
    for pat in _SECRET_PATTERNS:
        out = pat.sub("[REDACTED]", out)
    return out


def redact_detail(detail: dict[str, Any]) -> dict[str, Any]:
    clean: dict[str, Any] = {}
    for i, (k, v) in enumerate(sorted(detail.items())):
        if i >= MAX_DETAIL_FIELDS:
            clean["_truncated"] = True
            break
        if _SENSITIVE_KEYS.search(str(k)):
            clean[str(k)] = "[REDACTED]"
        elif isinstance(v, (int, float, bool)) or v is None:
            clean[str(k)] = v
        else:
            clean[str(k)] = redact(str(v))[:256]
    return clean


def new_operation_id() -> str:
    return "op-" + uuid.uuid4().hex


@dataclass
class Result:
    code: str = "OK"
    message: str = ""
    operation_id: str = field(default_factory=new_operation_id)
    principal: str | None = None
    target: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)
    per_target: list["Result"] = field(default_factory=list)
    value: Any = None
    retry_after_s: float | None = None
    timestamp: float = field(default_factory=time.time)
    _cause: BaseException | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.code not in REGISTRY:
            self.code = "UNKNOWN"

    @property
    def success(self) -> bool:
        return REGISTRY[self.code][2] in ("ok", "accepted", "degraded")

    @property
    def outcome(self) -> str:
        return REGISTRY[self.code][2]

    @property
    def retry(self) -> str:
        return REGISTRY[self.code][3]

    def to_wire(self) -> dict[str, Any]:
        num, cat, outcome, hint, _ = REGISTRY[self.code]
        wire: dict[str, Any] = {
            "schema": "inv60.result/1",
            "code": self.code, "number": num, "category": cat, "outcome": outcome,
            "retry": hint, "message": redact(self.message)[:512],
            "operation_id": self.operation_id, "timestamp": round(self.timestamp, 6),
            "principal": self.principal, "target": self.target,
            "detail": redact_detail(self.detail),
        }
        if self.retry_after_s is not None and hint == "after":
            wire["retry_after_s"] = float(self.retry_after_s)
        if self.per_target:
            wire["per_target"] = [r.to_wire() for r in self.per_target]
        data = json.dumps(wire, sort_keys=True)
        if len(data.encode()) > MAX_SERIALIZED_ERROR_BYTES:
            wire["detail"] = {"_truncated": True}
            wire.pop("per_target", None)
            wire["message"] = wire["message"][:128]
        return wire

    @classmethod
    def from_wire(cls, wire: dict[str, Any]) -> "Result":
        code = wire.get("code", "UNKNOWN")
        return cls(code=code if code in REGISTRY else "UNKNOWN",
                   message=str(wire.get("message", "")),
                   operation_id=str(wire.get("operation_id") or new_operation_id()),
                   principal=wire.get("principal"), target=wire.get("target"),
                   detail=dict(wire.get("detail") or {}),
                   per_target=[cls.from_wire(w) for w in wire.get("per_target", [])],
                   retry_after_s=wire.get("retry_after_s"),
                   timestamp=float(wire.get("timestamp", time.time())))


class FabricError(Exception):
    """Raised internally; carries a registry code. Converted to Result at the boundary."""

    def __init__(self, code: str, message: str = "", *, detail: dict | None = None,
                 retry_after_s: float | None = None) -> None:
        super().__init__(message or code)
        self.code = code if code in REGISTRY else "INTERNAL"
        self.detail = detail or {}
        self.retry_after_s = retry_after_s


def map_exception(exc: BaseException) -> str:
    """Map internal / runtime exceptions to public codes (M20)."""
    from .. import runtime as rt
    if isinstance(exc, FabricError):
        return exc.code
    table = [
        (rt.DigestMismatch, "DIGEST_MISMATCH"), (rt.NotLinked, "NOT_LINKED"),
        (rt.UnknownArtifact, "NOT_FOUND"), (rt.AlreadyRunning, "ALREADY_EXISTS"),
        (rt.InvalidConfiguration, "INVALID_ARGUMENT"), (TimeoutError, "DEADLINE_EXCEEDED"),
        (PermissionError, "PERMISSION_DENIED"), (LookupError, "NOT_FOUND"),
        (TypeError, "INVALID_ARGUMENT"), (ValueError, "INVALID_ARGUMENT"),
        (ConnectionError, "UNAVAILABLE"),
    ]
    for klass, code in table:
        if isinstance(exc, klass):
            return code
    return "INTERNAL"


def result_from_exception(exc: BaseException, **kw: Any) -> Result:
    code = map_exception(exc)
    r = Result(code=code, message=str(exc), _cause=exc, **kw)
    if isinstance(exc, FabricError):
        r.detail.update(exc.detail)
        r.retry_after_s = exc.retry_after_s
    return r
