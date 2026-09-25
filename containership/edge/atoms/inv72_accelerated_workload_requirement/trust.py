"""Caller authentication and capability authorization at the INV-72 boundary (C023, C024, C042, C044, C048).

INV-72 does not run an identity provider.  The host supplies a ``KeyProvider`` (the identity/key service);
callers present a PK_ACCEL_TOKEN/1: ``principal|tenant_scope|capabilities|nonce|expiry`` signed with the
principal's HMAC-SHA256 key.  Checks, in order, all fail closed:

1. key service reachable - otherwise ``ACCEL_DEPENDENCY_UNAVAILABLE`` (never "allow while down")  (C048)
2. principal known, signature valid (constant-time compare)                                       (C044)
3. token not expired against a trusted clock; clock skew bounded                                  (C048)
4. nonce not seen before inside the validity window                                               (replay)
5. requested capability in the token *and* in the principal's grant (least privilege)             (C024, C042)
6. the requirement's ``tenant`` inside the token's tenant scope                                    (C024)

Capabilities: ``accel.match`` (eligibility only), ``accel.reserve``, ``accel.release``,
``accel.operate`` (quarantine/drain/disable), ``accel.config`` (activate/rollback), ``accel.read``
(status/explain).  No capability implies another.
"""
from __future__ import annotations

import hashlib
import heapq
import hmac
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .errors import AccelError

CAPABILITIES = frozenset({"accel.match", "accel.reserve", "accel.release", "accel.operate",
                          "accel.config", "accel.read"})
MAX_TTL_S = 300
MAX_SKEW_S = 30


class KeyProvider(Protocol):
    def key_for(self, principal: str) -> bytes | None: ...
    def grants(self, principal: str) -> frozenset: ...


@dataclass
class StaticKeyProvider:
    """Reference provider for tests and single-node deployments."""

    keys: dict = field(default_factory=dict)
    grant_map: dict = field(default_factory=dict)
    available: bool = True

    def key_for(self, principal: str) -> bytes | None:
        if not self.available:
            raise ConnectionError("key service unavailable")
        return self.keys.get(principal)

    def grants(self, principal: str) -> frozenset:
        return frozenset(self.grant_map.get(principal, ()))


def _payload(principal: str, tenants: tuple, caps: tuple, nonce: str, expiry: int) -> bytes:
    return "|".join([principal, ",".join(sorted(tenants)), ",".join(sorted(caps)), nonce, str(expiry)]).encode()


def mint(key: bytes, principal: str, tenants, caps, nonce: str, expiry: int) -> str:
    """Create a token (used by callers/tests; INV-72 itself never mints for a caller)."""
    mac = hmac.new(key, _payload(principal, tuple(tenants), tuple(caps), nonce, expiry), hashlib.sha256).hexdigest()
    return "PK_ACCEL_TOKEN/1:" + "|".join([principal, ",".join(sorted(tenants)), ",".join(sorted(caps)),
                                           nonce, str(expiry), mac])


@dataclass
class Principal:
    name: str
    tenants: frozenset
    capabilities: frozenset


@dataclass
class Authenticator:
    provider: KeyProvider
    clock: Callable[[], float] = time.time
    _seen: dict = field(default_factory=dict)
    _expiry_heap: list = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    max_nonces: int = 100_000

    def authenticate(self, token: str) -> Principal:
        if not isinstance(token, str) or not token.startswith("PK_ACCEL_TOKEN/1:") or len(token) > 2048:
            raise AccelError("ACCEL_UNAUTHENTICATED", "missing or malformed token")
        parts = token[len("PK_ACCEL_TOKEN/1:"):].split("|")
        if len(parts) != 6:
            raise AccelError("ACCEL_UNAUTHENTICATED", "malformed token")
        principal, tenants, caps, nonce, expiry_s, mac = parts
        if not principal or not nonce or not expiry_s.isdigit() or len(mac) != 64:
            raise AccelError("ACCEL_UNAUTHENTICATED", "malformed token")
        try:
            key = self.provider.key_for(principal)
        except Exception as exc:  # any provider failure is "unavailable", never "allow"
            raise AccelError("ACCEL_DEPENDENCY_UNAVAILABLE", "identity/key service unavailable") from exc
        if not key:
            raise AccelError("ACCEL_UNAUTHENTICATED", "unknown principal")
        tset = tuple(t for t in tenants.split(",") if t)
        cset = tuple(c for c in caps.split(",") if c)
        expiry = int(expiry_s)
        want = hmac.new(key, _payload(principal, tset, cset, nonce, expiry), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(want, mac):
            raise AccelError("ACCEL_UNAUTHENTICATED", "bad signature")
        now = self.clock()
        if expiry < now - MAX_SKEW_S:
            raise AccelError("ACCEL_UNAUTHENTICATED", "token expired")
        if expiry > now + MAX_TTL_S + MAX_SKEW_S:
            raise AccelError("ACCEL_UNAUTHENTICATED", "token lifetime exceeds MAX_TTL_S")
        with self._lock:
            # amortised O(log n) pruning; the v4.3.0 draft scanned the whole cache on every call, which
            # the 60 s soak exposed as a p50 that grew ~2.7x over the run (evidence/OPTIMIZATION_REPORT.json)
            while self._expiry_heap and self._expiry_heap[0][0] < now - MAX_SKEW_S:
                _, stale = heapq.heappop(self._expiry_heap)
                self._seen.pop(stale, None)
            if (principal, nonce) in self._seen:
                raise AccelError("ACCEL_REPLAY", "nonce reuse")
            if len(self._seen) >= self.max_nonces:
                raise AccelError("ACCEL_OVERLOADED", "replay cache full")
            self._seen[(principal, nonce)] = expiry
            heapq.heappush(self._expiry_heap, (expiry, (principal, nonce)))
        granted = self.provider.grants(principal)
        unknown = set(cset) - CAPABILITIES
        if unknown:
            raise AccelError("ACCEL_FORBIDDEN", f"unknown capabilities {sorted(unknown)}")
        return Principal(principal, frozenset(tset), frozenset(cset) & granted)


def authorize(principal: Principal, capability: str, tenant: str | None = None) -> None:
    if capability not in CAPABILITIES:
        raise AccelError("ACCEL_FORBIDDEN", f"unknown capability {capability}")
    if capability not in principal.capabilities:
        raise AccelError("ACCEL_FORBIDDEN", f"{principal.name} lacks {capability}")
    if tenant is not None and tenant not in principal.tenants and "*" not in principal.tenants:
        raise AccelError("ACCEL_FORBIDDEN", f"{principal.name} not scoped to tenant")
