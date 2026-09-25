"""Authentication, authorization and tenant/workload identity (G14-P0-07, P0-08).

A caller presents a signed *capability token* (issuer = estate identity service).
The token binds a principal to a tenant set, scopes and an audience; it is checked
before any dependency is contacted.  Tenant and workload IDs are first-class in
the decision request and every artifact produced from it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .errors import G14Error
from .trust import KeyRing, check_fresh, exact_fields, ident, number

AUDIENCE = "gap14.data-gravity"
SCOPES = frozenset({
    "gravity:recommend",   # obtain a recommendation
    "gravity:handoff",     # hand an approved move-data to PLN-06
    "gravity:explain",     # read explain views
    "gravity:simulate",    # what-if API (non-executable)
    "gravity:admin",       # config activation / rollback
})
TOKEN_SCHEMA = "PK_CAPABILITY_TOKEN/1"
MAX_TOKEN_TTL_S = 3600.0


@dataclass(frozen=True)
class Principal:
    subject: str
    tenants: frozenset[str]
    scopes: frozenset[str]
    token_id: str
    issuer: str

    def require(self, scope: str, tenant: str | None = None) -> None:
        if scope not in self.scopes:
            raise G14Error("G14_FORBIDDEN", f"missing scope {scope}", details={"scope": scope, "subject": self.subject})
        if tenant is not None and tenant not in self.tenants and "*" not in self.tenants:
            raise G14Error("G14_FORBIDDEN", "principal not authorized for tenant", details={"subject": self.subject})


@dataclass(frozen=True)
class WorkloadIdentity:
    """Stable tenant/workload identity carried through the decision (P0-08)."""

    tenant_id: str
    workload_id: str
    environment: str = "production"

    @classmethod
    def parse(cls, raw: Mapping[str, Any]) -> "WorkloadIdentity":
        exact_fields(raw, "workload", ["tenant_id", "workload_id"], ["environment"])
        env = raw.get("environment", "production")
        if env not in ("production", "staging", "development", "test"):
            raise G14Error("G14_INVALID_REQUEST", "invalid environment", details={"field": "workload.environment"})
        return cls(ident(raw["tenant_id"], "workload.tenant_id"), ident(raw["workload_id"], "workload.workload_id"), env)

    def as_dict(self) -> dict[str, str]:
        return {"tenant_id": self.tenant_id, "workload_id": self.workload_id, "environment": self.environment}


class Authenticator:
    def __init__(self, keyring: KeyRing, issuer: str = "estate-identity", audience: str = AUDIENCE):
        self.keyring, self.issuer, self.audience = keyring, issuer, audience

    def mint(self, *, subject: str, tenants: list[str], scopes: list[str], kid: str, now: float,
             ttl_s: float = 900.0, token_id: str = "tok-1") -> dict[str, Any]:
        """Test/fixture helper: production tokens are minted by the identity service."""
        claims = {"schema": TOKEN_SCHEMA, "sub": subject, "tenants": sorted(tenants), "scopes": sorted(scopes),
                  "aud": self.audience, "iat": now, "exp": now + ttl_s, "jti": token_id}
        return {"claims": claims, "sig": self.keyring.sign(claims, kid)}

    def authenticate(self, token: Any, now: float) -> Principal:
        if token is None:
            raise G14Error("G14_UNAUTHENTICATED", "no capability token")
        try:
            exact_fields(token, "token", ["claims", "sig"])
            c = exact_fields(token["claims"], "token.claims", ["schema", "sub", "tenants", "scopes", "aud", "iat", "exp", "jti"])
        except G14Error as exc:
            raise G14Error("G14_UNAUTHENTICATED", "malformed token", details=exc.details) from None
        self.keyring.verify(c, token["sig"], expected_issuer=self.issuer, now=now)
        if c["schema"] != TOKEN_SCHEMA or c["aud"] != self.audience:
            raise G14Error("G14_UNAUTHENTICATED", "token schema/audience mismatch")
        iat, exp = number(c["iat"], "token.iat", maximum=1e11), number(c["exp"], "token.exp", maximum=1e11)
        if exp - iat > MAX_TOKEN_TTL_S or exp <= iat:
            raise G14Error("G14_UNAUTHENTICATED", "token lifetime invalid")
        if now >= exp:
            raise G14Error("G14_UNAUTHENTICATED", "token expired")
        check_fresh(iat, MAX_TOKEN_TTL_S, now, "capability token")
        if not isinstance(c["scopes"], list) or not isinstance(c["tenants"], list):
            raise G14Error("G14_UNAUTHENTICATED", "malformed scopes/tenants")
        scopes = frozenset(c["scopes"])
        if not scopes <= SCOPES:
            raise G14Error("G14_UNAUTHENTICATED", "unknown scope in token")
        tenants = frozenset(t if t == "*" else ident(t, "token.tenant") for t in c["tenants"])
        return Principal(ident(c["sub"], "token.sub"), tenants, scopes, ident(c["jti"], "token.jti"), self.issuer)
