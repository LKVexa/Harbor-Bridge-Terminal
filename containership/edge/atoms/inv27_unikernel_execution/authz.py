"""Caller authentication and capability authorization (MC-024, MC-025; C042, C043).

A caller presents a ``PK_UNIKERNEL_TOKEN/1``: canonical JSON claims + HMAC-SHA256 under a key
the host resolves by ``kid`` (keys come from the secret store; never from config literals).
Claims: ``sub`` (principal), ``tenants`` (scope), ``caps`` (capabilities), ``iat``/``exp``, ``nonce``.

Capabilities:  image.admit, instance.run, instance.stop, instance.quarantine,
               config.apply, config.rollback, component.disable, audit.read
Tenant-scoped capabilities require the target tenant in ``tenants`` ("*" is refused for tenant
data - operators use the explicit operator caps).  Nonces are single-use within their validity
window (bounded store, O(1) pruning).  Service identities cannot hold ``config.apply`` in prod
unless the host allows it explicitly.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Callable

from .errors import UkError

CAPS = frozenset({"image.admit", "instance.run", "instance.stop", "instance.quarantine", "config.apply",
                  "config.rollback", "component.disable", "audit.read"})
TENANT_SCOPED = frozenset({"image.admit", "instance.run", "instance.stop"})
MAX_TTL_S = 900


@dataclass(frozen=True)
class Principal:
    sub: str
    tenants: frozenset
    caps: frozenset
    kid: str


def _canon(d: dict) -> bytes:
    return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()


def mint(claims: dict, key: bytes, kid: str) -> str:
    body = base64.urlsafe_b64encode(_canon(claims)).decode().rstrip("=")
    mac = hmac.new(key, f"{kid}.{body}".encode(), hashlib.sha256).hexdigest()
    return f"{kid}.{body}.{mac}"


@dataclass
class Authenticator:
    keys: Callable[[str], bytes | None]
    clock: Callable[[], float] = time.time
    max_nonces: int = 100_000
    _nonces: OrderedDict = field(default_factory=OrderedDict)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def authenticate(self, token: str | None) -> Principal:
        if not isinstance(token, str) or token.count(".") != 2 or len(token) > 8192:
            raise UkError("UK_UNAUTHENTICATED", "missing or malformed token")
        kid, body, mac = token.split(".")
        key = self.keys(kid)
        if not key:
            raise UkError("UK_UNAUTHENTICATED", "unknown key id")
        want = hmac.new(key, f"{kid}.{body}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, mac):
            raise UkError("UK_UNAUTHENTICATED", "bad token MAC")
        try:
            raw = base64.urlsafe_b64decode(body + "=" * (-len(body) % 4))
            claims = json.loads(raw)
        except (binascii.Error, ValueError):
            raise UkError("UK_UNAUTHENTICATED", "token body not decodable") from None
        if _canon(claims) != raw:
            raise UkError("UK_UNAUTHENTICATED", "token body not canonical")
        need = {"sub", "tenants", "caps", "iat", "exp", "nonce"}
        if not isinstance(claims, dict) or set(claims) != need:
            raise UkError("UK_UNAUTHENTICATED", "token claims shape")
        now = self.clock()
        if not (isinstance(claims["iat"], (int, float)) and isinstance(claims["exp"], (int, float))
                and claims["iat"] - 30 <= now < claims["exp"] and claims["exp"] - claims["iat"] <= MAX_TTL_S):
            raise UkError("UK_UNAUTHENTICATED", "token expired, not yet valid, or TTL too long")
        caps = frozenset(claims["caps"]) if isinstance(claims["caps"], list) else None
        if caps is None or not caps <= CAPS:
            raise UkError("UK_UNAUTHENTICATED", "unknown capabilities in token")
        nonce = claims["nonce"]
        if not isinstance(nonce, str) or not 16 <= len(nonce) <= 64:
            raise UkError("UK_UNAUTHENTICATED", "nonce must be 16..64 chars")
        with self._lock:
            while self._nonces and next(iter(self._nonces.values())) < now:
                self._nonces.popitem(last=False)
            if nonce in self._nonces:
                raise UkError("UK_REPLAY")
            if len(self._nonces) >= self.max_nonces:
                raise UkError("UK_OVERLOADED", "nonce store full")
            self._nonces[nonce] = claims["exp"]
        tenants = claims["tenants"]
        if not isinstance(tenants, list) or not all(isinstance(t, str) and t for t in tenants):
            raise UkError("UK_UNAUTHENTICATED", "tenants must be a list of names")
        return Principal(str(claims["sub"])[:128], frozenset(tenants), caps, kid)


def authorize(p: Principal, cap: str, *, tenant: str | None = None) -> None:
    if cap not in CAPS:
        raise KeyError(cap)
    if cap not in p.caps:
        raise UkError("UK_FORBIDDEN", f"{p.sub} lacks {cap}", cap=cap)
    if cap in TENANT_SCOPED:
        if not tenant or tenant not in p.tenants:
            raise UkError("UK_FORBIDDEN", f"{p.sub} is not scoped to tenant", cap=cap)
