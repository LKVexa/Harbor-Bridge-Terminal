"""MC-06 / MC-21: authenticated principals, role checks and isolation scopes.

A ``Principal`` is only constructed from an authenticated source (mTLS peer
certificate via ``transport``, or a test fixture).  Every call names the scope
it touches; access requires the role AND matching environment/site/tenant.
Node identity is estate-level (contract.boundaries), so tenant scope applies to
workload identities and read APIs only.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .errors import fail

ROLES = {
    "enroll": "enroll nodes",
    "revoke": "revoke identities",
    "attest": "submit evidence for own node",
    "read": "read verdicts in scope",
    "policy_publish": "submit signed policy bundles",
    "quarantine_release": "release a quarantined node",
    "admin_config": "change signed configuration",
}


@dataclass(frozen=True)
class Principal:
    id: str
    roles: frozenset
    environments: frozenset = frozenset()
    sites: frozenset = frozenset({"*"})
    tenants: frozenset = frozenset({"*"})
    node: str | None = None  # set for node principals: may only attest as itself


@dataclass
class Authorizer:
    environment: str
    denials: list = field(default_factory=list)

    def require(self, p, role: str, *, site: str | None = None, tenant: str | None = None, node: str | None = None):
        if not isinstance(p, Principal):
            raise fail("E_UNAUTHENTICATED", "no authenticated principal")
        reason = None
        if role not in ROLES:
            reason = "unknown role"
        elif role not in p.roles:
            reason = f"missing role {role}"
        elif self.environment not in p.environments:
            reason = "environment out of scope"
        elif site is not None and "*" not in p.sites and site not in p.sites:
            reason = "site out of scope"
        elif tenant is not None and "*" not in p.tenants and tenant not in p.tenants:
            reason = "tenant out of scope"
        elif role == "attest" and (p.node is None or p.node != node):
            reason = "node principals may only attest as themselves"
        if reason:
            self.denials.append((p.id, role, reason))
            code = "E_TENANT_BOUNDARY" if "scope" in reason else "E_FORBIDDEN"
            raise fail(code, reason, principal=p.id, role=role)
        return p
