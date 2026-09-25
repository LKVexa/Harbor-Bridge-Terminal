"""Secret references (MC-009 B.5, INV-58-C039; MC-011 ambient authority, INV-58-C043).

Configuration carries only *references* of the form ``secretref://<provider>/<name>``.
Secret material is resolved at activation time through an explicitly injected
provider — the component never reads environment variables, files or the
network on its own.  ``Secret`` objects redact themselves in ``repr``/``str``.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Mapping

SECRET_REF_RE = re.compile(r"^secretref://([a-z][a-z0-9-]{0,31})/([A-Za-z0-9._/-]{1,128})$")
# Heuristics for secret material pasted where a reference belongs.
_SECRETISH = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|"
    r"(?i:password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S+)"
)
REDACTED = "***REDACTED***"


class SecretResolutionError(LookupError):
    pass


@dataclass(frozen=True)
class Secret:
    ref: str
    _value: bytes = field(repr=False)

    def reveal(self) -> bytes:
        return self._value

    def __str__(self) -> str:  # never leak
        return f"Secret({self.ref}, {REDACTED})"

    __repr__ = __str__


def is_secret_ref(value: object) -> bool:
    return isinstance(value, str) and SECRET_REF_RE.fullmatch(value) is not None


def looks_like_secret_material(value: object) -> bool:
    return isinstance(value, str) and _SECRETISH.search(value) is not None


class SecretResolver:
    """Resolve references through explicitly registered providers only."""

    def __init__(self, providers: Mapping[str, Callable[[str], bytes]] | None = None):
        self._providers = dict(providers or {})

    def resolve(self, ref: str) -> Secret:
        m = SECRET_REF_RE.fullmatch(ref) if isinstance(ref, str) else None
        if not m:
            raise SecretResolutionError("malformed secret reference")
        provider = self._providers.get(m.group(1))
        if provider is None:
            raise SecretResolutionError(f"no provider registered for {m.group(1)!r}")
        try:
            value = provider(m.group(2))
        except Exception as exc:  # provider failures never leak content
            raise SecretResolutionError(f"provider {m.group(1)!r} failed: {type(exc).__name__}") from None
        if not isinstance(value, (bytes, bytearray)) or not value:
            raise SecretResolutionError("provider returned no material")
        return Secret(ref, bytes(value))


def redact(obj):
    """Recursively redact secret-looking strings and Secret objects for logs/status."""
    if isinstance(obj, Secret):
        return REDACTED
    if isinstance(obj, str):
        return REDACTED if looks_like_secret_material(obj) else obj
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            sensitive_name = re.search(r"(?i)secret|password|passwd|token|_key$|^key$|private", str(k))
            # Only scalar string values under a sensitive name are redacted; containers
            # recurse (v4.3.0 finding: a dependency named "key" lost its status object).
            if sensitive_name and isinstance(v, (str, bytes)) and not is_secret_ref(v):
                out[k] = REDACTED
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, (list, tuple)):
        return type(obj)(redact(x) for x in obj)
    return obj
