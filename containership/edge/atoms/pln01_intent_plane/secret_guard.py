"""Secret exclusion, data classification, and diagnostic redaction (MC-018).

The intent plane never owns secret material.  Declarations are scanned before
admission; a field whose *name* or *value* looks like raw secret material is
refused with ``PLN01-E0017``.  References to secrets (``secret_ref`` pointing at
an external store, e.g. ``vault://...``) are allowed.  All diagnostics pass
through :func:`redact_text` / :func:`redact_value`.
"""
from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from .errors import SecretDetectedError

CLASSIFICATIONS = ("public", "internal", "confidential", "restricted-secret")

SECRET_KEY_RE = re.compile(
    r"(pass(word|wd)?|secret|token|api[_-]?key|private[_-]?key|credential|client[_-]?secret|"
    r"access[_-]?key|session[_-]?key|bearer|auth[_-]?header)$",
    re.IGNORECASE,
)
ALLOWED_REF_KEY_RE = re.compile(r"(_ref|_reference|_uri)$", re.IGNORECASE)
SECRET_REF_VALUE_RE = re.compile(r"^(vault|kms|secretsmanager|sm|keyvault|k8s-secret)://", re.IGNORECASE)
SECRET_VALUE_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),                     # AWS access key id
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b"),           # GitHub tokens
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}\b"),         # Slack tokens
    re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"),  # JWT
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"(?i)\b(password|passwd|secret|token)\s*[=:]\s*\S{4,}"),
]
REDACTED = "[REDACTED]"


def _walk(value: Any, path: str):
    if isinstance(value, Mapping):
        for k, v in value.items():
            yield from _walk(v, f"{path}.{k}" if path else str(k))
            yield (path, str(k), v)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for i, v in enumerate(value):
            yield from _walk(v, f"{path}[{i}]")


def find_secrets(spec: Any) -> list[str]:
    """Return paths (never values) of fields that look like raw secrets."""
    hits: list[str] = []
    for parent, key, val in _walk(spec, ""):
        field = f"{parent}.{key}" if parent else key
        if SECRET_KEY_RE.search(key) and not ALLOWED_REF_KEY_RE.search(key):
            if not (isinstance(val, str) and SECRET_REF_VALUE_RE.match(val)):
                hits.append(field)
                continue
        if isinstance(val, str) and any(p.search(val) for p in SECRET_VALUE_PATTERNS):
            hits.append(field)
    return sorted(set(hits))


def reject_secrets(spec: Any) -> None:
    hits = find_secrets(spec)
    if hits:
        raise SecretDetectedError(f"raw secret material refused at fields: {', '.join(hits)}", fields=hits)


def redact_text(text: str) -> str:
    out = text
    for pattern in SECRET_VALUE_PATTERNS:
        out = pattern.sub(REDACTED, out)
    return out


def redact_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {k: (REDACTED if SECRET_KEY_RE.search(str(k)) and not ALLOWED_REF_KEY_RE.search(str(k))
                    else redact_value(v)) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact_value(v) for v in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def classify(spec: Mapping[str, Any]) -> str:
    """Classify a declaration. Explicit ``classification`` wins if valid."""
    declared = spec.get("classification") if isinstance(spec, Mapping) else None
    if declared in CLASSIFICATIONS:
        return declared
    return "internal"
