"""Component 21 - deny-by-default RBAC + ABAC capability policy.

Policy model (``POLICY``, version PK_DYN_AUTHZ/1):
* A capability is ``action:resource_type`` (no wildcards allowed - checked).
* A role grants capabilities with a scope: ``tenant`` (principal.tenant must
  equal resource.tenant) or ``global`` (administrative).
* Explicit DENY rules (``DENY``) override any grant.
* ABAC conditions: resource ``residency`` must be in principal ``residencies``
  when both are present; principal ``authn_role`` (from authn claims) must be
  in the role's ``principal_types``.
* Anything not matched is denied (deny-by-default), including unknown roles,
  actions and resource types.  Every decision can be written to AuditLog.
* Privilege review: ``privilege_review`` lists grants never exercised in the
  audit log and roles holding global scope.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field

from .errors_catalog import error

ACTIONS = ("read", "grant_lease", "renew_lease", "release_lease", "scale", "read_cost", "set_quota",
           "admin_revoke", "heartbeat")
RESOURCES = ("lease", "pool", "cost", "quota", "identity", "node")

POLICY = {
    "version": "PK_DYN_AUTHZ/1",
    "roles": {
        "tenant_viewer": {"principal_types": ["controller"], "scope": "tenant",
                          "caps": ["read:lease", "read:pool", "read_cost:cost"]},
        "tenant_operator": {"principal_types": ["controller"], "scope": "tenant",
                            "caps": ["read:lease", "read:pool", "grant_lease:lease", "renew_lease:lease",
                                     "release_lease:lease", "scale:pool"]},
        "node_agent": {"principal_types": ["node"], "scope": "tenant",
                       "caps": ["renew_lease:lease", "heartbeat:node"]},
        "provider": {"principal_types": ["provider"], "scope": "global", "caps": ["read:pool"]},
        "platform_admin": {"principal_types": ["controller"], "scope": "global",
                           "caps": ["read:lease", "read:pool", "read_cost:cost", "set_quota:quota",
                                    "admin_revoke:identity", "scale:pool"]},
    },
    "deny": [
        {"cap": "grant_lease:lease", "when": {"resource.frozen": True}},
    ],
}


@dataclass(frozen=True)
class Principal:
    sub: str
    roles: tuple
    authn_role: str
    tenant: str | None = None
    residencies: tuple = ()


@dataclass
class Decision:
    allow: bool
    reason: str
    rule: str | None = None
    details: dict = field(default_factory=dict)


def validate_policy(policy: dict = POLICY) -> list[str]:
    probs = []
    for name, r in policy["roles"].items():
        if r["scope"] not in ("tenant", "global"):
            probs.append(f"{name}: bad scope")
        for cap in r["caps"]:
            a, _, t = cap.partition(":")
            if "*" in cap or a not in ACTIONS or t not in RESOURCES:
                probs.append(f"{name}: invalid capability {cap!r}")
    return probs


class Authorizer:
    def __init__(self, policy: dict = POLICY, *, audit=None, clock=None) -> None:
        probs = validate_policy(policy)
        if probs:
            raise ValueError("; ".join(probs))
        self.policy, self.audit, self.clock = policy, audit, clock

    def evaluate(self, p: Principal, action: str, resource: dict) -> Decision:
        cap = f"{action}:{resource.get('type')}"
        d = self._decide(p, cap, resource)
        if self.audit is not None:
            self.audit.append(p.sub, "authz." + action, f"{resource.get('type')}/{resource.get('id')}",
                              "ALLOW" if d.allow else "DENY",
                              {"reason": d.reason, "rule": d.rule, "cap": cap},
                              ts=self.clock() if self.clock else None)
        return d

    def require(self, p: Principal, action: str, resource: dict) -> Decision:
        d = self.evaluate(p, action, resource)
        if not d.allow:
            raise error("INV08.AUTHZ.DENIED", f"{p.sub} may not {action} {resource.get('type')}",
                        details={"reason": d.reason})
        return d

    def _decide(self, p: Principal, cap: str, res: dict) -> Decision:
        for i, rule in enumerate(self.policy["deny"]):
            if rule["cap"] == cap and all(res.get(k.split(".", 1)[1]) == v for k, v in rule["when"].items()):
                return Decision(False, "explicit deny", f"deny[{i}]")
        if res.get("residency") and p.residencies and res["residency"] not in p.residencies:
            return Decision(False, "residency mismatch")
        for rn in sorted(p.roles):
            role = self.policy["roles"].get(rn)
            if role is None or cap not in role["caps"] or p.authn_role not in role["principal_types"]:
                continue
            if role["scope"] == "global":
                return Decision(True, "global grant", rn)
            if p.tenant and res.get("tenant") == p.tenant:
                return Decision(True, "tenant grant", rn)
        return Decision(False, "no matching grant (deny by default)")

    def matrix(self) -> dict:
        """role -> capability -> scope for every action x resource (None = denied)."""
        out = {}
        for rn, r in sorted(self.policy["roles"].items()):
            out[rn] = {f"{a}:{t}": (r["scope"] if f"{a}:{t}" in r["caps"] else None)
                       for a in ACTIONS for t in RESOURCES}
        return out


def privilege_review(policy: dict, audit_path) -> dict:
    used: dict[str, set] = {}
    with open(audit_path, "rb") as fh:
        for line in fh:
            e = json.loads(line)
            if e.get("outcome") == "ALLOW" and e["details"].get("rule"):
                used.setdefault(e["details"]["rule"], set()).add(e["details"]["cap"])
    unused = {rn: sorted(set(r["caps"]) - used.get(rn, set())) for rn, r in sorted(policy["roles"].items())}
    return {"unused_grants": {k: v for k, v in unused.items() if v},
            "global_roles": sorted(rn for rn, r in policy["roles"].items() if r["scope"] == "global")}
