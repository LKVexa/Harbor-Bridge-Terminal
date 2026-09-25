"""Deterministic canonical JSON encoding for signing (GAP04-C01-007, C05).

Rules (PK_CANON/1): UTF-8, NFC-normalized strings only (non-NFC input is
rejected, not normalized), object keys sorted by code point, no insignificant
whitespace, integers only (floats, NaN, bool-as-int ambiguity rejected at the
schema layer), duplicate keys rejected on parse, and a hard size limit.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any

CANON_VERSION = "PK_CANON/1"
MAX_DOC_BYTES = 64 * 1024
MAX_DEPTH = 16


class CanonicalError(ValueError):
    pass


def _check(value: Any, depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise CanonicalError("document nesting too deep")
    if value is None or isinstance(value, bool):
        return
    if isinstance(value, int):
        if abs(value) > 2**53 - 1:
            raise CanonicalError("integer outside interoperable range")
        return
    if isinstance(value, float):
        raise CanonicalError("floating-point values are not canonical")
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise CanonicalError("string is not NFC-normalized")
        return
    if isinstance(value, (list, tuple)):
        for v in value:
            _check(v, depth + 1)
        return
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise CanonicalError("object keys must be strings")
            _check(k, depth + 1)
            _check(v, depth + 1)
        return
    raise CanonicalError(f"unsupported type {type(value).__name__}")


def dumps(value: Any) -> bytes:
    _check(value)
    out = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(out) > MAX_DOC_BYTES:
        raise CanonicalError("document exceeds size limit")
    return out


def _no_dupes(pairs):
    d = {}
    for k, v in pairs:
        if k in d:
            raise CanonicalError(f"duplicate key {k!r}")
        d[k] = v
    return d


def loads(data: bytes | str, *, require_canonical: bool = True) -> Any:
    raw = data.encode("utf-8") if isinstance(data, str) else bytes(data)
    if len(raw) > MAX_DOC_BYTES:
        raise CanonicalError("document exceeds size limit")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_dupes,
                           parse_float=lambda s: (_ for _ in ()).throw(CanonicalError("float")),
                           parse_constant=lambda s: (_ for _ in ()).throw(CanonicalError("constant")))
    except CanonicalError:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise CanonicalError(f"malformed JSON: {e}") from None
    if require_canonical and dumps(value) != raw:
        raise CanonicalError("document is not in canonical form")
    return value


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(dumps(value)).hexdigest()
