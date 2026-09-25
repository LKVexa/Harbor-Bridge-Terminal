"""MC-19: stable, machine-readable reason codes (GAP06-ERR/1).

Codes are append-only: a code is never renumbered or reused.  ``safe_detail``
never carries key material, raw quotes or nonces beyond an 8-hex prefix.
"""
from __future__ import annotations

import enum
import re
from dataclasses import dataclass, field

SCHEMA = "GAP06-ERR/1"


class Category(str, enum.Enum):
    MALFORMED = "malformed"
    AUTHENTICATION = "authentication"
    FRESHNESS = "freshness"
    MEASUREMENT = "measurement"
    UNSUPPORTED = "unsupported"
    TCB = "tcb"
    AUTHORIZATION = "authorization"
    CAPACITY = "capacity"
    STATE = "state"
    INTERNAL = "internal"


# code -> (category, retryable, http_status)
CODES: dict[str, tuple[Category, bool, int]] = {
    "E_MALFORMED_EVIDENCE": (Category.MALFORMED, False, 400),
    "E_TRAILING_BYTES": (Category.MALFORMED, False, 400),
    "E_BAD_MAGIC": (Category.MALFORMED, False, 400),
    "E_SCHEMA": (Category.MALFORMED, False, 400),
    "E_SIGNATURE": (Category.AUTHENTICATION, False, 401),
    "E_UNKNOWN_KEY": (Category.AUTHENTICATION, False, 401),
    "E_CERT_CHAIN": (Category.AUTHENTICATION, False, 401),
    "E_CERT_REVOKED": (Category.AUTHENTICATION, False, 401),
    "E_POP_FAILED": (Category.AUTHENTICATION, False, 401),
    "E_NONCE_MISMATCH": (Category.FRESHNESS, False, 409),
    "E_REPLAY": (Category.FRESHNESS, False, 409),
    "E_CHALLENGE_EXPIRED": (Category.FRESHNESS, True, 409),
    "E_UNISSUED_CHALLENGE": (Category.FRESHNESS, False, 409),
    "E_CLOCK_ROLLBACK": (Category.FRESHNESS, False, 409),
    "E_TPM_CLOCK_UNSAFE": (Category.FRESHNESS, False, 409),
    "E_TIME_UNTRUSTED": (Category.FRESHNESS, True, 503),
    "E_PCR_MISMATCH": (Category.MEASUREMENT, False, 422),
    "E_EVENTLOG_MISMATCH": (Category.MEASUREMENT, False, 422),
    "E_MEASUREMENT_REJECTED": (Category.MEASUREMENT, False, 422),
    "E_UNSUPPORTED_ALG": (Category.UNSUPPORTED, False, 422),
    "E_UNSUPPORTED_PLATFORM": (Category.UNSUPPORTED, False, 422),
    "E_TCB_OUT_OF_DATE": (Category.TCB, False, 422),
    "E_DEBUG_ENABLED": (Category.TCB, False, 422),
    "E_UNAUTHENTICATED": (Category.AUTHORIZATION, False, 401),
    "E_FORBIDDEN": (Category.AUTHORIZATION, False, 403),
    "E_TENANT_BOUNDARY": (Category.AUTHORIZATION, False, 403),
    "E_RATE_LIMITED": (Category.CAPACITY, True, 429),
    "E_OVERLOADED": (Category.CAPACITY, True, 503),
    "E_UNKNOWN_NODE": (Category.STATE, False, 404),
    "E_REVOKED": (Category.STATE, False, 403),
    "E_DUPLICATE_IDENTITY": (Category.STATE, False, 409),
    "E_CONFLICT": (Category.STATE, True, 409),
    "E_POLICY_ROLLBACK": (Category.STATE, False, 409),
    "E_POLICY_UNSIGNED": (Category.AUTHENTICATION, False, 401),
    "E_QUORUM": (Category.AUTHORIZATION, False, 403),
    "E_FENCED": (Category.STATE, True, 409),
    "E_LEDGER_TAMPER": (Category.INTERNAL, False, 500),
    "E_STATE_CORRUPT": (Category.INTERNAL, False, 500),
    "E_INTERNAL": (Category.INTERNAL, True, 500),
}

_REDACT = [
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S), "[REDACTED-PRIVATE-KEY]"),
    (re.compile(r"\b[0-9a-fA-F]{32,}\b"), lambda m: m.group(0)[:8] + "…"),
]


def redact(text: str) -> str:
    """Remove private-key blocks; truncate long hex (nonces, digests, keys)."""
    for pattern, repl in _REDACT:
        text = pattern.sub(repl, text)
    return text


@dataclass(eq=False)  # not frozen: the runtime must be able to set __traceback__/__context__
class Gap06Error(Exception):
    code: str
    detail: str = ""
    context: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.code not in CODES:
            raise ValueError(f"unregistered error code {self.code}")

    @property
    def category(self) -> Category:
        return CODES[self.code][0]

    @property
    def retryable(self) -> bool:
        return CODES[self.code][1]

    def to_dict(self) -> dict:
        cat, retry, status = CODES[self.code]
        return {"schema": SCHEMA, "code": self.code, "category": cat.value, "retryable": retry,
                "http_status": status, "safe_detail": redact(self.detail)[:512],
                "context": {k: redact(str(v))[:128] for k, v in sorted(self.context.items())}}

    def __str__(self) -> str:  # pragma: no cover - exercised implicitly
        return f"{self.code}: {redact(self.detail)}"


def fail(code: str, detail: str = "", **context) -> Gap06Error:
    return Gap06Error(code, detail, context)
