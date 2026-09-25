"""Pure-Python Ed25519 (RFC 8032, section 5.1) — stdlib only.

Used so the production layer has real asymmetric signatures without a
third-party dependency. Verification is strict: non-canonical ``S`` (>= L)
and non-canonical point encodings are rejected (signature malleability,
MC-03-09). This implementation is not constant-time; private keys must live
behind a ``KeyProvider`` boundary (see ``signing.py``) and production signing
is expected to be delegated to an HSM/KMS (MC-03-07, a recorded blocker).
"""
from __future__ import annotations

import hashlib

p = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493
d = -121665 * pow(121666, p - 2, p) % p
_SQRT_M1 = pow(2, (p - 1) // 4, p)


def _sha512(data: bytes) -> bytes:
    return hashlib.sha512(data).digest()


def _add(P, Q):
    A = (P[1] - P[0]) * (Q[1] - Q[0]) % p
    B = (P[1] + P[0]) * (Q[1] + Q[0]) % p
    C = 2 * P[3] * Q[3] * d % p
    D = 2 * P[2] * Q[2] % p
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % p, G * H % p, F * G % p, E * H % p)


def _mul(s: int, P):
    Q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _equal(P, Q) -> bool:
    return (P[0] * Q[2] - Q[0] * P[2]) % p == 0 and (P[1] * Q[2] - Q[1] * P[2]) % p == 0


def _recover_x(y: int, sign: int):
    if y >= p:
        return None
    x2 = (y * y - 1) * pow(d * y * y + 1, p - 2, p) % p
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


_GY = 4 * pow(5, p - 2, p) % p
_GX = _recover_x(_GY, 0)
G = (_GX, _GY, 1, _GX * _GY % p)


def _compress(P) -> bytes:
    zinv = pow(P[2], p - 2, p)
    x = P[0] * zinv % p
    y = P[1] * zinv % p
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


def _secret_expand(secret: bytes):
    if len(secret) != 32:
        raise ValueError("Ed25519 secret key must be 32 bytes")
    h = _sha512(secret)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(secret: bytes) -> bytes:
    a, _ = _secret_expand(secret)
    return _compress(_mul(a, G))


def sign(secret: bytes, message: bytes) -> bytes:
    a, prefix = _secret_expand(secret)
    A = _compress(_mul(a, G))
    r = int.from_bytes(_sha512(prefix + message), "little") % L
    R = _compress(_mul(r, G))
    h = int.from_bytes(_sha512(R + A + message), "little") % L
    s = (r + h * a) % L
    return R + int.to_bytes(s, 32, "little")


def verify(public: bytes, message: bytes, signature: bytes) -> bool:
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
    if s >= L:  # strict: reject malleable S
        return False
    h = int.from_bytes(_sha512(Rs + bytes(public) + message), "little") % L
    return _equal(_mul(s, G), _add(R, _mul(h, A)))
