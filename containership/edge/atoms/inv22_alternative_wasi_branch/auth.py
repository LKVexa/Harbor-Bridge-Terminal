"""Authentication and capability authorization (MC-18, MC-19, MC-28 security precedence).

Authentication: Ed25519-signed identity tokens (``PK_BRANCH_ID/1``) validated
for issuer, audience, subject, expiry/not-before, key and replay.  This is the
reference mechanism for local/CLI and service calls; deployments may swap in
mTLS/OIDC behind the same ``Principal`` result.  There is no anonymous path.

Authorization: default-deny capability grants scoped by environment/site/
branch, separation of duties, and time-boxed audited break-glass.
"""
from __future__ import annotations

import base64
import fnmatch
from dataclasses import dataclass, field

from . import canonical
from .errors import Inv22Error

ACTIONS = frozenset({"matrix.read", "matrix.publish", "translation.execute", "cert.issue", "cert.revoke",
                     "cert.read", "policy.admin", "audit.read", "config.activate", "site.branch", "site.freeze",
                     "waiver.approve", "health.read"})
TOKEN_DOMAIN = b"PK_BRANCH_ID/1\n"


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset
    issuer: str
    kind: str  # "operator" | "service" | "ci"


class Authenticator:
    def __init__(self, *, audience: str, issuers: dict[str, dict], max_lifetime: int = 3600, skew: int = 60) -> None:
        """``issuers``: key_id -> {"issuer": str, "public_key": b64, "kinds": [..]}."""
        self.audience, self.issuers, self.max_lifetime, self.skew = audience, issuers, max_lifetime, skew
        self._seen: dict[str, int] = {}

    def authenticate(self, token: str | None, *, now: int | None) -> Principal:
        from .cert import HAVE_CRYPTO
        if not token:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "credentials required")
        if now is None:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "trusted time unavailable")
        if not HAVE_CRYPTO:
            raise Inv22Error("INV22.DEPENDENCY.UNAVAILABLE", "authentication backend unavailable")
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        try:
            body_b64, sig_b64 = token.split(".")
            body = base64.urlsafe_b64decode(body_b64 + "=" * (-len(body_b64) % 4))
            sig = base64.urlsafe_b64decode(sig_b64 + "=" * (-len(sig_b64) % 4))
            claims = canonical.loads(body, canonical.Limits(max_bytes=4096, max_depth=4, max_items=64, max_string=256))
        except Exception:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "malformed credentials") from None
        if not isinstance(claims, dict) or claims.get("typ") != "PK_BRANCH_ID/1" or claims.get("alg") != "Ed25519":
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "unsupported credential type/algorithm")
        key = self.issuers.get(str(claims.get("kid")))
        if key is None or key["issuer"] != claims.get("iss"):
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "unknown issuer or key")
        try:
            Ed25519PublicKey.from_public_bytes(base64.b64decode(key["public_key"])).verify(sig, TOKEN_DOMAIN + body)
        except (InvalidSignature, ValueError):
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "credential signature invalid") from None
        if claims.get("aud") != self.audience:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "wrong audience")
        nbf, exp, jti = claims.get("nbf"), claims.get("exp"), claims.get("jti")
        if not isinstance(nbf, int) or not isinstance(exp, int) or not isinstance(jti, str) or not jti:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "missing required claims")
        if exp - nbf > self.max_lifetime:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "credential lifetime exceeds policy")
        if now + self.skew < nbf:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "credential not yet valid")
        if now - self.skew >= exp:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "credential expired")
        self._seen = {k: v for k, v in self._seen.items() if v > now - self.skew}
        if jti in self._seen:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "credential replay detected")
        self._seen[jti] = exp
        kind = claims.get("kind")
        if not isinstance(kind, str) or kind not in key.get("kinds", ()):
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "issuer not trusted for this principal kind")
        sub, roles = claims.get("sub"), claims.get("roles", [])
        if not isinstance(sub, str) or not sub or not isinstance(roles, list):
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "malformed subject/roles")
        return Principal(sub, frozenset(map(str, roles)), claims["iss"], kind)


def mint_token(private_key, *, kid: str, iss: str, sub: str, aud: str, roles: list[str], kind: str,
               nbf: int, exp: int, jti: str) -> str:
    """Issue a token (identity-provider/test helper; not used by verifying services)."""
    body = canonical.dumps({"typ": "PK_BRANCH_ID/1", "alg": "Ed25519", "kid": kid, "iss": iss, "sub": sub,
                            "aud": aud, "roles": sorted(roles), "kind": kind, "nbf": nbf, "exp": exp, "jti": jti})
    sig = private_key.sign(TOKEN_DOMAIN + body)
    enc = lambda b: base64.urlsafe_b64encode(b).decode().rstrip("=")  # noqa: E731
    return f"{enc(body)}.{enc(sig)}"


@dataclass(frozen=True)
class Grant:
    role: str
    action: str
    scope: str = "*"          # e.g. "env:prod/site:edge-1/branch:fork"; fnmatch within one tenant


@dataclass
class BreakGlass:
    subject: str
    action: str
    scope: str
    expires_at: int
    reason: str


@dataclass
class Policy:
    grants: list[Grant]
    version: int = 1
    break_glass: list[BreakGlass] = field(default_factory=list)
    # action pairs one subject may not both perform on the same object
    separation: tuple = (("matrix.publish", "cert.issue"), ("cert.issue", "waiver.approve"))

    def __post_init__(self) -> None:
        for g in self.grants:
            if g.action not in ACTIONS:
                raise Inv22Error("INV22.CONFIG.INVALID", "unknown action in policy", {"action": g.action})
            if g.scope.count("*") and g.scope != "*" and "**" in g.scope:
                raise Inv22Error("INV22.CONFIG.INVALID", "recursive wildcards are not allowed in scopes")


class Authorizer:
    def __init__(self, policy: Policy, audit=None) -> None:
        self.policy, self.audit = policy, audit

    def authorize(self, principal: Principal | None, action: str, scope: str, *, now: int) -> str:
        """Return how access was granted ("grant" | "break-glass") or raise FORBIDDEN."""
        if principal is None:
            raise Inv22Error("INV22.AUTH.UNAUTHENTICATED", "no principal")
        if action not in ACTIONS:
            raise Inv22Error("INV22.AUTH.FORBIDDEN", "unknown action", {"action": action})
        if "*" in scope or "?" in scope or "[" in scope:
            raise Inv22Error("INV22.AUTH.FORBIDDEN", "request scope must be concrete")
        for g in self.policy.grants:
            if g.role in principal.roles and g.action == action and fnmatch.fnmatchcase(scope, g.scope):
                return "grant"
        for bg in self.policy.break_glass:
            if bg.subject == principal.subject and bg.action == action and fnmatch.fnmatchcase(scope, bg.scope):
                if now >= bg.expires_at:
                    continue
                if self.audit is not None:
                    self.audit.record_event(actor=principal.subject, action="auth.break_glass", obj=f"{action}@{scope}",
                                            after=bg.expires_at, reason=bg.reason)
                return "break-glass"
        raise Inv22Error("INV22.AUTH.FORBIDDEN", "no grant for action", {"action": action, "scope": scope})

    def check_separation(self, subject: str, action: str, prior_actors: dict[str, str]) -> None:
        """``prior_actors`` maps action -> subject that performed it on the same object."""
        for a, b in self.policy.separation:
            other = b if action == a else a if action == b else None
            if other and prior_actors.get(other) == subject:
                raise Inv22Error("INV22.AUTH.SEPARATION_OF_DUTIES", "same principal cannot perform both actions",
                                 {"action": action, "conflicts_with": other})
