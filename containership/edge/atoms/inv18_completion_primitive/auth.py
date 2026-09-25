"""Authentication for non-local boundaries (C023, C044, C047, C048).

The core primitive is in-process and has no authentication boundary; its
capabilities are the access control.  When futures are exposed through the wire
adapter, every message carries a compact HMAC-SHA256 bearer token:

    base64url(json claims) "." base64url(mac)
    claims = {iss, aud, sub, cap, iat, exp, nonce, kid}

Verification order: key service reachable -> structure -> kid known -> MAC ->
issuer -> audience -> expiry/ttl -> replay (nonce) -> capability.  Identity is
taken only from verified claims, never from caller-controlled metadata.
Key material is obtained from a ``KeyRing`` (current + previous key for overlap
during rotation, revocation list); key bytes never appear in repr/logs.
Every unavailable security service fails closed.
"""
from __future__ import annotations

import base64
import collections
import hashlib
import hmac
import json
import secrets
import threading
import time
from typing import Mapping

from .errors import Rejected

ISSUER = "inv18-control-plane"
AUDIENCE = "inv18-wire"
CAPS = ("create", "resolve", "abandon", "receive", "inspect", "administer")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class KeyRing:
    """Key source abstraction; ``secret://`` references resolve through ``resolver``."""

    def __init__(self, resolver=None):
        self._keys: dict[str, bytes] = {}
        self.current: str | None = None
        self.revoked: set[str] = set()
        self.available = True
        self._resolver = resolver

    def __repr__(self) -> str:
        return f"KeyRing(kids={sorted(self._keys)}, current={self.current!r})"

    def add(self, kid: str, key: bytes | None = None, *, make_current: bool = True) -> None:
        if key is None and self._resolver is not None:
            key = self._resolver(kid)
        if not isinstance(key, bytes) or len(key) < 32:
            raise Rejected("keys must be >= 256 bits", code="INVALID_CONFIG")
        self._keys[kid] = key
        if make_current:
            self.current = kid

    def rotate(self, new_kid: str, key: bytes | None = None) -> None:
        """New key signs; previous keys still verify until retired (overlap window)."""
        self.add(new_kid, key or secrets.token_bytes(32), make_current=True)

    def retire(self, kid: str) -> None:
        self._keys.pop(kid, None)

    def revoke(self, kid: str) -> None:
        self.revoked.add(kid)

    def get(self, kid: str) -> bytes:
        if not self.available:
            raise Rejected("key service unavailable", code="DEPENDENCY_UNAVAILABLE")
        if kid in self.revoked:
            raise Rejected("key revoked", code="UNAUTHENTICATED")
        k = self._keys.get(kid)
        if k is None:
            raise Rejected("unknown key id", code="UNAUTHENTICATED")
        return k


class Authenticator:
    def __init__(self, keyring: KeyRing, *, issuer: str = ISSUER, audience: str = AUDIENCE,
                 max_ttl_s: int = 900, clock=time.time, replay_cache: int = 100_000,
                 time_trusted=lambda: True):
        self.keys, self.issuer, self.audience, self.max_ttl = keyring, issuer, audience, max_ttl_s
        self._clock = clock
        self._seen: collections.OrderedDict[str, float] = collections.OrderedDict()
        self._seen_max = replay_cache
        self._lock = threading.Lock()
        self._time_trusted = time_trusted

    def issue(self, sub: str, caps: list[str], *, ttl_s: int = 300, aud: str | None = None,
              iss: str | None = None, kid: str | None = None, iat: float | None = None) -> str:
        kid = kid or self.keys.current
        now = self._clock() if iat is None else iat
        claims = {"iss": iss or self.issuer, "aud": aud or self.audience, "sub": sub, "cap": sorted(caps),
                  "iat": int(now), "exp": int(now + ttl_s), "nonce": secrets.token_hex(12), "kid": kid}
        body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
        mac = hmac.new(self.keys.get(kid), body.encode(), hashlib.sha256).digest()
        return body + "." + _b64(mac)

    def verify(self, token: str, need: str) -> Mapping:
        if not self._time_trusted():
            raise Rejected("trusted time unavailable", code="DEPENDENCY_UNAVAILABLE")
        if not isinstance(token, str) or token.count(".") != 1 or len(token) > 4096:
            raise Rejected("malformed credential", code="UNAUTHENTICATED")
        body, mac = token.split(".")
        try:
            claims = json.loads(_unb64(body))
            mac_b = _unb64(mac)
        except Exception:
            raise Rejected("malformed credential", code="UNAUTHENTICATED") from None
        if not isinstance(claims, dict) or not isinstance(claims.get("kid"), str):
            raise Rejected("malformed credential", code="UNAUTHENTICATED")
        key = self.keys.get(claims["kid"])           # raises DEPENDENCY_UNAVAILABLE / UNAUTHENTICATED
        if not hmac.compare_digest(hmac.new(key, body.encode(), hashlib.sha256).digest(), mac_b):
            raise Rejected("bad signature", code="UNAUTHENTICATED")
        if claims.get("iss") != self.issuer:
            raise Rejected("wrong issuer", code="UNAUTHENTICATED")
        if claims.get("aud") != self.audience:
            raise Rejected("wrong audience", code="UNAUTHENTICATED")
        now = self._clock()
        exp, iat = claims.get("exp"), claims.get("iat")
        if not isinstance(exp, int) or not isinstance(iat, int) or exp <= now or exp - iat > self.max_ttl \
                or iat > now + 60:
            raise Rejected("credential expired or ttl invalid", code="UNAUTHENTICATED")
        nonce = claims.get("nonce")
        with self._lock:
            if not isinstance(nonce, str) or nonce in self._seen:
                raise Rejected("credential replayed", code="REPLAY_DETECTED")
            self._seen[nonce] = exp
            while len(self._seen) > self._seen_max:
                self._seen.popitem(last=False)
        if need not in claims.get("cap", []):
            raise Rejected(f"capability {need} not granted", code="PERMISSION_DENIED")
        return claims
