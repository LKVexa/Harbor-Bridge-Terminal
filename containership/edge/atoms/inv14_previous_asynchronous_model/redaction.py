"""Secret-handling / redaction policy (component P2-31; C039, C047, C075).

INV-14 needs no secrets.  Policy RED-1..4:
  RED-1 MUST: any key matching SECRET_KEY_PATTERN is replaced by "[REDACTED]".
  RED-2 MUST: any string value matching a credential shape (bearer, token-like,
        PEM, key=value secret, capability token) is replaced by "[REDACTED]".
  RED-3 MUST: values are truncated to MAX_VALUE_CHARS, nesting to MAX_DEPTH and
        collections to MAX_ITEMS, so diagnostics are bounded.
  RED-4 MUST: the function is total -- unknown types become their bounded type name.
"""
from __future__ import annotations

import re

SECRET_KEY_PATTERN = re.compile(r"(pass(word)?|secret|token|api[_-]?key|authorization|cookie|credential|private|signature|mac_key|session)", re.I)
_VALUE_PATTERNS = [
    re.compile(r"(?i)\bbearer\s+[a-z0-9._~+/=-]{8,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)\b(password|secret|token|api[_-]?key)\s*[=:]\s*\S+"),
    re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),  # JWT / capability-token shape
    re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"\b[a-f0-9]{64}\.[A-Za-z0-9_-]{20,}"),
]
MAX_VALUE_CHARS, MAX_DEPTH, MAX_ITEMS = 256, 4, 32
REDACTED = "[REDACTED]"


def redact(value, _depth: int = 0):
    if _depth > MAX_DEPTH:
        return "[DEPTH_LIMIT]"
    if isinstance(value, dict):
        out = {}
        for i, (k, v) in enumerate(value.items()):
            if i >= MAX_ITEMS:
                out["_truncated"] = True
                break
            ks = str(k)[:64]
            out[ks] = REDACTED if SECRET_KEY_PATTERN.search(ks) else redact(v, _depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        items = [redact(v, _depth + 1) for v in list(value)[:MAX_ITEMS]]
        if len(value) > MAX_ITEMS:
            items.append("[TRUNCATED]")
        return items
    if isinstance(value, bool) or value is None or isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if value == value and value not in (float("inf"), float("-inf")) else str(value)
    if isinstance(value, (bytes, bytearray)):
        return f"[bytes:{len(value)}]"
    if isinstance(value, str):
        if any(p.search(value) for p in _VALUE_PATTERNS):
            return REDACTED
        return value[:MAX_VALUE_CHARS]
    return f"[{type(value).__name__}]"
