"""Shared structured-error base for the v4.3.0 production components.

Every refusal raised by a v4.3.0 component is a ``PK_POLL_ERROR/1`` payload with a
stable code, bounded safe details, the deprecation marker and the migration target
(checklist items xx.21).  Callers branch on ``code``; message prose is advisory.
"""
from __future__ import annotations

try:
    from .polling import _StructuredPollError, ERROR_SCHEMA, MIGRATION_TARGET
except ImportError:  # flat import from tests/tools
    from polling import _StructuredPollError, ERROR_SCHEMA, MIGRATION_TARGET

MAX_DETAIL_VALUE_CHARS = 256
MAX_DETAIL_KEYS = 16


def _bound(details: dict | None) -> dict:
    out = {}
    for i, (k, v) in enumerate(dict(details or {}).items()):
        if i >= MAX_DETAIL_KEYS:
            out["_truncated"] = True
            break
        if isinstance(v, (int, float, bool)) or v is None:
            out[str(k)[:64]] = v
        else:
            out[str(k)[:64]] = str(v)[:MAX_DETAIL_VALUE_CHARS]
    return out


class Inv14Error(_StructuredPollError, RuntimeError):
    default_code = "PK_POLL_ERROR"

    def __init__(self, message: str, *, code: str | None = None, details: dict | None = None):
        super().__init__(message[:512], code=code, details=_bound(details))


__all__ = ["Inv14Error", "ERROR_SCHEMA", "MIGRATION_TARGET"]
