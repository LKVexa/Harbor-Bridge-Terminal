"""M07 - canonical module digest.

The identity of a module is SHA-256 over its *exact* bytes, custom sections
included (ADR-0003: no normalisation - any byte change is a new module, so a
custom section cannot be swapped under an existing attestation).  The digest
string is ``sha256:<64 lowercase hex>``; parsing is strict.
"""
from __future__ import annotations

import hashlib
import hmac
import re

from .errors import Code, InvalidModule

_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def module_digest(data: bytes) -> str:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise InvalidModule(Code.MALFORMED, "digest input must be bytes")
    return "sha256:" + hashlib.sha256(bytes(data)).hexdigest()


def parse_digest(s: object) -> str:
    if not isinstance(s, str) or not _RE.fullmatch(s):
        raise InvalidModule(Code.DIGEST_MISMATCH, "malformed digest string")
    return s


def digests_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(parse_digest(a).encode(), parse_digest(b).encode())
