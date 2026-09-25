"""Authentication boundary and identity federation (MC-015 / MC-031).

Callers are never identified by a caller-supplied string.  Every request must
carry a compact JWS bearer token (``header.payload.signature``) issued by a
configured trusted issuer.  Verification enforces:

* algorithm allow-list per issuer (``EdDSA`` via Ed25519, or ``HS256`` for
  in-cluster service tokens); ``none`` and algorithm confusion are rejected;
* ``iss`` must be a configured issuer, ``aud`` must contain our audience;
* ``exp``/``nbf``/``iat`` with bounded clock skew and a maximum token lifetime;
* single use of ``jti`` inside its lifetime (replay cache, bounded memory);
* subject type: ``user:``, ``service:`` (workload identity) — groups come from
  the ``groups`` claim and are intersected with configured group mappings.

OIDC/SAML front-ends terminate at an IdP that mints these tokens; mTLS peer
identity from :mod:`http_api` is bound via the ``cnf`` (``x5t#S256``) claim when
present.  Key rotation: each issuer holds a ``kid``-indexed key set.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from .errors import fail

MAX_TOKEN_BYTES = 8192


def _b64d(part: str) -> bytes:
    pad = "=" * (-len(part) % 4)
    return base64.urlsafe_b64decode(part + pad)


def b64e(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


@dataclass(frozen=True)
class Principal:
    subject: str                 # "user:alice" / "service:ci-runner"
    issuer: str
    groups: frozenset[str] = frozenset()
    token_id: str = ""
    expires_at: int = 0
    cert_thumbprint: str | None = None

    @property
    def kind(self) -> str:
        return self.subject.split(":", 1)[0]


@dataclass
class Issuer:
    name: str
    algorithms: frozenset[str]
    keys: dict[str, bytes]               # kid -> HS256 secret or Ed25519 raw public key
    audience: str = "inv66-control-plane"


@dataclass
class Authenticator:
    issuers: Mapping[str, Issuer]
    audience: str = "inv66-control-plane"
    skew_s: int = 60
    max_lifetime_s: int = 3600
    replay_capacity: int = 100_000
    clock: Callable[[], float] = time.time
    _seen: "OrderedDict[str, int]" = field(default_factory=OrderedDict, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    def authenticate(self, token: str | None, *, peer_thumbprint: str | None = None) -> Principal:
        if not token:
            raise fail("AUTHN_MISSING", "no bearer token")
        if len(token) > MAX_TOKEN_BYTES or token.count(".") != 2:
            raise fail("AUTHN_INVALID", "malformed token")
        h64, p64, s64 = token.split(".")
        try:
            header = json.loads(_b64d(h64))
            claims = json.loads(_b64d(p64))
            sig = _b64d(s64)
        except Exception:
            raise fail("AUTHN_INVALID", "undecodable token") from None
        if not isinstance(header, dict) or not isinstance(claims, dict):
            raise fail("AUTHN_INVALID", "token segments must be objects")
        iss = claims.get("iss")
        issuer = self.issuers.get(iss) if isinstance(iss, str) else None
        if issuer is None:
            raise fail("AUTHN_INVALID", "untrusted issuer")
        alg, kid = header.get("alg"), header.get("kid")
        if alg not in issuer.algorithms or not isinstance(kid, str) or kid not in issuer.keys:
            raise fail("AUTHN_INVALID", "algorithm or key id not permitted for issuer")
        signing_input = f"{h64}.{p64}".encode()
        if not _verify_sig(alg, issuer.keys[kid], signing_input, sig):
            raise fail("AUTHN_INVALID", "bad signature")
        aud = claims.get("aud")
        auds = aud if isinstance(aud, list) else [aud]
        if self.audience not in auds:
            raise fail("AUTHN_INVALID", "audience mismatch")
        now = int(self.clock())
        exp, nbf, iat = claims.get("exp"), claims.get("nbf", claims.get("iat")), claims.get("iat")
        if not all(isinstance(x, int) and not isinstance(x, bool) for x in (exp, nbf, iat)):
            raise fail("AUTHN_INVALID", "exp/iat/nbf must be integers")
        if now > exp + self.skew_s or now + self.skew_s < nbf:
            raise fail("AUTHN_INVALID", "token outside validity window")
        if exp - iat > self.max_lifetime_s:
            raise fail("AUTHN_INVALID", "token lifetime exceeds policy")
        sub = claims.get("sub")
        if not isinstance(sub, str) or not sub.startswith(("user:", "service:")) or len(sub) > 262:
            raise fail("AUTHN_INVALID", "subject must be user:<id> or service:<id>")
        cnf = claims.get("cnf", {}).get("x5t#S256") if isinstance(claims.get("cnf"), dict) else None
        if cnf is not None and cnf != peer_thumbprint:
            raise fail("AUTHN_INVALID", "token bound to a different client certificate")
        jti = claims.get("jti")
        if not isinstance(jti, str) or not jti:
            raise fail("AUTHN_INVALID", "jti required")
        with self._lock:
            key = f"{iss}\0{jti}"
            # expire stale entries
            while self._seen and next(iter(self._seen.values())) < now - self.skew_s:
                self._seen.popitem(last=False)
            if key in self._seen:
                raise fail("AUTHN_REPLAY", "token already used")
            if len(self._seen) >= self.replay_capacity:
                raise fail("OVERLOADED", "replay cache saturated")
            self._seen[key] = exp
        groups = claims.get("groups", [])
        if not isinstance(groups, list) or not all(isinstance(g, str) for g in groups):
            raise fail("AUTHN_INVALID", "groups claim must be a list of strings")
        return Principal(sub, iss, frozenset(groups), jti, exp, peer_thumbprint)


def _verify_sig(alg: str, key: bytes, data: bytes, sig: bytes) -> bool:
    if alg == "HS256":
        return hmac.compare_digest(hmac.new(key, data, hashlib.sha256).digest(), sig)
    if alg == "EdDSA":
        from .provenance import ed25519_verify
        return ed25519_verify(key, data, sig)
    return False


def mint_token(alg: str, kid: str, key: bytes, claims: dict[str, Any]) -> str:
    """Mint a token (test/bootstrap helper; production tokens come from the IdP)."""
    h = b64e(json.dumps({"alg": alg, "kid": kid, "typ": "JWT"}).encode())
    p = b64e(json.dumps(claims).encode())
    data = f"{h}.{p}".encode()
    if alg == "HS256":
        sig = hmac.new(key, data, hashlib.sha256).digest()
    elif alg == "EdDSA":
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        sig = Ed25519PrivateKey.from_private_bytes(key).sign(data)
    else:
        raise ValueError(alg)
    return f"{h}.{p}.{b64e(sig)}"
