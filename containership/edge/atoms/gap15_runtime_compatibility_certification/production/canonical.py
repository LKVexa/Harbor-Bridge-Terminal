"""Canonical encoding, bounded parsing and digests (MC-02-06, MC-09-04, MC-32-06).

One canonical form is used everywhere a byte string is signed, hashed or
compared: UTF-8 JSON with sorted keys, no insignificant whitespace, no floats,
NFC-normalised strings and no duplicate keys. Parsing untrusted input is
bounded in size, nesting depth and collection cardinality and fails closed
with stable error codes.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

MAX_PAYLOAD_BYTES = 256 * 1024
MAX_DEPTH = 16
MAX_COLLECTION = 4096
MAX_STRING = 8192
MAX_INT = 2**63 - 1


class CanonicalError(ValueError):
    """Raised with a stable machine-readable ``code``."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def _reject_constant(token: str) -> Any:
    raise CanonicalError("E_NON_FINITE", f"non-finite number {token!r} is not allowed")


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    seen: dict[str, Any] = {}
    for key, value in pairs:
        if key in seen:
            raise CanonicalError("E_DUPLICATE_KEY", f"duplicate key {key[:64]!r}")
        seen[key] = value
    return seen


def _reject_float(token: str) -> Any:
    raise CanonicalError("E_FLOAT", "floating point numbers are not permitted in canonical payloads")


def _check(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise CanonicalError("E_DEPTH", f"nesting deeper than {MAX_DEPTH}")
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        if abs(value) > MAX_INT:
            raise CanonicalError("E_INT_RANGE", "integer outside signed 64-bit range")
        return
    if isinstance(value, float):
        raise CanonicalError("E_FLOAT", "floating point numbers are not permitted")
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise CanonicalError("E_STRING_LENGTH", f"string longer than {MAX_STRING}")
        if unicodedata.normalize("NFC", value) != value:
            raise CanonicalError("E_UNICODE_NFC", "string is not NFC-normalised")
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in value):
            raise CanonicalError("E_UNICODE_SURROGATE", "lone surrogate in string")
        return
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_COLLECTION:
            raise CanonicalError("E_COLLECTION_SIZE", f"array larger than {MAX_COLLECTION}")
        for item in value:
            _check(item, depth + 1)
        return
    if isinstance(value, dict):
        if len(value) > MAX_COLLECTION:
            raise CanonicalError("E_COLLECTION_SIZE", f"object larger than {MAX_COLLECTION}")
        for key, item in value.items():
            if not isinstance(key, str):
                raise CanonicalError("E_KEY_TYPE", "object keys must be strings")
            _check(key, depth + 1)
            _check(item, depth + 1)
        return
    raise CanonicalError("E_TYPE", f"unsupported type {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    """Return the one canonical byte encoding of ``value`` (validated first)."""
    _check(value)
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def parse(raw: bytes | str, *, max_bytes: int = MAX_PAYLOAD_BYTES, require_canonical: bool = False) -> Any:
    """Parse untrusted JSON under size/depth/cardinality/number bounds."""
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(raw, (bytes, bytearray)):
        raise CanonicalError("E_TYPE", "payload must be bytes")
    if len(raw) > max_bytes:
        raise CanonicalError("E_PAYLOAD_TOO_LARGE", f"{len(raw)} bytes exceeds {max_bytes}")
    # Cheap structural pre-scan so deeply nested input cannot hit the recursion limit.
    depth = 0
    in_string = escaped = False
    for byte in raw:
        if in_string:
            if escaped:
                escaped = False
            elif byte == 0x5C:
                escaped = True
            elif byte == 0x22:
                in_string = False
            continue
        if byte == 0x22:
            in_string = True
        elif byte in (0x5B, 0x7B):
            depth += 1
            if depth > MAX_DEPTH:
                raise CanonicalError("E_DEPTH", f"nesting deeper than {MAX_DEPTH}")
        elif byte in (0x5D, 0x7D):
            depth -= 1
    try:
        text = bytes(raw).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CanonicalError("E_ENCODING", "payload is not valid UTF-8") from exc
    try:
        value = json.loads(
            text,
            object_pairs_hook=_no_duplicates,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except CanonicalError:
        raise
    except (ValueError, RecursionError) as exc:
        raise CanonicalError("E_MALFORMED", "payload is not well-formed JSON") from exc
    _check(value)
    if require_canonical and canonical_bytes(value) != bytes(raw):
        raise CanonicalError("E_NON_CANONICAL", "payload bytes are not in canonical form")
    return value


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    """``sha256:<hex>`` over the canonical encoding."""
    return "sha256:" + sha256_hex(canonical_bytes(value))
