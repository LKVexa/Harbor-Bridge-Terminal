"""MC-18 - Secret references, redaction, and secret-store integration boundary.

Configuration may only *reference* secrets (``secret://<store>/<path>#<version>``).
Inline values under sensitive keys are refused. Resolution goes through a
``SecretStore`` protocol; when the store is unavailable the plane fails closed
(``SECRET_UNAVAILABLE``) rather than falling back to a default.

Encryption at rest / in transit is delegated to the deployment's KMS and TLS
terminator (see docs/security/ISOLATION_PROFILE.md); this archive ships the
boundary and tests, not a KMS.
"""
from __future__ import annotations

import re
from typing import Any, Mapping, Protocol

from .errors import PlaneError

SECRET_REF = re.compile(r"^secret://([a-z0-9\-]{1,32})/([A-Za-z0-9_./\-]{1,200})#([A-Za-z0-9.\-]{1,32})$")
SENSITIVE_KEY = re.compile(r"(secret|password|passwd|token|api[_-]?key|private[_-]?key|credential)", re.I)
REDACTED = "***REDACTED***"


class SecretStore(Protocol):
    def fetch(self, store: str, path: str, version: str) -> bytes: ...


class InMemorySecretStore:
    """Test/dev store. Production must bind a KMS-backed implementation."""

    def __init__(self, values: Mapping[tuple[str, str, str], bytes] | None = None) -> None:
        self._values = dict(values or {})
        self.available = True

    def fetch(self, store: str, path: str, version: str) -> bytes:
        if not self.available:
            raise ConnectionError("secret store unavailable")
        return self._values[(store, path, version)]


def is_ref(value: Any) -> bool:
    return isinstance(value, str) and SECRET_REF.fullmatch(value) is not None


def check_no_inline_secrets(doc: Any, path: str = "$") -> None:
    """Refuse inline secrets: sensitive keys must hold a ``secret://`` ref."""
    if isinstance(doc, Mapping):
        for k, v in doc.items():
            p = f"{path}.{k}"
            if isinstance(k, str) and SENSITIVE_KEY.search(k) and not isinstance(v, (Mapping, list)):
                if v is not None and not is_ref(v):
                    raise PlaneError("inline secret value refused; use a secret:// reference",
                                     code="SECRET_INLINE", details={"field": p})
            check_no_inline_secrets(v, p)
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            check_no_inline_secrets(v, f"{path}[{i}]")


def resolve_ref(store: SecretStore, ref: str) -> bytes:
    m = SECRET_REF.fullmatch(ref) if isinstance(ref, str) else None
    if m is None:
        raise PlaneError("malformed secret reference", code="CONFIG_INVALID", details={"field": "secret_ref"})
    try:
        return store.fetch(*m.groups())
    except Exception:
        raise PlaneError("secret store unavailable or secret missing", code="SECRET_UNAVAILABLE",
                         details={"ref": f"secret://{m.group(1)}/…#{m.group(3)}"}) from None


def redact(doc: Any) -> Any:
    """Deep-copy ``doc`` with sensitive-key values replaced for logs/traces."""
    if isinstance(doc, Mapping):
        return {k: (REDACTED if isinstance(k, str) and SENSITIVE_KEY.search(k) else redact(v)) for k, v in doc.items()}
    if isinstance(doc, list):
        return [redact(v) for v in doc]
    return doc
