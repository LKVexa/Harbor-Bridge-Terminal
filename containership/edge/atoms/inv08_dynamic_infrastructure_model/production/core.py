"""Shared primitives: canonical JSON, digests, result/error model (13, 23),
HMAC signing with an explicitly NON-PRODUCTION trust root, redaction."""
from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

# ---------------------------------------------------------------- canonical JSON

def canonical(obj: Any) -> bytes:
    """Deterministic JSON encoding (sorted keys, no whitespace, UTF-8, no NaN)."""
    def check(o: Any) -> None:
        if isinstance(o, float) and not math.isfinite(o):
            raise ValueError("non-finite float cannot be canonically encoded")
        if isinstance(o, dict):
            for k, v in o.items():
                if not isinstance(k, str):
                    raise TypeError(f"canonical JSON keys must be str, got {k!r}")
                check(v)
        elif isinstance(o, (list, tuple)):
            for v in o:
                check(v)
    check(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(obj: Any) -> str:
    return "sha256:" + sha256_hex(canonical(obj))

# ---------------------------------------------------------------- results (13)

class Outcome(str, Enum):
    """Stable result codes.  Adding a value is compatible; removing or renaming
    one is a breaking change (see ``RESULT_CODE_POLICY``)."""
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    DEGRADED = "DEGRADED"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    OPERATOR_REQUIRED = "OPERATOR_REQUIRED"
    BLOCKED = "BLOCKED"


RESULT_CODE_POLICY = {
    "version": "PK_DYN_RESULT/1",
    "add": "minor - consumers MUST treat unknown codes as OPERATOR_REQUIRED",
    "deprecate": "announce one minor release ahead; keep accepting for two minors",
    "remove_or_rename": "major version only",
}

RETRYABLE = {Outcome.RETRYABLE_FAILURE, Outcome.DEGRADED}


def parse_outcome(value: str) -> Outcome:
    """Unknown codes from newer peers degrade to OPERATOR_REQUIRED (fail safe)."""
    try:
        return Outcome(value)
    except ValueError:
        return Outcome.OPERATOR_REQUIRED

# ---------------------------------------------------------------- redaction

_SECRET_PATTERNS = [
    re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key)\s*[=:]\s*\S+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
]
SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "private_key", "credential",
                  "authorization", "email"}


def redact_text(text: str) -> str:
    for pat in _SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: ("[REDACTED]" if k.lower() in SENSITIVE_KEYS else redact(v)) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact(v) for v in obj]
    if isinstance(obj, str):
        return redact_text(obj)
    return obj

# ---------------------------------------------------------------- errors (23)

ERROR_NAMESPACE = "INV08"


@dataclass
class Inv08Error(Exception):
    code: str                       # INV08.<DOMAIN>.<NAME>
    message: str
    outcome: Outcome = Outcome.TERMINAL_FAILURE
    severity: str = "error"         # info|warning|error|critical
    remediation: str = ""
    details: dict = field(default_factory=dict)
    cause: "Inv08Error | None" = None

    def __post_init__(self) -> None:
        if not re.fullmatch(rf"{ERROR_NAMESPACE}\.[A-Z0-9_]+\.[A-Z0-9_]+", self.code):
            raise ValueError(f"error code {self.code!r} outside the {ERROR_NAMESPACE} namespace")
        if self.severity not in {"info", "warning", "error", "critical"}:
            raise ValueError(f"bad severity {self.severity!r}")
        Exception.__init__(self, f"{self.code}: {self.message}")

    @property
    def retryable(self) -> bool:
        return self.outcome in RETRYABLE

    def chain(self) -> list[str]:
        out, cur = [], self
        while cur is not None:
            out.append(cur.code)
            cur = cur.cause
        return out

    def to_dict(self) -> dict:
        d = {
            "code": self.code, "message": redact_text(self.message), "outcome": self.outcome.value,
            "retryable": self.retryable, "severity": self.severity,
            "remediation": self.remediation, "details": redact(self.details),
        }
        if self.cause is not None:
            d["cause"] = self.cause.to_dict()
        return d


def wrap_provider_error(provider: str, exc: BaseException, *, retryable: bool) -> Inv08Error:
    """Translate an arbitrary provider exception into the stable namespace."""
    return Inv08Error(
        code="INV08.PROVIDER.RETRYABLE" if retryable else "INV08.PROVIDER.TERMINAL",
        message=f"{provider}: {type(exc).__name__}: {exc}",
        outcome=Outcome.RETRYABLE_FAILURE if retryable else Outcome.TERMINAL_FAILURE,
        remediation="check provider status; retry is automatic" if retryable else "operator review required",
        details={"provider": provider, "exception_type": type(exc).__name__},
    )

# ---------------------------------------------------------------- signing

class TrustRoot:
    """HMAC-SHA256 keyring.

    The stdlib offers no asymmetric signature primitive, so this keyring is a
    *symmetric* integrity mechanism.  Every key carries ``production: False``
    unless constructed from an external KMS binding (none exists in this
    overlay), and ``verify(..., require_production=True)`` therefore always
    fails.  That is deliberate: a nonproduction key must never satisfy a
    production gate.
    """

    def __init__(self) -> None:
        self._keys: dict[str, tuple[bytes, bool, bool]] = {}  # kid -> (key, production, revoked)

    def add(self, kid: str, key: bytes, *, production: bool = False) -> None:
        if len(key) < 32:
            raise ValueError("HMAC keys must be >= 32 bytes")
        if production:
            raise PermissionError("production keys require an external KMS binding (not provisioned)")
        self._keys[kid] = (key, production, False)

    def revoke(self, kid: str) -> None:
        key, prod, _ = self._keys[kid]
        self._keys[kid] = (key, prod, True)

    def sign(self, kid: str, payload: Any) -> dict:
        key, prod, revoked = self._keys[kid]
        if revoked:
            raise PermissionError(f"key {kid} is revoked")
        mac = hmac.new(key, canonical(payload), hashlib.sha256).hexdigest()
        return {"alg": "HMAC-SHA256", "kid": kid, "production": prod, "mac": mac}

    def verify(self, payload: Any, sig: dict, *, require_production: bool = False) -> bool:
        if not isinstance(sig, dict) or sig.get("alg") != "HMAC-SHA256":
            return False
        entry = self._keys.get(sig.get("kid", ""))
        if entry is None:
            return False
        key, prod, revoked = entry
        if revoked or (require_production and not prod):
            return False
        want = hmac.new(key, canonical(payload), hashlib.sha256).hexdigest()
        return hmac.compare_digest(want, str(sig.get("mac", "")))
