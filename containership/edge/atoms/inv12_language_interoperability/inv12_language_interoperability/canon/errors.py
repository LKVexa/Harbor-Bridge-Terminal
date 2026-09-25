"""MC-014 canonical error envelope and MC-040 diagnostic redaction policy.

Every refusal raised by the ``canon`` package is an :class:`InteropError` that
carries a stable machine-readable ``code``, a field ``path`` (list of path
segments, never payload values), optional source/target language, interface and
type identity, and a retryability flag.  :meth:`InteropError.envelope` returns
the ``PK_INTEROP_ERROR/1`` wire form.

Redaction rule (normative): diagnostics MUST NOT contain payload values,
secrets, or attacker-controlled strings longer than :data:`MAX_DETAIL_CHARS`.
Path segments that are record field / case names come from the *schema*, not the
payload, and are therefore safe; list indexes are integers.  Free-text detail is
passed through :func:`redact` which truncates and strips control characters.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

ENVELOPE_SCHEMA = "PK_INTEROP_ERROR/1"
MAX_DETAIL_CHARS = 160
MAX_PATH_SEGMENTS = 32
_CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")

# Stable error-code registry.  Codes are append-only; never renumber/rename.
ERROR_CODES = {
    "PK_INTEROP_SCHEMA_SYNTAX": (False, "schema text does not match the grammar"),
    "PK_INTEROP_SCHEMA_DUPLICATE": (False, "duplicate or ambiguous declaration"),
    "PK_INTEROP_SCHEMA_UNRESOLVED": (False, "reference to an undeclared type"),
    "PK_INTEROP_SCHEMA_RECURSIVE": (False, "illegal recursive type definition"),
    "PK_INTEROP_SCHEMA_LIMIT": (False, "schema exceeds a structural limit"),
    "PK_INTEROP_TYPE_MISMATCH": (False, "value does not match the declared type"),
    "PK_INTEROP_OUT_OF_RANGE": (False, "numeric value outside the declared range"),
    "PK_INTEROP_LOSSY_CONVERSION": (False, "conversion would lose information"),
    "PK_INTEROP_ENCODING": (False, "invalid Unicode / UTF-8 sequence"),
    "PK_INTEROP_UNREPRESENTABLE": (False, "target language cannot represent the type exactly"),
    "PK_INTEROP_INVALID_DISCRIMINANT": (False, "variant/enum discriminant is out of range"),
    "PK_INTEROP_INVALID_FLAGS": (False, "flags value sets undeclared bits"),
    "PK_INTEROP_MEMORY_BOUNDS": (False, "guest memory access out of bounds"),
    "PK_INTEROP_MEMORY_ALIGNMENT": (False, "guest memory access misaligned"),
    "PK_INTEROP_MEMORY_OVERFLOW": (False, "size/offset arithmetic overflowed"),
    "PK_INTEROP_REALLOC": (False, "guest allocator returned an invalid region"),
    "PK_INTEROP_LIFECYCLE": (False, "allocation/post-return lifecycle violation"),
    "PK_INTEROP_OWNERSHIP": (False, "owned value/resource used after transfer"),
    "PK_INTEROP_HANDLE": (False, "invalid, stale or foreign resource handle"),
    "PK_INTEROP_BORROW": (False, "borrow used outside its scope or still outstanding"),
    "PK_INTEROP_LIMIT": (True, "a resource limit or quota was exceeded"),
    "PK_INTEROP_VERSION": (False, "no mutually supported version"),
    "PK_INTEROP_INCOMPATIBLE": (False, "breaking schema change"),
    "PK_INTEROP_ASYNC": (False, "illegal future/stream state transition"),
    "PK_INTEROP_CANCELLED": (True, "operation was cancelled"),
    "PK_INTEROP_CONFIG": (False, "configuration failed validation"),
    "PK_INTEROP_PROVENANCE": (False, "artifact digest/signature/approval verification failed"),
    "PK_INTEROP_UNAUTHORIZED": (False, "caller lacks the required capability"),
    "PK_INTEROP_TRUST_UNAVAILABLE": (True, "a trust dependency is unavailable; failing closed"),
    "PK_INTEROP_CANONICALIZATION": (False, "value cannot be canonicalized safely"),
}


def redact(text: object) -> str:
    """Return a bounded, control-free diagnostic string (never raises)."""
    s = text if isinstance(text, str) else type(text).__name__
    s = _CONTROL.sub("?", s.encode("utf-8", "replace").decode("utf-8", "replace"))
    if len(s) > MAX_DETAIL_CHARS:
        s = s[: MAX_DETAIL_CHARS - 1] + "…"
    return s


def _safe_path(path: Iterable[Any]) -> list:
    out = []
    for seg in list(path)[:MAX_PATH_SEGMENTS]:
        out.append(seg if type(seg) is int else redact(str(seg)))
    return out


class InteropError(Exception):
    """Base class of every structured INV-12 refusal."""

    code = "PK_INTEROP_CANONICALIZATION"

    def __init__(self, detail: str = "", *, code: str | None = None, path=(),
                 source_language: str | None = None, target_language: str | None = None,
                 interface: str | None = None, type_id: str | None = None,
                 retryable: bool | None = None):
        if code is not None:
            if code not in ERROR_CODES:
                raise KeyError(f"unregistered error code {code!r}")
            self.code = code
        self.detail = redact(detail or ERROR_CODES.get(self.code, (False, ""))[1])
        self.path = _safe_path(path)
        self.source_language = source_language
        self.target_language = target_language
        self.interface = interface
        self.type_id = type_id
        self.retryable = ERROR_CODES.get(self.code, (False, ""))[0] if retryable is None else bool(retryable)
        super().__init__(self.detail)

    def at(self, *segments) -> "InteropError":
        """Prefix path segments (used while unwinding recursive validation)."""
        self.path = _safe_path(list(segments) + self.path)
        return self

    def envelope(self) -> dict:
        return {
            "schema": ENVELOPE_SCHEMA,
            "code": self.code,
            "path": list(self.path),
            "source_language": self.source_language,
            "target_language": self.target_language,
            "interface": self.interface,
            "type_id": self.type_id,
            "retryable": self.retryable,
            "detail": self.detail,
        }

    def __str__(self) -> str:
        where = "/" + "/".join(str(p) for p in self.path) if self.path else ""
        return f"{self.code}{' at ' + where if where else ''}: {self.detail}"


class SchemaError(InteropError):
    code = "PK_INTEROP_SCHEMA_SYNTAX"


class ValidationError(InteropError):
    code = "PK_INTEROP_TYPE_MISMATCH"


class MemoryError_(InteropError):
    code = "PK_INTEROP_MEMORY_BOUNDS"


class LifecycleError(InteropError):
    code = "PK_INTEROP_LIFECYCLE"


class HandleError(InteropError):
    code = "PK_INTEROP_HANDLE"


class LimitError(InteropError):
    code = "PK_INTEROP_LIMIT"


class VersionError(InteropError):
    code = "PK_INTEROP_VERSION"


class ConfigError(InteropError):
    code = "PK_INTEROP_CONFIG"


class ProvenanceError(InteropError):
    code = "PK_INTEROP_PROVENANCE"


class AuthError(InteropError):
    code = "PK_INTEROP_UNAUTHORIZED"


class AsyncError(InteropError):
    code = "PK_INTEROP_ASYNC"


def validate_envelope(env: object) -> None:
    """Validate a ``PK_INTEROP_ERROR/1`` envelope received from another party."""
    keys = {"schema", "code", "path", "source_language", "target_language",
            "interface", "type_id", "retryable", "detail"}
    if type(env) is not dict or set(env) != keys:
        raise ValueError("malformed error envelope")
    if env["schema"] != ENVELOPE_SCHEMA or env["code"] not in ERROR_CODES:
        raise ValueError("unknown envelope schema or code")
    if type(env["path"]) is not list or len(env["path"]) > MAX_PATH_SEGMENTS:
        raise ValueError("malformed envelope path")
    if type(env["retryable"]) is not bool or type(env["detail"]) is not str \
            or len(env["detail"]) > MAX_DETAIL_CHARS:
        raise ValueError("malformed envelope detail/retryable")
