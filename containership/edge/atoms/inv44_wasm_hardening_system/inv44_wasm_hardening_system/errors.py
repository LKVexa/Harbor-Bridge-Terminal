"""Structured failure codes for INV-44 (C026, C014).

Every refusal the system produces maps to exactly one stable code, an outcome
class, and a retry disposition. Codes are part of PK_WASM_HARDENING/1 and
PK_WASM_INSTANCE/1; adding one is a minor change, renaming or removing one is a
major (breaking) change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

#: Outcome classes (C014). ``success`` and ``degraded`` are the only non-failures.
OUTCOMES: Final[tuple[str, ...]] = (
    "success", "degraded", "retryable_failure", "terminal_failure",
)


@dataclass(frozen=True, slots=True)
class ErrorCode:
    code: str
    outcome: str
    retryable: bool
    summary: str


_CODES: Final[tuple[ErrorCode, ...]] = (
    ErrorCode("WH-HARDENING-INCOMPLETE", "terminal_failure", False, "a required hardening feature is inactive"),
    ErrorCode("WH-OUTPUT-UNVERIFIED", "terminal_failure", False, "compiled output failed verification"),
    ErrorCode("WH-OUTPUT-MALFORMED", "terminal_failure", False, "module bytes are not a structurally valid Wasm binary"),
    ErrorCode("WH-RECEIPT-INVALID", "terminal_failure", False, "verification receipt signature, digest or toolchain did not match"),
    ErrorCode("WH-TOOLCHAIN-UNAPPROVED", "terminal_failure", False, "the compiler/verifier identity is not on the approved list"),
    ErrorCode("WH-FUEL-EXHAUSTED", "terminal_failure", False, "instance consumed its fuel budget"),
    ErrorCode("WH-MEMORY-CEILING", "terminal_failure", False, "linear memory would exceed its ceiling"),
    ErrorCode("WH-INSTANCE-BYPASS", "terminal_failure", False, "instance construction bypassed the engine factory"),
    ErrorCode("WH-INVALID-ARGUMENT", "terminal_failure", False, "an argument failed type or range validation"),
    ErrorCode("WH-AUTHN-FAILED", "terminal_failure", False, "caller identity could not be authenticated"),
    ErrorCode("WH-AUTHZ-DENIED", "terminal_failure", False, "caller lacks the capability for this operation"),
    ErrorCode("WH-CAPABILITY-EXPIRED", "terminal_failure", False, "capability token is expired or revoked"),
    ErrorCode("WH-AMBIENT-IMPORT", "terminal_failure", False, "module imports an ambient host authority not granted"),
    ErrorCode("WH-TENANT-MISMATCH", "terminal_failure", False, "request crosses the engine's tenant boundary"),
    ErrorCode("WH-CONFIG-INVALID", "terminal_failure", False, "configuration document failed schema validation"),
    ErrorCode("WH-CONFIG-CONFLICT", "retryable_failure", True, "configuration changed concurrently; re-read and retry"),
    ErrorCode("WH-AUDIT-CHAIN-BROKEN", "terminal_failure", False, "audit log chain verification failed"),
    ErrorCode("WH-DEPENDENCY-UNAVAILABLE", "retryable_failure", True, "a trust dependency (key, clock, policy) is unavailable"),
    ErrorCode("WH-OVERLOADED", "retryable_failure", True, "admission control shed the request"),
    ErrorCode("WH-TIMEOUT", "retryable_failure", True, "operation exceeded its deadline"),
    ErrorCode("WH-CANCELLED", "terminal_failure", False, "operation was cancelled by the caller"),
    ErrorCode("WH-VERSION-UNSUPPORTED", "terminal_failure", False, "peer requested an unsupported interface version"),
)

CODES: Final[dict[str, ErrorCode]] = {c.code: c for c in _CODES}


class HardeningError(Exception):
    """Base for structured refusals raised by the v4.3 subsystems."""

    code = "WH-INVALID-ARGUMENT"

    def __init__(self, message: str, *, code: str | None = None, **detail: object) -> None:
        super().__init__(message)
        if code is not None:
            if code not in CODES:
                raise ValueError(f"unknown error code {code!r}")
            self.code = code
        self.detail = dict(detail)

    def to_dict(self) -> dict:
        spec = CODES[self.code]
        return {
            "code": spec.code,
            "outcome": spec.outcome,
            "retryable": spec.retryable,
            "message": str(self),
            "detail": {k: v for k, v in sorted(self.detail.items())},
        }


def classify(exc: BaseException) -> dict:
    """Map any exception raised by INV-44 to a structured error document."""
    from . import runtime  # local import keeps runtime free of this module

    if isinstance(exc, HardeningError):
        return exc.to_dict()
    table = (
        (runtime.HardeningIncomplete, "WH-HARDENING-INCOMPLETE"),
        (runtime.OutputUnverified, "WH-OUTPUT-UNVERIFIED"),
        (runtime.FuelExhausted, "WH-FUEL-EXHAUSTED"),
        (runtime.MemoryCeiling, "WH-MEMORY-CEILING"),
        (runtime.InstanceConstructionDenied, "WH-INSTANCE-BYPASS"),
        (TypeError, "WH-INVALID-ARGUMENT"),
        (ValueError, "WH-INVALID-ARGUMENT"),
    )
    for kind, code in table:
        if isinstance(exc, kind):
            return HardeningError(str(exc), code=code).to_dict()
    # Unknown failures are never reported as success or as retryable.
    return {"code": "WH-INVALID-ARGUMENT", "outcome": "terminal_failure",
            "retryable": False, "message": f"unclassified: {type(exc).__name__}", "detail": {}}
