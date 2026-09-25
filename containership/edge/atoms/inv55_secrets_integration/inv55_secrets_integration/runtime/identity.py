"""Workload authentication at the boundary (checklist #18, #39, #41).

Compact signed workload tokens: ``base64url(claims).base64url(HMAC-SHA256)``.
Verification checks, in order: structure, key id known, signature (constant
time), issuer, audience, not-before / expiry with bounded skew, and the
subject pattern.  Any failure is ``INV55-E-UNAUTHENTICATED`` with a reason code
- never the token or the key.

This is the in-repo verifier for a symmetric trust root.  Production binding to
an external IdP / SPIFFE / Kubernetes service-account issuer is BLOCKED on an
issuer being provisioned (see WAIVERS.md W-003); the ``Verifier`` protocol is
the seam.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass

from ..reference import _SecretValue
from .errors import INV55Error

_SUBJECT = re.compile(r"^spiffe://[a-z0-9.-]+/(tenant/[a-z0-9-]+/)?workload/[A-Za-z0-9._-]{1,128}$")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass(frozen=True)
class Principal:
    subject: str          # spiffe://trust-domain/tenant/<t>/workload/<app>
    tenant: str
    app: str
    roles: frozenset[str]
    key_id: str


class HmacTokenVerifier:
    def __init__(self, keys: dict[str, str], *, issuer: str, audience: str, max_skew_s: float = 30.0,
                 max_lifetime_s: float = 3600.0, max_token_bytes: int = 4096):
        if not keys:
            raise INV55Error("INV55-E-CONFIG", "no verification keys")
        self._keys = {k: _SecretValue(v) for k, v in keys.items()}
        self.issuer, self.audience = issuer, audience
        self.max_skew_s, self.max_lifetime_s, self.max_token_bytes = max_skew_s, max_lifetime_s, max_token_bytes

    def issue(self, claims: dict, key_id: str) -> str:
        """Test/bootstrap helper - production tokens are minted by the IdP."""
        body = _b64(json.dumps({**claims, "kid": key_id}, sort_keys=True, separators=(",", ":")).encode())
        sig = hmac.new(self._keys[key_id]._reveal().encode(), body.encode(), hashlib.sha256).digest()
        return f"{body}.{_b64(sig)}"

    def verify(self, token: str, now: float) -> Principal:
        def deny(reason):
            raise INV55Error("INV55-E-UNAUTHENTICATED", reason, reason=reason)
        if not isinstance(token, str) or len(token) > self.max_token_bytes or token.count(".") != 1:
            deny("malformed_token")
        body, sig = token.split(".")
        try:
            claims = json.loads(_unb64(body))
            sigb = _unb64(sig)
        except Exception:
            deny("malformed_token")
        if not isinstance(claims, dict):
            deny("malformed_token")
        kid = claims.get("kid")
        key = self._keys.get(kid) if isinstance(kid, str) else None
        if key is None:
            deny("unknown_key")
        expect = hmac.new(key._reveal().encode(), body.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expect, sigb):
            deny("bad_signature")
        if claims.get("iss") != self.issuer:
            deny("wrong_issuer")
        if claims.get("aud") != self.audience:
            deny("wrong_audience")
        nbf, exp = claims.get("nbf"), claims.get("exp")
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in (nbf, exp)):
            deny("missing_time_claims")
        if exp - nbf > self.max_lifetime_s:
            deny("lifetime_too_long")
        if now + self.max_skew_s < nbf:
            deny("not_yet_valid")
        if now - self.max_skew_s >= exp:
            deny("expired")
        sub = claims.get("sub")
        if not isinstance(sub, str) or not _SUBJECT.fullmatch(sub):
            deny("bad_subject")
        m = re.search(r"/tenant/([a-z0-9-]+)/workload/([A-Za-z0-9._-]+)$", sub)
        tenant, app = (m.group(1), m.group(2)) if m else ("default", sub.rsplit("/", 1)[-1])
        roles = claims.get("roles") or []
        if not isinstance(roles, list) or not all(isinstance(r, str) for r in roles):
            deny("bad_roles")
        return Principal(sub, tenant, app, frozenset(roles), kid)


# Least-privilege role catalogue (checklist #39).  Roles grant verbs, never names;
# names come only from the per-secret scope policy (authz.py).
ROLES = {
    "secret-consumer": {"resolve", "use"},
    "secret-rotator": {"rotate"},
    "scope-admin": {"scope.read", "scope.write"},
    "operator": {"freeze", "unfreeze", "health.read"},
    "auditor": {"audit.read"},
}
