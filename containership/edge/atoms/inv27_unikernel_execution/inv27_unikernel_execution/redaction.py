"""Redaction for logs, audit details and diagnostics (C039, C075).

Credential-looking keys and values are replaced; tenant identifiers in high-cardinality diagnostic
output are pseudonymised with a keyed hash so operators can correlate without learning tenant names.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from typing import Any

MAX_DEPTH = 16
MAX_STR = 512
_KEY = re.compile(r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key|credential|authorization|mac$|signature)")
_VAL = re.compile(r"(?i)(-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?(-----END [A-Z ]*PRIVATE KEY-----|$)|"
                  r"\bsk-[A-Za-z0-9-]{8,}|\bghp_[A-Za-z0-9]{20,}|\bAKIA[0-9A-Z]{16}\b|"
                  r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]*|\bBearer\s+[A-Za-z0-9._~+/=-]{8,})")
REDACTED = "[REDACTED]"


def redact(value: Any, _depth: int = 0) -> Any:
    if _depth > MAX_DEPTH:
        return "[TRUNCATED-DEPTH]"
    if isinstance(value, dict):
        return {str(k)[:128]: (REDACTED if _KEY.search(str(k)) else redact(v, _depth + 1)) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact(v, _depth + 1) for v in (sorted(value, key=repr) if isinstance(value, (set, frozenset)) else value)]
    if isinstance(value, str):
        v = _VAL.sub(REDACTED, value)
        return v if len(v) <= MAX_STR else v[:MAX_STR] + "...[TRUNCATED]"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    return redact(repr(value), _depth + 1)


def pseudonym(tenant: str, key: bytes) -> str:
    return "t-" + hmac.new(key, tenant.encode(), hashlib.sha256).hexdigest()[:12]
