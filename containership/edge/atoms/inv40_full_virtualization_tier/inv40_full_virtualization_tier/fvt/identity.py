"""Authentication and capability authorization at every tier boundary
(INV-40-C023, C024, C042-C044, C048).

Callers present a capability token: a canonical JSON claim set MAC'd with
HMAC-SHA256 by a key the tier obtains from a ``KeyProvider``.  Claims bind
subject, kind (human|service|node|controller), audience, tenant scope, the
exact operations granted, expiry and a nonce.  Nonces are single-use within
their lifetime (replay cache).  Every missing, expired, replayed, mis-scoped
or unverifiable token is refused; if the key or the clock is unavailable the
tier fails CLOSED (PK_FULL_VM_TRUST_UNAVAILABLE) rather than admitting.

Production note (recorded as blocker SEC-KMS): HMAC keys are symmetric; a
production deployment binds KeyProvider to a KMS/IdP and should move to an
asymmetric issuer.  Neither exists in this repository.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass

from .errors import OpError

AUDIENCE = "pk-full-vm"
OPERATIONS = frozenset({"create", "boot", "stop", "destroy", "read", "quarantine", "admin"})
MAX_TTL_S = 3600
KINDS = frozenset({"human", "service", "node", "controller"})


class KeyProvider:
    """Source of MAC keys by key id.  Raise ``LookupError`` if unavailable."""

    def __init__(self, keys: dict[str, bytes] | None = None):
        self._keys = dict(keys or {})
        self.available = True

    def get(self, kid: str) -> bytes:
        if not self.available:
            raise LookupError("key service unavailable")
        if kid not in self._keys:
            raise KeyError(kid)
        k = self._keys[kid]
        if len(k) < 32:
            raise LookupError("key too short")
        return k

    def rotate(self, kid: str, key: bytes) -> None:
        self._keys[kid] = key

    def revoke(self, kid: str) -> None:
        self._keys.pop(kid, None)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def issue(keys: KeyProvider, kid: str, *, sub: str, kind: str, tenants: list[str], ops: list[str],
          ttl_s: int = 300, nonce: str, now: float | None = None, aud: str = AUDIENCE) -> str:
    if kind not in KINDS or not set(ops) <= OPERATIONS or not tenants or ttl_s > MAX_TTL_S:
        raise ValueError("invalid claims")
    now = time.time() if now is None else now
    claims = {"sub": sub, "kind": kind, "aud": aud, "tenants": sorted(tenants), "ops": sorted(ops),
              "iat": int(now), "exp": int(now) + ttl_s, "nonce": nonce, "kid": kid}
    body = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    mac = hmac.new(keys.get(kid), body, hashlib.sha256).digest()
    return _b64(body) + "." + _b64(mac)


@dataclass(frozen=True)
class Principal:
    sub: str
    kind: str
    tenants: frozenset
    ops: frozenset
    nonce: str

    def may(self, op: str, tenant: str) -> bool:
        return op in self.ops and (tenant in self.tenants or "*" in self.tenants and self.kind == "controller")


class Authenticator:
    def __init__(self, keys: KeyProvider, clock=time.time, *, skew_s: int = 30):
        self.keys, self.clock, self.skew_s = keys, clock, skew_s
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def authenticate(self, token: object) -> Principal:
        if not isinstance(token, str) or token.count(".") != 1 or len(token) > 8192:
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "malformed credential")
        try:
            now = self.clock()
            if not isinstance(now, (int, float)) or now <= 0:
                raise LookupError("clock")
        except Exception:  # noqa: BLE001
            raise OpError("PK_FULL_VM_TRUST_UNAVAILABLE", "time source unavailable; failing closed") from None
        b, m = token.split(".")
        try:
            body, mac = _unb64(b), _unb64(m)
            claims = json.loads(body)
        except Exception:  # noqa: BLE001
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "undecodable credential") from None
        if not isinstance(claims, dict) or not isinstance(claims.get("kid"), str):
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "missing key id")
        try:
            key = self.keys.get(claims["kid"])
        except KeyError:
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "unknown or revoked key id") from None
        except LookupError:
            raise OpError("PK_FULL_VM_TRUST_UNAVAILABLE", "key service unavailable; failing closed") from None
        if not hmac.compare_digest(hmac.new(key, body, hashlib.sha256).digest(), mac):
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "bad signature")
        if claims.get("aud") != AUDIENCE:
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "wrong audience")
        exp, iat = claims.get("exp"), claims.get("iat")
        if not isinstance(exp, int) or not isinstance(iat, int) or exp - iat > MAX_TTL_S:
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "bad lifetime")
        if now > exp + self.skew_s or now + self.skew_s < iat:
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "expired or not yet valid")
        if claims.get("kind") not in KINDS:
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "bad principal kind")
        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            raise OpError("PK_FULL_VM_UNAUTHENTICATED", "missing nonce")
        with self._lock:
            for n, e in list(self._seen.items()):
                if e + self.skew_s < now:
                    del self._seen[n]
            if nonce in self._seen:
                raise OpError("PK_FULL_VM_UNAUTHENTICATED", "replayed credential")
            self._seen[nonce] = exp
        return Principal(claims["sub"], claims["kind"], frozenset(claims.get("tenants", [])),
                         frozenset(claims.get("ops", [])), nonce)


def authorize(p: Principal, op: str, tenant: str) -> None:
    """Least privilege: exact op + exact tenant (controllers alone may hold '*')."""
    if op not in OPERATIONS:
        raise OpError("PK_FULL_VM_FORBIDDEN", f"unknown operation {op}")
    if not p.may(op, tenant):
        raise OpError("PK_FULL_VM_FORBIDDEN", f"{p.sub} lacks '{op}' on tenant {tenant}",
                      subject=p.sub, op=op, tenant=tenant)
