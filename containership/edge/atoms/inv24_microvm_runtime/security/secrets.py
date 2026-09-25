"""Secret separation and redaction (MC-016, MC-043).

Secrets are only ever obtained through a ``SecretRef`` resolved by a provider
at use time; configuration files may hold references (``secret://name``) but
never values.  ``redact`` scrubs mappings/strings before they reach logs,
audit, diagnostics or evidence; ``scan_for_secrets`` is a CI/diagnostic check.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from ..errors import Inv24Error

SENSITIVE_KEYS: Final[re.Pattern] = re.compile(
    r"(^|[_-])(pass(word)?|passphrase|secret|token|api[_-]?key|private[_-]?key|credentials?|cookie|session|mac|signature|authorization)($|[_-])", re.I)
SECRET_VALUE_PATTERNS: Final[tuple[re.Pattern, ...]] = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}"),
    re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"[A-Za-z0-9_-]{20,}\.[a-z0-9-]{1,32}\.[0-9a-f]{64}"),  # INV-24 capability token
)
REDACTED: Final[str] = "[REDACTED]"
MAX_DEPTH = 8
MAX_STR = 1024


@dataclass(frozen=True, slots=True)
class SecretRef:
    name: str

    @classmethod
    def parse(cls, text: str) -> "SecretRef":
        if not isinstance(text, str) or not re.fullmatch(r"secret://[a-z0-9][a-z0-9_.-]{0,63}", text):
            raise Inv24Error("CONFIG_REJECTED", "secret references must look like secret://name")
        return cls(text[len("secret://"):])

    def __repr__(self) -> str:
        return f"SecretRef({self.name!r})"


def _scrub_str(s: str) -> str:
    for pat in SECRET_VALUE_PATTERNS:
        s = pat.sub(REDACTED, s)
    return s if len(s) <= MAX_STR else s[:MAX_STR] + "...[truncated]"


def redact(value: object, _depth: int = 0) -> object:
    if _depth > MAX_DEPTH:
        return "[depth-limit]"
    if isinstance(value, dict):
        return {str(k)[:64]: (REDACTED if SENSITIVE_KEYS.search(str(k)) else redact(v, _depth + 1))
                for k, v in list(value.items())[:64]}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [redact(v, _depth + 1) for v in list(value)[:64]]
    if isinstance(value, str):
        return _scrub_str(value)
    if isinstance(value, (bytes, bytearray)):
        return f"[{len(value)} bytes]"
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _scrub_str(repr(value))


def scan_for_secrets(text: str) -> list[str]:
    return [p.pattern for p in SECRET_VALUE_PATTERNS if p.search(text)]


def forbid_inline_secrets(config: dict, path: str = "") -> None:
    """Reject configuration that embeds a secret value instead of a SecretRef."""
    for k, v in config.items():
        here = f"{path}.{k}" if path else str(k)
        if isinstance(v, dict):
            forbid_inline_secrets(v, here)
        elif SENSITIVE_KEYS.search(str(k)) and not (isinstance(v, str) and v.startswith("secret://")):
            raise Inv24Error("CONFIG_REJECTED", f"{here}: sensitive field must be a secret:// reference")
        elif isinstance(v, str) and scan_for_secrets(v):
            raise Inv24Error("CONFIG_REJECTED", f"{here}: value looks like an embedded secret")
