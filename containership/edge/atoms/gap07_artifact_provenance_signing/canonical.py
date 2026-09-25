"""Bounded strict parsing and canonical encodings shared by every v6 envelope.

* ``strict_loads`` - JSON parse that rejects duplicate keys, floats/NaN/Infinity,
  lone surrogates, excessive depth, oversized documents/arrays/maps/strings.
* ``canonical_bytes`` - RFC 8785 (JCS) encoding restricted to the strict value
  space (no floats; integers within +/-(2^53-1) so JCS number serialisation is
  exact): keys sorted by UTF-16 code units, no whitespace, UTF-8, minimal
  string escaping.
* ``ld_encode`` - domain-separated, length-delimited field encoding used for the
  bytes that are actually signed.  Each field is ``u32be(len(name)) name
  u64be(len(value)) value`` after an ASCII domain tag, so no concatenation of
  distinct field tuples can collide.
* ``b64u_encode`` / ``b64u_decode`` - strict unpadded base64url; any
  non-canonical encoding (padding, stray bits, wrong alphabet) is rejected.
"""
from __future__ import annotations

import base64
import binascii
import json
import re
import struct
from typing import Any, Iterable, Mapping

from .errors import fail

MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
MAX_DEPTH = 32
MAX_COLLECTION = 10_000
MAX_STRING = 1 * 1024 * 1024
MAX_SAFE_INT = 2**53 - 1
_B64U = re.compile(r"^[A-Za-z0-9_-]*$")


def _reject_constant(value: str) -> Any:
    raise fail("ENVELOPE_MALFORMED", f"non-finite number {value} not allowed")


def _reject_float(value: str) -> Any:
    raise fail("ENVELOPE_MALFORMED", "floating point numbers are not allowed in signed documents")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if len(pairs) > MAX_COLLECTION:
        raise fail("INPUT_TOO_LARGE", "object has too many members", limit=MAX_COLLECTION)
    for key, value in pairs:
        if key in out:
            raise fail("ENVELOPE_MALFORMED", "duplicate JSON key", key=key[:64])
        out[key] = value
    return out


def _check(value: Any, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise fail("INPUT_TOO_LARGE", "document nesting too deep", limit=MAX_DEPTH)
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            raise fail("INPUT_TOO_LARGE", "string too long", limit=MAX_STRING)
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise fail("ENVELOPE_MALFORMED", "string contains lone surrogate") from exc
    elif isinstance(value, dict):
        if len(value) > MAX_COLLECTION:
            raise fail("INPUT_TOO_LARGE", "object has too many members", limit=MAX_COLLECTION)
        for k, v in value.items():
            _check(k, depth + 1)
            _check(v, depth + 1)
    elif isinstance(value, list):
        if len(value) > MAX_COLLECTION:
            raise fail("INPUT_TOO_LARGE", "array has too many items", limit=MAX_COLLECTION)
        for v in value:
            _check(v, depth + 1)
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, int):
        if abs(value) > MAX_SAFE_INT:
            raise fail("ENVELOPE_MALFORMED", "integer outside the I-JSON safe range (+/-(2^53-1))")
    else:
        raise fail("ENVELOPE_MALFORMED", f"unsupported JSON value type {type(value).__name__}")


def strict_loads(data: bytes | str, *, max_bytes: int = MAX_DOCUMENT_BYTES) -> Any:
    """Parse JSON with every ambiguity rejected before semantic evaluation."""
    if isinstance(data, str):
        raw = data.encode("utf-8", "surrogatepass")
    elif isinstance(data, (bytes, bytearray, memoryview)):
        raw = bytes(data)
    else:
        raise fail("ENVELOPE_MALFORMED", "document must be bytes or str")
    if len(raw) > max_bytes:
        raise fail("INPUT_TOO_LARGE", "document exceeds size bound", limit=max_bytes, size=len(raw))
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeDecodeError as exc:
        raise fail("ENVELOPE_MALFORMED", "document is not valid UTF-8") from exc
    if text.startswith("﻿"):
        raise fail("ENVELOPE_MALFORMED", "byte-order mark not allowed")
    # cheap depth pre-scan so the recursive decoder cannot be driven deep
    depth = peak = 0
    in_str = esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
        elif ch == '"':
            in_str = True
        elif ch in "[{":
            depth += 1
            peak = max(peak, depth)
            if peak > MAX_DEPTH:
                raise fail("INPUT_TOO_LARGE", "document nesting too deep", limit=MAX_DEPTH)
        elif ch in "]}":
            depth -= 1
    try:
        value = json.loads(
            text,
            object_pairs_hook=_pairs,
            parse_constant=_reject_constant,
            parse_float=_reject_float,
        )
    except (ValueError, RecursionError) as exc:
        if hasattr(exc, "code"):
            raise
        raise fail("ENVELOPE_MALFORMED", "document is not valid JSON") from exc
    _check(value, 0)
    return value


