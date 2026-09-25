"""PK_DEVICE_ERROR/1 - stable machine-readable error contract for INV-25.

Dependency-free.  Library callers keep ordinary Python exceptions
(``DeviceRejected`` and friends, all carrying ``.code``); external boundaries
call :func:`to_error` to obtain a deterministic, redacted serialization.
Codes are a permanent compatibility surface: they may be added, never renamed
or re-purposed.
"""
from __future__ import annotations

import re
from typing import Any

SCHEMA = "PK_DEVICE_ERROR/1"

# code -> (category, retryable, safe default message)
CODES: dict[str, tuple[str, bool, str]] = {
    "INV25_INVALID_NAME": ("validation", False, "device name is invalid"),
    "INV25_INVALID_CLASS": ("validation", False, "device class is not a recognised permitted class"),
    "INV25_FORBIDDEN_LEGACY_EMULATION": ("policy", False, "legacy emulation is never permitted"),
    "INV25_FORBIDDEN_HOST_EXPOSURE": ("policy", False, "host passthrough / raw MMIO is never permitted"),
    "INV25_INVALID_VERSION": ("validation", False, "version identifier is not supported"),
    "INV25_INVALID_REGISTER": ("validation", False, "guest-visible register identifier is invalid"),
    "INV25_MISSING_RATIONALE": ("validation", False, "a rationale is required"),
    "INV25_MISSING_REVIEWER": ("validation", False, "a reviewer is required"),
    "INV25_INVALID_FIELD": ("validation", False, "a field is malformed"),
    "INV25_REPLACE_REQUIRED": ("conflict", False, "changed entry must use replace()"),
    "INV25_REPLACE_TARGET_ABSENT": ("conflict", False, "replacement target is not catalogued"),
    "INV25_VERSION_NOT_CHANGED": ("conflict", False, "changed entry requires a new version"),
    "INV25_VERSION_DOWNGRADE": ("policy", False, "version downgrade refused by anti-downgrade policy"),
    "INV25_CONCURRENT_MODIFICATION": ("conflict", True, "expected catalogue digest no longer current"),
    "INV25_UNAUTHENTICATED": ("security", False, "authentication failed"),
    "INV25_UNAUTHORIZED": ("security", False, "operation not authorized"),
    "INV25_REPLAY_DETECTED": ("security", False, "request replay detected"),
    "INV25_ARTIFACT_VERIFICATION_FAILED": ("security", False, "artifact digest/signature/provenance verification failed"),
    "INV25_COMPATIBILITY_MISMATCH": ("compatibility", False, "no mutually supported version"),
    "INV25_LIMIT_EXCEEDED": ("capacity", False, "a resource ceiling was exceeded"),
    "INV25_RATE_LIMITED": ("capacity", True, "rate limit exceeded"),
    "INV25_DEPENDENCY_UNAVAILABLE": ("dependency", True, "a required dependency is unavailable"),
    "INV25_DEVICE_DISABLED": ("policy", False, "device is under emergency disable"),
    "INV25_AUDIT_UNAVAILABLE": ("dependency", True, "audit sink unavailable; mutation refused"),
    "INV25_INTERNAL": ("internal", False, "internal error"),
}

_SAFE_DETAIL = re.compile(r"^[A-Za-z0-9 ._:/@+=,-]{0,128}$")
_SENSITIVE_KEYS = ("token", "secret", "key", "password", "credential", "path", "trace")


class Inv25Error(Exception):
    """Base for every INV-25 exception that carries a stable code."""

    code = "INV25_INTERNAL"

    def __init__(self, message: str = "", *, code: str | None = None, **details: Any) -> None:
        super().__init__(message or CODES[code or self.code][2])
        if code is not None:
            if code not in CODES:
                raise ValueError(f"unknown error code {code!r}")
            self.code = code
        self.details = details


def _redact(details: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in sorted(details.items()):
        if any(s in k.lower() for s in _SENSITIVE_KEYS):
            continue
        if isinstance(v, bool) or isinstance(v, int):
            out[k] = v
        elif isinstance(v, str) and _SAFE_DETAIL.fullmatch(v):
            out[k] = v
        else:
            out[k] = "[redacted]"
    return out


def to_error(exc: BaseException, *, operation: str, correlation_id: str = "",
             device: str = "", environment: str = "") -> dict[str, Any]:
    """Serialize any exception to PK_DEVICE_ERROR/1. Unknown failures map to INV25_INTERNAL."""
    code = getattr(exc, "code", "INV25_INTERNAL")
    if code not in CODES:
        code = "INV25_INTERNAL"
    category, retryable, message = CODES[code]
    rec: dict[str, Any] = {
        "schema": SCHEMA, "code": code, "category": category, "message": message,
        "retryable": retryable, "operation": operation,
    }
    for k, v in (("device", device), ("environment", environment), ("correlation_id", correlation_id)):
        if v:
            rec[k] = v
    details = _redact(getattr(exc, "details", {}) or {})
    if details:
        rec["details"] = details
    return rec
