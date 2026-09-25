"""Deny-by-default, tenant-scoped capability authorization (MC-08; C024, C042-C043).

Policy document ``PK_APP_AUTHZ_POLICY/1`` (see ``schema/authz-policy-v1.schema.json``)::

    {"format": "PK_APP_AUTHZ_POLICY/1", "version": "2026-09-22.1",
     "grants": [{"id": "g1", "roles": ["app-submitter"], "capabilities": ["app.submit"],
                 "tenants": ["acme"], "environments": ["prod"], "sites": ["*"],
                 "resources": ["apps/*"], "kinds": ["human", "workload"]}],
     "separation_of_duties": [["release.approve", "admin.policy"]]}

Rules enforced here, all fail-closed:

* unknown capabilities are denied and cannot be granted (load fails);
* a grant never uses ``"*"`` for tenants — cross-tenant authority must name each
  tenant, and only ``service``/``node``/``breakglass`` identities may act on a
  tenant other than their own (no human or workload confused deputy);
* resource selectors are exact or a single trailing ``/*`` prefix;
* a policy that fails to parse/verify leaves the previous active policy in
  force; with no active policy every decision is ``authz.policy_invalid``;
* separation-of-duties pairs cannot both be granted to the same role/principal;
* ``breakglass`` capability requires a break-glass principal (short-lived token).

Manifest content never contributes to a decision: the manifest is an input to
be authorized, not a source of authority (extension fields cannot grant).
"""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from typing import Any, Mapping

from .errors import Inv64Error

POLICY_FORMAT = "PK_APP_AUTHZ_POLICY/1"
CAPABILITIES = frozenset({
    "app.submit", "app.validate", "app.canonicalize", "config.activate", "config.rollback",
    "config.overlay.write", "status.inspect", "diagnostics.read", "audit.read", "explain.read",
    "provider.bind", "admin.policy", "admin.trust", "release.approve", "rollout.promote", "breakglass",
})
CROSS_TENANT_KINDS = frozenset({"service", "node", "breakglass"})
MAX_GRANTS = 10_000


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: str | None
    reason: str
    capability: str
    tenant: str
    resource: str
    policy_version: str | None
    policy_digest: str | None
    grant_id: str | None = None

    def record(self, actor: str) -> dict:
        return {"actor": actor, "action": self.capability, "tenant": self.tenant, "resource": self.resource,
                "decision": "allow" if self.allowed else "deny", "reason": self.reason,
                "policy_version": self.policy_version, "policy_digest": self.policy_digest,
                "grant_id": self.grant_id}


class PolicyError(ValueError):
    pass


def _str_list(g: Mapping, key: str, *, required: bool = True) -> tuple[str, ...]:
    v = g.get(key, None if required else [])
    if not isinstance(v, list) or (required and not v) or not all(isinstance(x, str) and x for x in v):
        raise PolicyError(f"grant.{key} must be a non-empty list of strings")
    return tuple(v)


