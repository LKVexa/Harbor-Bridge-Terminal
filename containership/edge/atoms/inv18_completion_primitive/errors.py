"""Structured failure taxonomy for INV-18 (C014, C026).

Stable machine-readable codes are kept separate from human-readable messages.
Codes never change meaning across patch/minor releases; new codes may be added
in a minor release and peers MUST map unknown codes to ``UNKNOWN`` while
preserving the original value (forward compatibility).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

ERROR_SCHEMA = "PK_FUTURE_ERROR/1"

# Outcome categories (C014).  PARTIAL_SUCCESS is structurally impossible for a
# one-shot primitive: a terminal record holds exactly one value or one error.
SUCCESS = "SUCCESS"
DEGRADED = "DEGRADED"
RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
TERMINAL_FAILURE = "TERMINAL_FAILURE"
ABANDONED = "ABANDONED"
OUTCOME_CATEGORIES = (SUCCESS, DEGRADED, RETRYABLE_FAILURE, TERMINAL_FAILURE, ABANDONED)


@dataclass(frozen=True)
class CodeSpec:
    code: str
    category: str
    retryable: bool
    severity: str          # telemetry severity: info | warning | error | critical
    operator_action: str
    consumes_receiver: bool  # does this outcome consume receiver ownership?
    precedence: int          # lower number wins when several conditions coexist


_SPECS = [
    CodeSpec("COMPONENT_DISABLED", DEGRADED, True, "warning", "check quarantine state; re-enable under admin authority", False, 10),
    CodeSpec("UNAUTHENTICATED", TERMINAL_FAILURE, False, "warning", "inspect caller credentials; audit event emitted", False, 20),
    CodeSpec("PERMISSION_DENIED", TERMINAL_FAILURE, False, "warning", "inspect capability grant; audit event emitted", False, 30),
    CodeSpec("REPLAY_DETECTED", TERMINAL_FAILURE, False, "error", "possible replay attack; follow security escalation", False, 35),
    CodeSpec("STALE_EPOCH", TERMINAL_FAILURE, False, "warning", "stale owner fenced; confirm failover completed", False, 36),
    CodeSpec("INCOMPATIBLE_VERSION", TERMINAL_FAILURE, False, "error", "upgrade/downgrade peer to a supported contract version", False, 40),
    CodeSpec("INVALID_CONFIG", TERMINAL_FAILURE, False, "critical", "fix configuration; component stays unready", False, 45),
    CodeSpec("RESOURCE_EXHAUSTED", RETRYABLE_FAILURE, True, "warning", "shed load or raise limits via reviewed config change", False, 50),
    CodeSpec("DEPENDENCY_UNAVAILABLE", RETRYABLE_FAILURE, True, "error", "restore dependency; component reports degraded", False, 55),
    CodeSpec("TIMEOUT", RETRYABLE_FAILURE, True, "warning", "caller-owned deadline expired; producer may still resolve", False, 60),
    CodeSpec("FUTURE_ALREADY_TAKEN", TERMINAL_FAILURE, False, "error", "second receiver is a modelling defect in the caller", False, 70),
    CodeSpec("FUTURE_ALREADY_RESOLVED", TERMINAL_FAILURE, False, "error", "second resolution is a producer defect; first value kept", False, 71),
    CodeSpec("FUTURE_CANCELLED", TERMINAL_FAILURE, False, "info", "receiver cancelled; producer should stop work", True, 72),
    CodeSpec("FUTURE_ABANDONED", ABANDONED, False, "warning", "writer dropped unresolved; investigate producer", True, 73),
    CodeSpec("TYPE_MISMATCH", TERMINAL_FAILURE, False, "error", "producer sent a value of the wrong type", False, 80),
    CodeSpec("INVALID_ARGUMENT", TERMINAL_FAILURE, False, "error", "malformed input; fix caller", False, 81),
    CodeSpec("INTERNAL_INVARIANT", TERMINAL_FAILURE, False, "critical", "invariant violated: page owner, quarantine component", False, 0),
    CodeSpec("UNKNOWN", TERMINAL_FAILURE, False, "error", "code from a newer peer; treat as terminal", False, 99),
]
CODES: dict[str, CodeSpec] = {s.code: s for s in _SPECS}

_SECRET_KEY = re.compile(r"(secret|token|password|passwd|credential|api[_-]?key|private)", re.I)
_SECRET_VALUE = re.compile(r"(sk-[A-Za-z0-9]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|SENTINEL-SECRET-[A-Za-z0-9]+)")
MAX_DETAIL_ITEMS = 16
MAX_TEXT = 512
MAX_CAUSE_DEPTH = 4


def redact_text(text: str) -> str:
    text = _SECRET_VALUE.sub("[REDACTED]", str(text))
    return text if len(text) <= MAX_TEXT else text[:MAX_TEXT] + "...[truncated]"


def redact(details: Mapping[str, Any] | None) -> dict[str, Any]:
    """Security-safe redaction: secret-looking keys and values are removed."""
    out: dict[str, Any] = {}
    for i, (k, v) in enumerate((details or {}).items()):
        if i >= MAX_DETAIL_ITEMS:
            out["_truncated"] = True
            break
        k = str(k)[:64]
        if _SECRET_KEY.search(k):
            out[k] = "[REDACTED]"
        elif isinstance(v, (int, float, bool)) or v is None:
            out[k] = v
        else:
            out[k] = redact_text(str(v))
    return out


@dataclass(frozen=True)
class ErrorRecord:
    code: str
    message: str = ""
    details: dict = field(default_factory=dict)
    cause: "ErrorRecord | None" = None
    original_code: str | None = None

    @property
    def spec(self) -> CodeSpec:
        return CODES.get(self.code, CODES["UNKNOWN"])

    @property
    def retryable(self) -> bool:
        return self.spec.retryable

    @property
    def category(self) -> str:
        return self.spec.category

    def to_dict(self) -> dict:
        d = {"schema": ERROR_SCHEMA, "code": self.code, "category": self.category,
             "retryable": self.retryable, "message": redact_text(self.message),
             "details": redact(self.details)}
        if self.original_code:
            d["original_code"] = self.original_code
        if self.cause is not None:
            d["cause"] = self.cause.to_dict()
        return d

    @classmethod
    def from_dict(cls, d: Mapping[str, Any], _depth: int = 0) -> "ErrorRecord":
        if not isinstance(d, Mapping) or d.get("schema") != ERROR_SCHEMA:
            raise ValueError("not a PK_FUTURE_ERROR/1 record")
        code = d.get("code")
        if not isinstance(code, str) or not code:
            raise ValueError("error record needs a code")
        original = None
        if code not in CODES:          # forward compatibility (C026/C027)
            original, code = code, "UNKNOWN"
        cause = None
        if d.get("cause") is not None:
            if _depth >= MAX_CAUSE_DEPTH:
                raise ValueError("cause chain too deep")
            cause = cls.from_dict(d["cause"], _depth + 1)
        details = d.get("details", {})
        if details is None:
            details = {}
        if not isinstance(details, Mapping):
            raise ValueError("details must be an object")
        oc = original or d.get("original_code")
        if oc is not None and (not isinstance(oc, str) or not re.fullmatch(r"[A-Z_]{2,64}", oc)):
            oc = None                                   # never echo malformed peer data
        return cls(code, str(d.get("message", "")), redact(details), cause, oc)


class FutureError(RuntimeError):
    """Base of every INV-18 exception; carries a stable code."""

    code = "INTERNAL_INVARIANT"

    def __init__(self, message: str = "", *, details: Mapping[str, Any] | None = None,
                 code: str | None = None):
        super().__init__(message)
        if code is not None:
            self.code = code
        self.details = dict(details or {})

    def record(self) -> ErrorRecord:
        return ErrorRecord(self.code, str(self), redact(self.details))


class Rejected(FutureError):
    """A runtime/adapter rejection carrying any structured code."""


def from_exception(exc: BaseException) -> ErrorRecord:
    """Map any Python exception to a structured record (C026)."""
    if isinstance(exc, FutureError):
        rec = exc.record()
    elif isinstance(exc, TypeError):
        rec = ErrorRecord("TYPE_MISMATCH", str(exc))
    elif isinstance(exc, ValueError):
        rec = ErrorRecord("INVALID_ARGUMENT", str(exc))
    elif isinstance(exc, TimeoutError):
        rec = ErrorRecord("TIMEOUT", str(exc))
    elif isinstance(exc, MemoryError):
        rec = ErrorRecord("RESOURCE_EXHAUSTED", "memory exhausted")
    else:
        rec = ErrorRecord("INTERNAL_INVARIANT", type(exc).__name__)
    cause = exc.__cause__
    if cause is not None and cause is not exc:
        rec = ErrorRecord(rec.code, rec.message, rec.details, from_exception(cause))
    return rec


def precedence(codes: list[str]) -> str:
    """Deterministic failure precedence when several conditions coexist (C011/C014)."""
    if not codes:
        raise ValueError("no codes")
    return min(codes, key=lambda c: CODES.get(c, CODES["UNKNOWN"]).precedence)
