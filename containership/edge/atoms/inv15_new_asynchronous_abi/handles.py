"""Opaque handle representation (components 5, 6, 20, 21, 40, 41).

Binary layout, version 1 (all integers unsigned, big-endian, no padding):

    offset size field
    0      1    format version (only 1 is defined; 0 and 255 are forbidden)
    1      1    feature flags
    2      4    host epoch (incremented on every host restart)
    6      4    slot index
    10     4    slot generation (incremented on every slot reuse)
    14     16   authority token (CSPRNG)
    30     16   [only if FLAG_AUTH] HMAC-SHA256/128 over bytes 0..29 + tenant id

Feature flag bits: bit0 = FLAG_AUTH (must-understand). Bits 1..3 are
must-understand and currently undefined, so any set bit is rejected. Bits 4..7
are advisory and ignored by version-1 decoders.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import hmac

from .errors import Malformed, UnsupportedFeature, UnsupportedVersion, Replayed

FORMAT_VERSION = 1
FLAG_AUTH = 0x01
MUST_UNDERSTAND_MASK = 0x0F
KNOWN_MUST_UNDERSTAND = FLAG_AUTH
BASE_LEN = 30
AUTH_LEN = 16
U32 = (1 << 32) - 1


@dataclass(frozen=True, slots=True)
class Handle:
    epoch: int
    slot: int
    generation: int
    token: bytes = field(repr=False)

    def __post_init__(self):
        for name in ("epoch", "slot", "generation"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= U32:
                raise Malformed(f"{name} out of u32 range")
        if not isinstance(self.token, (bytes, bytearray)) or len(self.token) != 16:
            raise Malformed("token must be 16 bytes")

    @property
    def diagnostic_id(self) -> str:
        """Non-secret diagnostic identifier (epoch.slot.generation)."""
        return f"{self.epoch}.{self.slot}.{self.generation}"

    def __str__(self) -> str:  # never print the token
        return f"<handle {self.diagnostic_id}>"


def _mac(key: bytes, body: bytes, tenant: str) -> bytes:
    return hmac.new(key, body + b"\x00" + tenant.encode("utf-8"), hashlib.sha256).digest()[:AUTH_LEN]


def encode(h: Handle, *, auth_key: bytes | None = None, tenant: str = "") -> bytes:
    flags = FLAG_AUTH if auth_key is not None else 0
    body = (bytes([FORMAT_VERSION, flags]) + h.epoch.to_bytes(4, "big") + h.slot.to_bytes(4, "big")
            + h.generation.to_bytes(4, "big") + bytes(h.token))
    if auth_key is not None:
        body += _mac(auth_key, body, tenant)
    return body


def decode(data: bytes, *, auth_key: bytes | None = None, tenant: str = "") -> Handle:
    if not isinstance(data, (bytes, bytearray)):
        raise Malformed("handle encoding must be bytes")
    data = bytes(data)
    if len(data) < 2:
        raise Malformed("truncated handle")
    version, flags = data[0], data[1]
    if version != FORMAT_VERSION:
        raise UnsupportedVersion(f"handle format version {version}")
    if flags & MUST_UNDERSTAND_MASK & ~KNOWN_MUST_UNDERSTAND:
        raise UnsupportedFeature("unknown must-understand handle feature bit")
    want = BASE_LEN + (AUTH_LEN if flags & FLAG_AUTH else 0)
    if len(data) != want:
        raise Malformed(f"handle length {len(data)} != {want}")
    if auth_key is not None and not flags & FLAG_AUTH:
        raise Replayed("unauthenticated handle presented at an authenticated boundary")
    if flags & FLAG_AUTH:
        if auth_key is None:
            raise UnsupportedFeature("authenticated handle but no key at this boundary")
        if not hmac.compare_digest(data[BASE_LEN:], _mac(auth_key, data[:BASE_LEN], tenant)):
            raise Replayed("handle authentication failed")
    return Handle(int.from_bytes(data[2:6], "big"), int.from_bytes(data[6:10], "big"),
                  int.from_bytes(data[10:14], "big"), data[14:30])


def redact(h: Handle, key: bytes) -> str:
    """Secret-safe correlation id: keyed hash, never reversible to the token."""
    return hmac.new(key, bytes(h.token), hashlib.sha256).hexdigest()[:16]
