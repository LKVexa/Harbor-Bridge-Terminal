"""Capability-token enforcement, key rotation and security-dependency outage policy
(MC-013, MC-032 key-rotation part, MC-033).

Tokens are compact ``<b64url(json claims)>.<b64url(hmac-sha256)>`` strings minted
by PLN-07 (the security plane).  This module *verifies* them; the reference
``TokenIssuer`` exists only so tests and fixtures can mint tokens.  Production key
material is supplied by the security plane / KMS, never by this archive.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable

from .runtime import RuntimePlaneError

TOKEN_VERSION = "pk.captoken/1"
MAX_TOKEN_CHARS = 4096
MAX_TTL_SECONDS = 3600
CLOCK_SKEW_SECONDS = 30


class TokenInvalid(RuntimePlaneError):
    code = "PK_TOKEN_INVALID"


class TokenExpired(TokenInvalid):
    code = "PK_TOKEN_EXPIRED"


class SecurityDependencyUnavailable(RuntimePlaneError):
    code = "PK_SECURITY_DEPENDENCY_UNAVAILABLE"


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass
class KeyRing:
    """Verification keys by key id.  Rotation = add new kid, move ``active``, retire old after max TTL."""

    keys: dict[str, bytes] = field(default_factory=dict)
    active: str | None = None
    retired: set[str] = field(default_factory=set)
    _lock: RLock = field(default_factory=RLock, repr=False)

    def add(self, kid: str, secret: bytes, *, activate: bool = False) -> None:
        if len(secret) < 32:
            raise ValueError("token keys must be at least 256 bits")
        with self._lock:
            self.keys[kid] = secret
            if activate or self.active is None:
                self.active = kid

    def retire(self, kid: str) -> None:
        with self._lock:
            if kid == self.active:
                raise ValueError("cannot retire the active key; rotate first")
            self.retired.add(kid)

    def get(self, kid: str) -> bytes | None:
        with self._lock:
            return None if kid in self.retired else self.keys.get(kid)


@dataclass(frozen=True)
class Claims:
    workload: str
    tenant: str
    capabilities: frozenset[str]
    issued_at: int
    expires_at: int
    token_id: str
    kid: str


class TokenIssuer:
    """Reference issuer for tests/fixtures only (PLN-07 owns issuance in production)."""

    def __init__(self, ring: KeyRing, clock: Callable[[], float] = time.time):
        self.ring, self.clock = ring, clock

    def mint(self, workload: str, tenant: str, capabilities: set[str], ttl: int = 300, token_id: str = "t") -> str:
        if not 0 < ttl <= MAX_TTL_SECONDS:
            raise ValueError("ttl out of range")
        kid = self.ring.active
        if kid is None:
            raise ValueError("no active key")
        now = int(self.clock())
        body = {"v": TOKEN_VERSION, "wl": workload, "tn": tenant, "cap": sorted(capabilities),
                "iat": now, "exp": now + ttl, "jti": token_id, "kid": kid}
        raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
        sig = hmac.new(self.ring.keys[kid], raw, hashlib.sha256).digest()
        return f"{_b64e(raw)}.{_b64e(sig)}"


class TokenVerifier:
    """Fail-closed verifier.  Outage policy (MC-033):

    * key ring empty / kid unknown           -> TokenInvalid (terminal, fail closed)
    * clock reported unhealthy by ``clock_ok`` -> SecurityDependencyUnavailable (retryable, fail closed)
    * policy/attestation provider unavailable  -> SecurityDependencyUnavailable (retryable, fail closed)
    No path grants access when a security dependency cannot be consulted.
    """

    def __init__(self, ring: KeyRing, clock: Callable[[], float] = time.time,
                 clock_ok: Callable[[], bool] = lambda: True,
                 revoked: Callable[[str], bool] | None = None):
        self.ring, self.clock, self.clock_ok = ring, clock, clock_ok
        self.revoked = revoked

    def verify(self, token: str | None, *, workload: str, tenant: str, capability: str) -> Claims:
        if not token:
            raise TokenInvalid("capability token absent", workload=workload, capability=capability)
        if not isinstance(token, str) or len(token) > MAX_TOKEN_CHARS or token.count(".") != 1:
            raise TokenInvalid("malformed capability token")
        if not self.clock_ok():
            raise SecurityDependencyUnavailable("trusted time unavailable; refusing to evaluate expiry",
                                                dependency="time")
        raw_b64, sig_b64 = token.split(".")
        try:
            raw, sig = _b64d(raw_b64), _b64d(sig_b64)
            body = json.loads(raw)
        except Exception:
            raise TokenInvalid("undecodable capability token") from None
        if not isinstance(body, dict) or body.get("v") != TOKEN_VERSION:
            raise TokenInvalid("unsupported token version")
        key = self.ring.get(str(body.get("kid")))
        if key is None:
            raise TokenInvalid("unknown or retired signing key", kid=str(body.get("kid")))
        if not hmac.compare_digest(hmac.new(key, raw, hashlib.sha256).digest(), sig):
            raise TokenInvalid("bad token signature")
        if self.revoked is not None:
            try:
                is_revoked = self.revoked(str(body.get("jti")))
            except Exception:
                raise SecurityDependencyUnavailable("revocation source unavailable", dependency="revocation") from None
            if is_revoked:
                raise TokenInvalid("token revoked")
        now = self.clock()
        try:
            iat, exp = int(body["iat"]), int(body["exp"])
        except Exception:
            raise TokenInvalid("token missing iat/exp") from None
        if exp - iat > MAX_TTL_SECONDS or iat > now + CLOCK_SKEW_SECONDS:
            raise TokenInvalid("token lifetime or issue time out of policy")
        if now >= exp + CLOCK_SKEW_SECONDS:
            raise TokenExpired("capability token expired", workload=workload)
        if body.get("wl") != workload or body.get("tn") != tenant:
            raise TokenInvalid("token subject mismatch", workload=workload)
        caps = frozenset(body.get("cap") or [])
        if capability not in caps:
            raise TokenInvalid("token does not grant capability", capability=capability)
        return Claims(workload, tenant, caps, iat, exp, str(body.get("jti")), str(body.get("kid")))
