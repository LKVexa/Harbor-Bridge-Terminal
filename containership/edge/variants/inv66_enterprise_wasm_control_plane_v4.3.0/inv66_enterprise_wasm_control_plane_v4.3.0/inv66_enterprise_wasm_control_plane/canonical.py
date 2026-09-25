"""Canonical JSON and hashing helpers shared by every module."""
from __future__ import annotations

import hashlib
import hmac
import json
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    return sha256_hex(canonical_json(value))


def hmac_hex(key: bytes, domain: bytes, value: Any) -> str:
    return hmac.new(key, domain + canonical_json(value), hashlib.sha256).hexdigest()


def consteq(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())
