"""Authentication integration (M07).

Production adapter: HMAC-SHA256 signed workload tokens issued by a configured
trust root (the shape an INV-60 fabric / SPIFFE-style issuer plugs into).  The
provider trusts identity ONLY after signature, issuer, audience, expiry and
replay (nonce) checks pass; any ambiguity fails closed.  mTLS peer verification
is configured separately in ``crypto/transport.py``.
"""
from __future__ import annotations

import base64
import heapq
import hashlib
import hmac
import json
import threading
import time
from dataclasses import dataclass, field

from ..errors.mapping import ProviderFault
from ..identity.context import FIELDS, IdentityContext

MAX_TOKEN = 4096
MAX_TTL_S = 3600
CLOCK_SKEW_S = 30


@dataclass
class TrustRoot:
    issuer: str
    keys: dict[str, bytes]  # kid -> key; >1 key during rotation
    audience: str
    revoked_kids: set[str] = field(default_factory=set)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    """Strict, canonical base64url: non-alphabet chars or non-canonical encodings are
    rejected (the stdlib decoder silently discards junk, which made tokens malleable
    -- found by fuzz/harness.py on 2026-09-22)."""
    raw = base64.b64decode(s.replace("-", "+").replace("_", "/") + "=" * (-len(s) % 4), validate=True)
    if _b64(raw) != s:
        raise ValueError("non-canonical base64url")
    return raw


def issue_token(root: TrustRoot, kid: str, identity: dict, *, ttl_s: int = 300, nonce: str, now: float | None = None,
                principal: str = "") -> str:
    """Test/fixture issuer (real issuance belongs to the identity plane)."""
    now = time.time() if now is None else now
    claims = {"iss": root.issuer, "aud": root.audience, "iat": int(now), "exp": int(now + ttl_s),
              "nonce": nonce, "kid": kid, "sub": principal or identity["component"], **{f: identity[f] for f in FIELDS}}
    body = _b64(json.dumps(claims, sort_keys=True, separators=(",", ":")).encode())
    sig = _b64(hmac.new(root.keys[kid], body.encode(), hashlib.sha256).digest())
    return f"{body}.{sig}"


class Authenticator:
    def __init__(self, root: TrustRoot, *, nonce_capacity: int = 100_000):
        self.root = root
        self._seen: dict[str, float] = {}
        self._expiry: list[tuple[float, str]] = []  # min-heap: O(log n) sweep instead of O(n) per call
        self._cap = nonce_capacity
        self._lock = threading.Lock()

    def authenticate(self, token: object, *, now: float | None = None) -> IdentityContext:
        now = time.time() if now is None else now
        if not isinstance(token, str) or not token or len(token) > MAX_TOKEN or token.count(".") != 1:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "malformed credential")
        body, sig = token.split(".")
        try:
            claims = json.loads(_unb64(body))
            got = _unb64(sig)
        except Exception:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "malformed credential") from None
        if not isinstance(claims, dict):
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "malformed credential")
        kid = claims.get("kid")
        key = self.root.keys.get(kid) if isinstance(kid, str) else None
        if key is None or kid in self.root.revoked_kids:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "unknown or revoked signing key")
        if not hmac.compare_digest(got, hmac.new(key, body.encode(), hashlib.sha256).digest()):
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "bad signature")
        if claims.get("iss") != self.root.issuer or claims.get("aud") != self.root.audience:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "issuer/audience mismatch")
        iat, exp = claims.get("iat"), claims.get("exp")
        if not isinstance(iat, int) or not isinstance(exp, int) or exp - iat > MAX_TTL_S:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "invalid validity window")
        if now > exp + CLOCK_SKEW_S or now < iat - CLOCK_SKEW_S:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "credential expired or not yet valid")
        nonce = claims.get("nonce")
        if not isinstance(nonce, str) or not 8 <= len(nonce) <= 128:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "missing nonce")
        with self._lock:
            while self._expiry and self._expiry[0][0] + CLOCK_SKEW_S < now:
                _, n = heapq.heappop(self._expiry)
                self._seen.pop(n, None)
            if nonce in self._seen:
                raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "replayed credential")
            if len(self._seen) >= self._cap:
                raise ProviderFault("PK_PROVIDER_OVERLOADED", "replay cache full")
            self._seen[nonce] = exp
            heapq.heappush(self._expiry, (exp, nonce))
        try:
            return IdentityContext(**{f: claims.get(f) for f in FIELDS}, authenticated=True,
                                   principal=str(claims.get("sub", ""))[:256])
        except Exception:
            raise ProviderFault("PK_PROVIDER_UNAUTHENTICATED", "identity claims invalid") from None
