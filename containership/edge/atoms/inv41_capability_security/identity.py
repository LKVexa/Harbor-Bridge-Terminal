"""External identity adapters and principal-to-authority binding (Section 11).

Core capability code never parses credentials.  An adapter validates a
credential and returns a minimal :class:`Principal`; the :class:`PrincipalBinder`
maps a principal to an Authority it created itself, so a textual principal ID
can never select or impersonate an existing domain.  Authentication success
never implies authorization: the bound Authority still grants only its policy.

``HmacTokenAdapter`` is a reference/test adapter (compact HMAC-signed JSON).
Production adapters (OIDC/JWT, mTLS/SPIFFE, attestation) are integration
work that is BLOCKED on the owner naming trust anchors (see BLOCKERS.json).
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass
from typing import Callable, Final, Mapping, Protocol

from .capabilities import Authority
from .errors import AuthenticationFailed, StaleState, Unavailable

PRINCIPAL_TYPES: Final[frozenset] = frozenset({
    "node", "workload", "service", "operator", "provider", "build-agent", "control-plane", "peer",
})
MAX_CACHE_AGE_S: Final[float] = 60.0


@dataclass(frozen=True)
class Principal:
    principal_id: str
    principal_type: str
    tenant: str
    environment: str
    issuer: str
    authenticated_at: float
    expires_at: float

    def canonical(self) -> str:
        return f"{self.issuer}|{self.tenant}|{self.environment}|{self.principal_type}|{self.principal_id}"


class IdentityAdapter(Protocol):
    def authenticate(self, credential: str) -> Principal: ...


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(claims: dict, key: bytes) -> str:
    body = base64.urlsafe_b64encode(json.dumps(claims, sort_keys=True).encode()).decode().rstrip("=")
    mac = hmac.new(key, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{mac}"


class HmacTokenAdapter:
    """Validates issuer, audience, subject, tenant, signature, nbf/exp, revocation and replay."""

    def __init__(self, *, issuer: str, audience: str, keys: Mapping[str, bytes], clock: Callable[[], float] = time.time,
                 max_skew: float = 30.0, available: Callable[[], bool] = lambda: True) -> None:
        self.issuer, self.audience, self.keys = issuer, audience, dict(keys)
        self.clock, self.max_skew, self.available = clock, max_skew, available
        self.revoked_subjects: set = set()
        self._seen_nonces: dict = {}
        self._lock = threading.Lock()

    def authenticate(self, credential: str) -> Principal:
        if not self.available():
            raise Unavailable("identity provider unavailable")  # fail closed, no cache for privileged binding
        if not isinstance(credential, str) or credential.count(".") != 1 or len(credential) > 8192:
            raise AuthenticationFailed("malformed credential")
        body, mac = credential.split(".")
        try:
            claims = json.loads(_b64d(body))
        except Exception:
            raise AuthenticationFailed("malformed credential") from None
        if not isinstance(claims, dict):
            raise AuthenticationFailed("malformed credential")
        key = self.keys.get(claims.get("kid"))
        if key is None or not hmac.compare_digest(hmac.new(key, body.encode(), hashlib.sha256).hexdigest(), mac):
            raise AuthenticationFailed("bad signature")
        now = self.clock()
        if claims.get("iss") != self.issuer:
            raise AuthenticationFailed("wrong issuer")
        aud = claims.get("aud")
        if aud != self.audience:
            raise AuthenticationFailed("wrong audience")
        for req in ("sub", "typ", "tenant", "env", "nbf", "exp", "nonce"):
            if req not in claims:
                raise AuthenticationFailed("incomplete claims")
        subs = claims["sub"]
        if not isinstance(subs, str):
            raise AuthenticationFailed("ambiguous identity")
        if claims["typ"] not in PRINCIPAL_TYPES:
            raise AuthenticationFailed("unknown principal type")
        if now + self.max_skew < claims["nbf"]:
            raise AuthenticationFailed("not yet valid")
        if now - self.max_skew >= claims["exp"]:
            raise StaleState("credential expired")
        if subs in self.revoked_subjects:
            raise AuthenticationFailed("credential revoked")
        with self._lock:
            # prune expired nonces to bound memory
            for n, exp in list(self._seen_nonces.items()):
                if exp < now - self.max_skew:
                    del self._seen_nonces[n]
            if claims["nonce"] in self._seen_nonces:
                raise AuthenticationFailed("replayed credential")
            self._seen_nonces[claims["nonce"]] = claims["exp"]
        return Principal(subs, claims["typ"], claims["tenant"], claims["env"], self.issuer, now, float(claims["exp"]))


class PrincipalBinder:
    """Maps authenticated principals to authority domains this binder minted."""

    def __init__(self, bootstrap: Mapping[str, Mapping[str, set]]) -> None:
        # bootstrap: canonical principal key -> policy.  Unknown principals get nothing.
        self._bootstrap = {k: dict(v) for k, v in bootstrap.items()}
        self._domains: dict = {}
        self._lock = threading.Lock()

    def bind(self, principal: Principal, *, now: float | None = None) -> Authority:
        if not isinstance(principal, Principal):
            raise AuthenticationFailed("unauthenticated principal")
        if (now if now is not None else time.time()) >= principal.expires_at:
            raise StaleState("principal expired")
        key = principal.canonical()
        policy = self._bootstrap.get(key)
        if policy is None:
            raise AuthenticationFailed("principal has no authority binding")
        with self._lock:
            auth = self._domains.get(key)
            if auth is None:
                auth = Authority(policy)  # random id: textual ids never select a domain
                self._domains[key] = auth
            return auth

    def terminate(self, principal: Principal) -> None:
        """Drop the binding (credential revoked/rotated).  A new bind mints a new domain."""
        with self._lock:
            self._domains.pop(principal.canonical(), None)
