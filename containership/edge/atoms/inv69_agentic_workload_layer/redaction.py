"""Field-level redaction and input bounds shared by errors, status, telemetry and explain (C026, C033, C079, C085)."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
import re

SECRET_FRAGMENTS = (
    "authorization", "credential", "passwd", "password", "secret", "token",
    "api_key", "apikey", "private_key", "cookie", "session", "prompt",
)
# Bearer tokens / long hex / key-like material inside string values.
_VALUE_PATTERNS = [
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)\b(sk|pk|rk|ghp|gho|xox[abpr])[-_][a-z0-9_-]{12,}"),
    re.compile(r"(?i)\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]
_VALUE_RE = re.compile("|".join(f"(?:{p.pattern.replace('(?i)', '')})" for p in _VALUE_PATTERNS), re.IGNORECASE)
REDACTED = "<redacted>"

MAX_DEPTH = 32
MAX_ITEMS = 4096
MAX_STR = 1 << 20


class InputTooLarge(ValueError):
    pass


_KEY_RE = re.compile("|".join(re.escape(f) for f in SECRET_FRAGMENTS), re.IGNORECASE)


def is_secret_key(name: str) -> bool:
    return _KEY_RE.search(str(name)) is not None


def safe_key(name: Any) -> str:
    """Field *names* are untrusted too: a secret used as a key must not be echoed."""
    text = str(name)
    if _VALUE_RE.search(text):
        return "<redacted-key>"
    return text if len(text) <= 64 else text[:64] + "<truncated>"


def redact(value: Any, _depth: int = 0) -> Any:
    """Return a copy with secret-named fields and secret-looking strings replaced."""
    if _depth > MAX_DEPTH:
        return "<truncated:depth>"
    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        for k, v in list(value.items())[:256]:
            key = safe_key(k)
            if key in out:
                key = f"{key}#{len(out)}"
            out[key] = REDACTED if (is_secret_key(k) or key.startswith("<redacted-key>")) else redact(v, _depth + 1)
        return out
    if isinstance(value, (list, tuple)):
        return [redact(v, _depth + 1) for v in list(value)[:256]]
    if isinstance(value, str):
        if _VALUE_RE.search(value):
            return REDACTED
        return value if len(value) <= 512 else value[:512] + "<truncated>"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return f"<{type(value).__name__}>"


def check_bounds(value: Any) -> None:
    """Iterative (non-recursive) depth/size/count guard run BEFORE any recursive processing."""
    stack = [(value, 0)]
    seen: set[int] = set()
    count = 0
    while stack:
        v, d = stack.pop()
        count += 1
        if count > MAX_ITEMS:
            raise InputTooLarge("item count limit exceeded")
        if d > MAX_DEPTH:
            raise InputTooLarge("nesting depth limit exceeded")
        if isinstance(v, (str, bytes)) and len(v) > MAX_STR:
            raise InputTooLarge("string/bytes length limit exceeded")
        if isinstance(v, Mapping):
            if id(v) in seen:
                continue
            seen.add(id(v))
            for k, x in v.items():
                stack.append((k, d + 1))
                stack.append((x, d + 1))
        elif isinstance(v, (list, tuple, set, frozenset)):
            if id(v) in seen:
                continue
            seen.add(id(v))
            for x in v:
                stack.append((x, d + 1))