def _jcs(value: Any, out: list[str]) -> None:
    if isinstance(value, dict):
        out.append("{")
        for i, k in enumerate(sorted(value, key=lambda k: k.encode("utf-16-be"))):
            if i:
                out.append(",")
            out.append(json.dumps(k, ensure_ascii=False))
            out.append(":")
            _jcs(value[k], out)
        out.append("}")
    elif isinstance(value, list):
        out.append("[")
        for i, v in enumerate(value):
            if i:
                out.append(",")
            _jcs(v, out)
        out.append("]")
    else:
        out.append(json.dumps(value, ensure_ascii=False, allow_nan=False))


def canonical_bytes(value: Any) -> bytes:
    """RFC 8785 (JCS) bytes for the strict value space; refuses anything outside it."""
    _check(value, 0)
    out: list[str] = []
    _jcs(value, out)
    return "".join(out).encode("utf-8")


def is_canonical(raw: bytes) -> bool:
    try:
        return canonical_bytes(strict_loads(raw)) == bytes(raw)
    except Exception:  # noqa: BLE001 - any failure means "not canonical"
        return False


def ld_encode(domain: str, fields: Iterable[tuple[str, bytes | str | int | None]]) -> bytes:
    """Domain-separated length-delimited encoding for signed messages."""
    if not domain.isascii() or "\x00" in domain:
        raise ValueError("domain tag must be ASCII without NUL")
    out = [b"GAP07\x00", domain.encode("ascii"), b"\x00"]
    for name, value in fields:
        nb = name.encode("utf-8")
        if value is None:
            vb = b""
            marker = b"\x00"
        elif isinstance(value, bool):
            raise TypeError("bool is not a signed field type")
        elif isinstance(value, int):
            vb = str(value).encode("ascii")
            marker = b"\x02"
        elif isinstance(value, str):
            vb = value.encode("utf-8")
            marker = b"\x01"
        else:
            vb = bytes(value)
            marker = b"\x03"
        out.append(struct.pack(">I", len(nb)) + nb + marker + struct.pack(">Q", len(vb)) + vb)
    return b"".join(out)


def b64u_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64u_decode(text: str, *, max_len: int = 16384) -> bytes:
    if not isinstance(text, str) or len(text) > max_len or _B64U.fullmatch(text) is None or len(text) % 4 == 1:
        raise fail("ENVELOPE_MALFORMED", "invalid base64url encoding")
    try:
        raw = base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))
    except (binascii.Error, ValueError) as exc:
        raise fail("ENVELOPE_MALFORMED", "invalid base64url encoding") from exc
    if b64u_encode(raw) != text:  # stray low bits => non-canonical
        raise fail("ENVELOPE_MALFORMED", "non-canonical base64url encoding")
    return raw


def b64_std_decode(text: str, *, max_len: int = 8 * 1024 * 1024) -> bytes:
    """Strict standard base64 (padded) used by DSSE."""
    if not isinstance(text, str) or len(text) > max_len:
        raise fail("ENVELOPE_MALFORMED", "invalid base64 encoding")
    try:
        raw = base64.b64decode(text, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise fail("ENVELOPE_MALFORMED", "invalid base64 encoding") from exc
    if base64.b64encode(raw).decode("ascii") != text:
        raise fail("ENVELOPE_MALFORMED", "non-canonical base64 encoding")
    return raw


def exact_fields(obj: Any, required: set[str], optional: set[str] = frozenset(), *, what: str = "object") -> Mapping[str, Any]:
    if not isinstance(obj, Mapping):
        raise fail("ENVELOPE_MALFORMED", f"{what} must be an object")
    keys = set(obj)
    missing = sorted(required - keys)
    extra = sorted(keys - required - set(optional))
    if missing or extra:
        raise fail("ENVELOPE_MALFORMED", f"{what} fields invalid", missing=missing, extra=extra)
    return obj
