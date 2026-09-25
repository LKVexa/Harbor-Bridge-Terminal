"""Authentication and capability-based authorization for INV-25 catalogue operations.

Stdlib-only reference implementation of the boundary in docs/authn-authz.md.
Tokens are HMAC-SHA256 signed claim sets (issuer, subject, audience, capabilities,
environments, nbf/exp, nonce).  Production deployments substitute their workload
identity provider by implementing the same :class:`Verifier` interface; the
semantics (fail closed, anti-replay, deny-by-default) are what is certified.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Iterable

from .errors import Inv25Error

POLICY_REVISION = "INV25-AUTHZ/1"

CAPABILITIES = frozenset({
    "catalogue.read", "catalogue.export", "catalogue.audit",
    "catalogue.register", "catalogue.replace", "catalogue.widen",
    "catalogue.approve", "catalogue.activate", "catalogue.rollback",
    "catalogue.emergency_disable",
})
MUTATING = frozenset(CAPABILITIES - {"catalogue.read", "catalogue.export", "catalogue.audit"})


class Unauthenticated(Inv25Error):
    code = "INV25_UNAUTHENTICATED"


class Unauthorized(Inv25Error):
    code = "INV25_UNAUTHORIZED"


class ReplayDetected(Inv25Error):
    code = "INV25_REPLAY_DETECTED"


@dataclass(frozen=True)
class Principal:
    subject: str
    issuer: str
    capabilities: frozenset[str]
    environments: frozenset[str]
    break_glass: bool = False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    subject: str
    capability: str
    environment: str
    reason: str
    policy_revision: str = POLICY_REVISION


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def mint_token(key: bytes, *, key_id: str, issuer: str, subject: str, audience: str,
               capabilities: Iterable[str], environments: Iterable[str], ttl: int = 300,
               nonce: str, now: float | None = None, break_glass: bool = False) -> str:
    """Mint a signed token (used by tests and by an issuer implementing this format)."""
    now = time.time() if now is None else now
    claims = {"kid": key_id, "iss": issuer, "sub": subject, "aud": audience,
              "cap": sorted(capabilities), "env": sorted(environments),
              "nbf": int(now), "exp": int(now) + ttl, "nonce": nonce, "bg": break_glass}
    body = json.dumps(claims, sort_keys=True, separators=(",", ":")).encode()
    sig = hmac.new(key, body, hashlib.sha256).digest()
    return _b64(body) + "." + _b64(sig)


@dataclass
class Verifier:
    """Verifies tokens. Fails closed on any missing trust input."""

    audience: str
    keys: dict[str, tuple[str, bytes]]            # kid -> (issuer, key)
    revoked_subjects: set[str] = field(default_factory=set)
    revoked_keys: set[str] = field(default_factory=set)
    clock: Callable[[], float] = time.time
    max_skew: int = 30
    max_token_bytes: int = 4096
    _seen: dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def verify(self, token: str | None) -> Principal:
        if not token or not isinstance(token, str):
            raise Unauthenticated("missing credential")
        if len(token) > self.max_token_bytes or token.count(".") != 1:
            raise Unauthenticated("malformed credential")
        try:
            now = float(self.clock())
        except Exception as exc:  # clock/time service unavailable -> fail closed
            raise Unauthenticated("clock unavailable") from exc
        body_b64, sig_b64 = token.split(".")
        try:
            body, sig = _unb64(body_b64), _unb64(sig_b64)
            claims = json.loads(body)
        except Exception as exc:
            raise Unauthenticated("malformed credential") from exc
        if not isinstance(claims, dict):
            raise Unauthenticated("malformed credential")
        kid = claims.get("kid")
        if kid not in self.keys or kid in self.revoked_keys:
            raise Unauthenticated("unknown or revoked signing key")
        issuer, key = self.keys[kid]
        if not hmac.compare_digest(hmac.new(key, body, hashlib.sha256).digest(), sig):
            raise Unauthenticated("bad signature")
        if claims.get("iss") != issuer:
            raise Unauthenticated("wrong issuer")
        if claims.get("aud") != self.audience:
            raise Unauthenticated("wrong audience")
        nbf, exp = claims.get("nbf"), claims.get("exp")
        if not isinstance(nbf, int) or not isinstance(exp, int):
            raise Unauthenticated("missing validity window")
        if now + self.max_skew < nbf:
            raise Unauthenticated("credential not yet valid")
        if now - self.max_skew >= exp:
            raise Unauthenticated("credential expired")
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub or sub in self.revoked_subjects:
            raise Unauthenticated("subject missing or revoked")
        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not nonce:
            raise Unauthenticated("missing nonce")
        with self._lock:
            for n, e in list(self._seen.items()):
                if e < now - self.max_skew:
                    del self._seen[n]
            if nonce in self._seen:
                raise ReplayDetected("credential nonce already used")
            self._seen[nonce] = exp
        caps = frozenset(c for c in claims.get("cap", []) if c in CAPABILITIES)
        envs = frozenset(e for e in claims.get("env", []) if isinstance(e, str))
        return Principal(sub, issuer, caps, envs, bool(claims.get("bg")))


def authorize(principal: Principal | None, capability: str, environment: str) -> Decision:
    """Deny-by-default capability check. Raises Unauthorized; returns the recorded decision."""
    if principal is None:
        raise Unauthenticated("no authenticated principal")
    if capability not in CAPABILITIES:
        raise Unauthorized(f"unknown capability {capability}", capability="unknown")
    if capability == "catalogue.emergency_disable" and not principal.break_glass:
        raise Unauthorized("emergency disable requires a break-glass credential")
    if capability not in principal.capabilities:
        raise Unauthorized(f"{principal.subject} lacks {capability}", capability=capability)
    if environment not in principal.environments and "*" not in principal.environments:
        raise Unauthorized(f"{principal.subject} not scoped to environment", capability=capability)
    return Decision(True, principal.subject, capability, environment, f"granted {capability}")
