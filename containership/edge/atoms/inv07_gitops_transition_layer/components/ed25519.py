"""Pure-Python Ed25519 (RFC 8032 section 5.1), stdlib only.

Built new for the shop (no permissive donor was reachable this pass).  It is
a *correct* but *not constant-time* implementation: acceptable for signature
VERIFICATION of public data, which is the GAP-09 use.  Signing here exists
for fixtures and test vectors only; production signers must use a vetted,
constant-time provider (recorded as waiver W-002).
"""
from __future__ import annotations

import hashlib

p = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493
d = (-121665 * pow(121666, p - 2, p)) % p
_SQRT_M1 = pow(2, (p - 1) // 4, p)


def _inv(x: int) -> int:
    return pow(x, p - 2, p)


def _recover_x(y: int, sign: int) -> int | None:
    if y >= p:
        return None
    x2 = (y * y - 1) * _inv(d * y * y + 1) % p
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (p + 3) // 8, p)
    if (x * x - x2) % p != 0:
        x = x * _SQRT_M1 % p
    if (x * x - x2) % p != 0:
        return None
    if (x & 1) != sign:
        x = p - x
    return x


_GY = 4 * _inv(5) % p
_GX = _recover_x(_GY, 0)
G = (_GX, _GY, 1, _GX * _GY % p)
_IDENT = (0, 1, 1, 0)


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % p
    C = 2 * P[3] * Q[3] * d % p
    D = 2 * P[2] * Q[2] % p
    E, F, G_, H = B - A, D - C, D + C, B + A
    return (E * F % p, G_ * H % p, F * G_ % p, E * H % p)


def _mul(s: int, P):
    Q = _IDENT
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _eq(P, Q) -> bool:
    return (P[0] * Q[2] - Q[0] * P[2]) % p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % p == 0


def _compress(P) -> bytes:
    zi = _inv(P[2])
    x, y = P[0] * zi % p, P[1] * zi % p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decompress(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % p)


def _h(m: bytes) -> int:
    return int.from_bytes(hashlib.sha512(m).digest(), "little")


def _expand(secret: bytes):
    if len(secret) != 32:
        raise ValueError("Ed25519 secret must be 32 bytes")
    h = hashlib.sha512(secret).digest()
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret: bytes) -> bytes:
    a, _ = _expand(secret)
    return _compress(_mul(a, G))


def sign(secret: bytes, msg: bytes) -> bytes:
    """Fixture signer (not constant-time)."""
    a, prefix = _expand(secret)
    A = _compress(_mul(a, G))
    r = _h(prefix + msg) % L
    R = _compress(_mul(r, G))
    k = _h(R + A + msg) % L
    s = (r + k * a) % L
    return R + int.to_bytes(s, 32, "little")


def verify(public: bytes, msg: bytes, signature: bytes) -> bool:
    """Strict RFC 8032 verification; rejects non-canonical S (malleability)."""
    if not isinstance(public, (bytes, bytearray)) or len(public) != 32:
        return False
    if not isinstance(signature, (bytes, bytearray)) or len(signature) != 64:
        return False
    A = _decompress(bytes(public))
    if A is None:
        return False
    Rs = bytes(signature[:32])
    R = _decompress(Rs)
    if R is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= L:
        return False
    k = _h(Rs + bytes(public) + msg) % L
    return _eq(_mul(s, G), _add(R, _mul(k, A)))
