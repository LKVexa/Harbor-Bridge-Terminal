"""Bounded, canonical JSON (MC-001 CHK-009/013; reused by every signed artifact).

Canonical form: UTF-8, keys sorted by code point, no insignificant whitespace,
integers only (no floats unless a schema field declares ``number``), NaN/Inf
forbidden.  The parser rejects duplicate keys, over-depth, over-size and
out-of-range integers *before* any scheduling logic sees the payload.
"""
from __future__ import annotations

import hashlib
import json
import math

MAX_BYTES = 1 << 20
MAX_DEPTH = 16
MAX_INT = (1 << 53) - 1
MAX_ITEMS = 100_000


class CanonicalError(ValueError):
    pass


def _reject_constant(name):
    raise CanonicalError(f"non-finite number {name} not permitted")


def _pairs(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise CanonicalError(f"duplicate key {k!r}")
        out[k] = v
    return out


def _check(value, depth=0, counter=None):
    counter = counter if counter is not None else [0]
    counter[0] += 1
    if counter[0] > MAX_ITEMS:
        raise CanonicalError("too many items")
    if depth > MAX_DEPTH:
        raise CanonicalError("nesting too deep")
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, int):
        if abs(value) > MAX_INT:
            raise CanonicalError("integer out of range")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CanonicalError("non-finite float")
        return
    if isinstance(value, list):
        for v in value:
            _check(v, depth + 1, counter)
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalError("non-string key")
            _check(v, depth + 1, counter)
        return
    raise CanonicalError(f"unsupported type {type(value).__name__}")


def loads(data: bytes | str, *, max_bytes: int = MAX_BYTES):
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not isinstance(data, (bytes, bytearray)):
        raise CanonicalError("payload must be bytes")
    if len(data) > max_bytes:
        raise CanonicalError("payload too large")
    try:
        text = bytes(data).decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CanonicalError("invalid utf-8") from exc
    # cheap pre-scan for depth so the stdlib parser never recurses deeply
    depth = best = 0
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
            best = max(best, depth)
            if best > MAX_DEPTH + 1:
                raise CanonicalError("nesting too deep")
        elif ch in "]}":
            depth -= 1
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_constant=_reject_constant)
    except CanonicalError:
        raise
    except (ValueError, RecursionError) as exc:
        raise CanonicalError(f"malformed json: {type(exc).__name__}") from exc
    _check(value)
    return value


def dumps(value) -> bytes:
    _check(value)
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(dumps(value)).hexdigest()


def is_canonical(data: bytes) -> bool:
    try:
        return dumps(loads(data)) == bytes(data)
    except CanonicalError:
        return False


def readb(path) -> bytes:
    with open(path, "rb") as fh:
        return fh.read()
