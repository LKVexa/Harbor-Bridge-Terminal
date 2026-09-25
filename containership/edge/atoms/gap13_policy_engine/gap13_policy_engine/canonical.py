"""Canonical JSON used for every digest/signature in GAP-13 (G13-MC-002).

Rules (normative, see ``docs/REQUIREMENTS.md`` REQ-BND-004):
* UTF-8, NFC-normalised strings; keys sorted by code point; no insignificant
  whitespace (separators ``,`` and ``:``); ``ensure_ascii=False``.
* Integers only -- floats, NaN and Infinity are refused so numeric
  representation can never differ between signer and verifier.
* ``bool`` and ``None`` serialise as JSON literals.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from typing import Any


def _normalise(value: Any, depth: int = 0) -> Any:
    if depth > 64:
        raise ValueError("value nests deeper than 64 levels")
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        raise ValueError("floats are not permitted in canonical policy JSON")
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, (list, tuple)):
        return [_normalise(v, depth + 1) for v in value]
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if not isinstance(k, str):
                raise ValueError("object keys must be strings")
            nk = unicodedata.normalize("NFC", k)
            if nk in out:
                raise ValueError(f"keys collide after NFC normalisation: {k!r}")
            out[nk] = _normalise(v, depth + 1)
        return out
    raise ValueError(f"type {type(value).__name__} is not canonical-JSON serialisable")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(_normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    return "sha256:" + sha256_hex(canonical_bytes(value))