def load_policy(doc: Any) -> "Policy":
    if not isinstance(doc, dict) or doc.get("format") != POLICY_FORMAT:
        raise PolicyError("unsupported policy format")
    version = doc.get("version")
    if not isinstance(version, str) or not version:
        raise PolicyError("policy.version required")
    grants = doc.get("grants")
    if not isinstance(grants, list) or len(grants) > MAX_GRANTS:
        raise PolicyError("policy.grants must be a bounded list")
    parsed = []
    ids = set()
    for g in grants:
        if not isinstance(g, dict):
            raise PolicyError("grant must be a mapping")
        gid = g.get("id")
        if not isinstance(gid, str) or gid in ids:
            raise PolicyError("grant.id missing or duplicate")
        ids.add(gid)
        caps = _str_list(g, "capabilities")
        unknown = set(caps) - CAPABILITIES
        if unknown:
            raise PolicyError(f"unknown capabilities {sorted(unknown)}")
        tenants = _str_list(g, "tenants")
        if "*" in tenants or any("*" in t for t in tenants):
            raise PolicyError("tenant wildcards are prohibited")
        resources = _str_list(g, "resources")
        for r in resources:
            if "*" in r and not (r == "*" or (r.endswith("/*") and "*" not in r[:-2])):
                raise PolicyError(f"illegal resource selector {r!r}")
        roles = _str_list(g, "roles", required=False)
        principals = _str_list(g, "principals", required=False)
        if not roles and not principals:
            raise PolicyError("grant must name roles or principals")
        parsed.append({
            "id": gid, "capabilities": frozenset(caps), "tenants": frozenset(tenants),
            "environments": _str_list(g, "environments"), "sites": _str_list(g, "sites"),
            "resources": resources, "roles": frozenset(roles), "principals": frozenset(principals),
            "kinds": frozenset(_str_list(g, "kinds", required=False)),
        })
    sod = doc.get("separation_of_duties", [])
    if not isinstance(sod, list) or not all(isinstance(p, list) and len(p) == 2 for p in sod):
        raise PolicyError("separation_of_duties must be a list of pairs")
    for a, b in sod:
        if a not in CAPABILITIES or b not in CAPABILITIES:
            raise PolicyError("separation_of_duties names unknown capability")
        by_holder: dict[str, set] = {}
        for g in parsed:
            for h in [f"role:{r}" for r in g["roles"]] + [f"principal:{p}" for p in g["principals"]]:
                by_holder.setdefault(h, set()).update(g["capabilities"])
        for holder, caps in by_holder.items():
            if a in caps and b in caps:
                raise PolicyError(f"separation of duties violated for {holder}: {a} + {b}")
    digest = hashlib.sha256(json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return Policy(version, digest, tuple(parsed), tuple(tuple(p) for p in sod))


@dataclass(frozen=True)
class Policy:
    version: str
    digest: str
    grants: tuple
    sod: tuple


def _match(selector: str, value: str) -> bool:
    if selector == "*":
        return True
    if selector.endswith("/*"):
        return value.startswith(selector[:-1])
    return selector == value


class Authorizer:
    """Holds the active policy; activation is atomic, rollback restores the prior one."""

    def __init__(self, policy_doc: Any | None = None, *, audit=None, metrics=None):
        self._lock = threading.Lock()
        self._active: Policy | None = None
        self._previous: Policy | None = None
        self._audit = audit
        self._metrics = metrics
        if policy_doc is not None:
            self.activate(policy_doc)

    @property
    def policy(self) -> Policy | None:
        return self._active

    def activate(self, doc: Any, *, actor: str = "inv64") -> Policy:
        try:
            new = load_policy(doc)  # raises PolicyError; active policy unchanged
        except PolicyError as exc:
            if self._audit is not None:
                self._audit.append("policy.activate", actor=actor, outcome="rejected", reason=str(exc)[:200])
            raise
        with self._lock:
            if self._audit is not None:  # a policy change must not happen unaudited
                self._audit.append("policy.activate", actor=actor, outcome="active", resource=new.version,
                                   fail_closed=True, digest=new.digest,
                                   previous=self._active.version if self._active else None)
            self._previous, self._active = self._active, new
        return new

    def rollback(self, *, actor: str = "inv64") -> Policy:
        with self._lock:
            if self._previous is None:
                raise Inv64Error("activation.no_known_good")
            if self._audit is not None:
                self._audit.append("policy.rollback", actor=actor, outcome="active", resource=self._previous.version,
                                   fail_closed=True, from_version=self._active.version)
            self._active, self._previous = self._previous, self._active
            return self._active

    def decide(self, principal, capability: str, *, tenant: str, environment: str, site: str,
               resource: str) -> Decision:
        pol = self._active
        if pol is None:
            d = Decision(False, "authz.policy_invalid", "no verified policy active", capability, tenant,
                         resource, None, None)
        elif capability not in CAPABILITIES:
            d = Decision(False, "authz.denied", "unknown capability", capability, tenant, resource,
                         pol.version, pol.digest)
        elif capability == "breakglass" and not principal.breakglass:
            d = Decision(False, "authz.denied", "breakglass requires a break-glass credential", capability,
                         tenant, resource, pol.version, pol.digest)
        elif tenant != principal.tenant and principal.kind not in CROSS_TENANT_KINDS:
            d = Decision(False, "tenant.mismatch", "identity may act only in its own tenant", capability,
                         tenant, resource, pol.version, pol.digest)
        else:
            d = Decision(False, "authz.denied", "no matching grant", capability, tenant, resource,
                         pol.version, pol.digest)
            for g in pol.grants:
                holder = principal.subject in g["principals"] or bool(g["roles"] & set(principal.roles))
                if not holder or capability not in g["capabilities"] or tenant not in g["tenants"]:
                    continue
                if g["kinds"] and principal.kind not in g["kinds"]:
                    continue
                if not any(_match(e, environment) for e in g["environments"]):
                    continue
                if not any(_match(s, site) for s in g["sites"]):
                    continue
                if not any(_match(r, resource) for r in g["resources"]):
                    continue
                d = Decision(True, None, "granted", capability, tenant, resource, pol.version, pol.digest, g["id"])
                break
        if self._metrics is not None:
            self._metrics.inc("inv64_authz_decisions_total", decision="allow" if d.allowed else "deny")
        if self._audit is not None:
            rec = d.record(principal.subject)
            self._audit.append("authz", actor=principal.subject, tenant=tenant,
                               outcome="allowed" if d.allowed else "denied",
                               **{k: v for k, v in rec.items() if k not in ("actor", "tenant")})
        return d

    def require(self, principal, capability: str, **scope) -> Decision:
        d = self.decide(principal, capability, **scope)
        if not d.allowed:
            raise Inv64Error(d.code or "authz.denied",
                             details={"capability": capability, "policy_version": d.policy_version})
        return d
