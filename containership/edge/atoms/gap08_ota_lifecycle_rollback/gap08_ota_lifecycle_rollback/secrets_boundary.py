"""Secrets/key handling boundary (checklist component 27).

Rules enforced here:
* secrets are referenced, never embedded: persisted/logged structures may hold a
  ``SecretRef`` (``{"secret_ref": "vault://..."}``) but never raw material;
* anything written to the state store, audit sink, logs or explain output passes
  through ``assert_no_secrets`` (fail closed) or ``redact`` (for human output);
* rotation is tracked by reference version so a rotated credential never
  requires rewriting rollout state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from .errors import ValidationFailed

_SENSITIVE_KEY = re.compile(
    r"(pass(word|phrase)?|secret|token|private[_-]?key|credential|api[_-]?key|bearer|session[_-]?key|hmac[_-]?key)",
    re.IGNORECASE,
)
# Values that look like PEM blocks or long high-entropy bearer tokens.
_SENSITIVE_VALUE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|^eyJ[A-Za-z0-9_-]{20,}\.")
REDACTED = "***REDACTED***"


@dataclass(frozen=True)
class SecretRef:
    uri: str          # e.g. vault://ota/controller/mtls#v3
    version: str = "1"

    def to_dict(self) -> dict[str, str]:
        return {"secret_ref": self.uri, "version": self.version}


def _is_ref(value: Any) -> bool:
    return isinstance(value, dict) and set(value) <= {"secret_ref", "version"} and "secret_ref" in value


def find_secrets(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for k, v in value.items():
            p = f"{path}.{k}"
            if _is_ref(v):
                continue
            if isinstance(k, str) and _SENSITIVE_KEY.search(k) and v not in (None, "", REDACTED) \
                    and not isinstance(v, (bool, int, float)):
                hits.append(p)
            else:
                hits.extend(find_secrets(v, p))
    elif isinstance(value, (list, tuple)):
        for i, v in enumerate(value):
            hits.extend(find_secrets(v, f"{path}[{i}]"))
    elif isinstance(value, str) and _SENSITIVE_VALUE.search(value):
        hits.append(path)
    return hits


def assert_no_secrets(value: Any, *, where: str) -> None:
    hits = find_secrets(value)
    if hits:
        raise ValidationFailed(f"secret material may not be persisted to {where}: {hits[:5]}", resource=where)


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if _is_ref(v):
                out[k] = v
            elif isinstance(k, str) and _SENSITIVE_KEY.search(k) and not isinstance(v, (bool, int, float, type(None))):
                out[k] = REDACTED
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact(v) for v in value)
    if isinstance(value, str) and _SENSITIVE_VALUE.search(value):
        return REDACTED
    return value
