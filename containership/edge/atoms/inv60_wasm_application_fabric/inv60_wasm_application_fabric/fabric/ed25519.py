"""Pure-Python Ed25519 (RFC 8032) - stdlib only.

Reference-grade and NOT constant time. It exists so signature/identity checks run
with no third-party dependency; tests cross-check it against RFC 8032 vectors and
(when installed) the ``cryptography`` package. Production deployments SHOULD
swap in a vetted constant-time implementation via ``signing.set_backend``.
"""
from __future__ import annotations

import hashlib

p = 2**255 - 19
L = 2**252 + 27742317777372353535851937790883648493
d = -121665 * pow(121666, p - 2, p) % p
I = pow(2, (p - 1) // 4, p)


def _sha512(m: bytes) -> bytes:
    return hashlib.sha512(m).digest()


def _xrecover(y: int) -> int:
    xx = (y * y - 1) * pow(d * y * y + 1, p - 2, p)
    x = pow(xx, (p + 3) // 8, p)
    if (x * x - xx) % p != 0:
        x = x * I % p
    if x % 2 != 0:
        x = p - x
    return x


By = 4 * pow(5, p - 2, p) % p
Bx = _xrecover(By)
B = (Bx, By, 1, Bx * By % p)
ZERO = (0, 1, 1, 0)


def _add(P, Q):
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    A = (y1 - x1) * (y2 - x2) % p
    Bv = (y1 + x1) * (y2 + x2) % p
    C = t1 * 2 * d * t2 % p
    D = z1 * 2 * z2 % p
    E, F, G, H = Bv - A, D - C, D + C, Bv + A
    return (E * F % p, G * H % p, F * G % p, E * H % p)


def _mul(s: int, P):
    Q = ZERO
    while s > 0:
        if s & 1:
            Q = _add(Q, P)
        P = _add(P, P)
        s >>= 1
    return Q


def _encode(P) -> bytes:
    x, y, z, _ = P
    zi = pow(z, p - 2, p)
    x, y = x * zi % p, y * zi % p
    return int.to_bytes(y | ((x & 1) << 255), 32, "little")


def _decode(s: bytes):
    if len(s) != 32:
        raise ValueError("bad point length")
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= p:
        raise ValueError("non-canonical y")
    x = _xrecover(y)
    if (x & 1) != sign:
        x = p - x
    P = (x, y, 1, x * y % p)
    if (-x * x + y * y - 1 - d * x * x * y * y) % p != 0:
        raise ValueError("point not on curve")
    return P


def _expand(seed: bytes):
    if len(seed) != 32:
        raise ValueError("seed must be 32 bytes")
    h = _sha512(seed)
    a = int.from_bytes(h[:32], "little")
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:]


def public_key(seed: bytes) -> bytes:
    a, _ = _expand(seed)
    return _encode(_mul(a, B))


def sign(seed: bytes, msg: bytes) -> bytes:
    a, prefix = _expand(seed)
    A = _encode(_mul(a, B))
    r = int.from_bytes(_sha512(prefix + msg), "little") % L
    R = _encode(_mul(r, B))
    k = int.from_bytes(_sha512(R + A + msg), "little") % L
    S = (r + k * a) % L
    return R + int.to_bytes(S, 32, "little")


def verify(pub: bytes, msg: bytes, sig: bytes) -> bool:
    try:
        if len(sig) != 64:
            return False
        A = _decode(pub)
        R = _decode(sig[:32])
        S = int.from_bytes(sig[32:], "little")
        if S >= L:
            return False
        k = int.from_bytes(_sha512(sig[:32] + pub + msg), "little") % L
        return _encode(_mul(S, B)) == _encode(_add(R, _mul(k, A)))
    except (ValueError, TypeError):
        return False
