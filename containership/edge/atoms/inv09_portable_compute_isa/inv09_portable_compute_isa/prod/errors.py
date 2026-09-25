"""M12 - structured failure schema (PK_VALIDATION_FAILURE/1).

Every refusal leaving the validation boundary is a :class:`InvalidModule`
carrying a stable machine code, a byte offset, section context and a bounded,
sanitised detail string.  Unexpected implementation exceptions are converted
to ``INTERNAL_ERROR`` by :func:`boundary` - which is itself a refusal, never an
accept (fail closed).
"""
from __future__ import annotations

import enum
import functools
from typing import Any, Callable, TypeVar

SCHEMA = "PK_VALIDATION_FAILURE/1"
MAX_DETAIL_CHARS = 240


class Code(str, enum.Enum):
    # M01 structural
    BAD_MAGIC = "BAD_MAGIC"
    BAD_VERSION = "BAD_VERSION"
    TRUNCATED = "TRUNCATED"
    BAD_LEB128 = "BAD_LEB128"
    BAD_UTF8 = "BAD_UTF8"
    SECTION_ORDER = "SECTION_ORDER"
    DUPLICATE_SECTION = "DUPLICATE_SECTION"
    UNKNOWN_SECTION = "UNKNOWN_SECTION"
    SECTION_SIZE_MISMATCH = "SECTION_SIZE_MISMATCH"
    MALFORMED = "MALFORMED"
    COUNT_MISMATCH = "COUNT_MISMATCH"
    INVALID_INDEX = "INVALID_INDEX"
    INVALID_LIMITS = "INVALID_LIMITS"
    DUPLICATE_EXPORT = "DUPLICATE_EXPORT"
    # M02 typing
    TYPE_MISMATCH = "TYPE_MISMATCH"
    STACK_UNDERFLOW = "STACK_UNDERFLOW"
    INVALID_BRANCH = "INVALID_BRANCH"
    INVALID_CONST_EXPR = "INVALID_CONST_EXPR"
    INVALID_ALIGNMENT = "INVALID_ALIGNMENT"
    UNKNOWN_OPCODE = "UNKNOWN_OPCODE"
    UNSUPPORTED_PROPOSAL = "UNSUPPORTED_PROPOSAL"
    UNDECLARED_FUNC_REF = "UNDECLARED_FUNC_REF"
    IMMUTABLE_GLOBAL = "IMMUTABLE_GLOBAL"
    # M13 governor
    LIMIT_EXCEEDED = "LIMIT_EXCEEDED"
    DEADLINE_EXCEEDED = "DEADLINE_EXCEEDED"
    # policy / binding / admission
    FEATURE_REFUSED = "FEATURE_REFUSED"
    BINDING_MISMATCH = "BINDING_MISMATCH"
    ENGINE_UNSUPPORTED = "ENGINE_UNSUPPORTED"
    REGISTRY_INVALID = "REGISTRY_INVALID"
    ATTESTATION_INVALID = "ATTESTATION_INVALID"
    DIGEST_MISMATCH = "DIGEST_MISMATCH"
    STALE_CONFIGURATION = "STALE_CONFIGURATION"
    HOST_IMPORT_REFUSED = "HOST_IMPORT_REFUSED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


#: codes that indicate the module itself is invalid (deterministic, cacheable)
DETERMINISTIC_REJECTS = frozenset(Code) - {
    Code.DEADLINE_EXCEEDED, Code.INTERNAL_ERROR, Code.REGISTRY_INVALID,
    Code.ATTESTATION_INVALID, Code.STALE_CONFIGURATION, Code.DIGEST_MISMATCH,
}


def sanitize(text: object, limit: int = MAX_DETAIL_CHARS) -> str:
    """Bounded, log-injection-safe rendering of attacker-influenced text."""
    s = str(text)
    out = []
    for ch in s:
        o = ord(ch)
        if o < 0x20 or o == 0x7F or 0x80 <= o < 0xA0 or ch in "  ":
            out.append("\\x%02x" % o if o < 0x100 else "\\u%04x" % o)
        else:
            out.append(ch)
        if len(out) >= limit:
            out.append("...")
            break
    return "".join(out)


class InvalidModule(Exception):
    """A structured, fail-closed refusal."""

    def __init__(self, code: Code, detail: str = "", *, offset: int | None = None,
                 section: str | None = None):
        self.code = Code(code)
        self.detail = sanitize(detail)
        self.offset = offset
        self.section = section
        super().__init__(f"{self.code.value}@{offset}[{section}]: {self.detail}")

    @property
    def deterministic(self) -> bool:
        return self.code in DETERMINISTIC_REJECTS

    def to_dict(self) -> dict[str, Any]:
        return {"schema": SCHEMA, "code": self.code.value, "offset": self.offset,
                "section": self.section, "detail": self.detail,
                "deterministic": self.deterministic}


F = TypeVar("F", bound=Callable[..., Any])


def boundary(fn: F) -> F:
    """Convert any non-structured exception at a component boundary into
    ``INTERNAL_ERROR``.  ``InvalidModule`` passes through unchanged."""
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        try:
            return fn(*a, **kw)
        except InvalidModule:
            raise
        except RecursionError as exc:
            raise InvalidModule(Code.LIMIT_EXCEEDED, "recursion limit") from exc
        except MemoryError as exc:
            raise InvalidModule(Code.LIMIT_EXCEEDED, "memory exhausted") from exc
        except Exception as exc:  # noqa: BLE001 - deliberate fail-closed boundary
            raise InvalidModule(Code.INTERNAL_ERROR, type(exc).__name__) from exc
    return wrapper  # type: ignore[return-value]
