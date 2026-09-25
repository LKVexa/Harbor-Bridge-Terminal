"""MC13 - Authorization policy integration.

Explicit permissions for every privileged operation.  Policy is a versioned set of
grants ``(principal, permission, tenant, environment)``; ``*`` is allowed only for the
tenant/environment scope of break-glass operator principals and is itself audited.
Evaluation fails closed: no matching grant, an unknown permission, or a policy provider
error all deny.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .errors import AuthorizationError, ConfigError


class Permission(str, Enum):
    WRITE = "write"
    REPLICATE = "replicate"
    INSPECT_CONFLICTS = "inspect_conflicts"
    QUARANTINE_ADMIN = "quarantine_admin"
    RESOLVE = "resolve"
    RECONFIGURE = "reconfigure"
    RECOVER = "recover"
    READ = "read"


@dataclass(frozen=True)
class Grant:
    principal: str
    permission: Permission
    tenant: str
    environment: str

    def matches(self, principal: str, permission: Permission, tenant: str, environment: str) -> bool:
        return (self.principal == principal and self.permission == permission
                and self.tenant in (tenant, "*") and self.environment in (environment, "*"))


class Policy:
    def __init__(self, grants, *, version: str, wildcard_principals: frozenset = frozenset()):
        if not version:
            raise ConfigError("policy version required")
        self.version = version
        self.grants = tuple(grants)
        for g in self.grants:
            if not isinstance(g.permission, Permission):
                raise ConfigError(f"unknown permission {g.permission!r}")
            if (g.tenant == "*" or g.environment == "*") and g.principal not in wildcard_principals:
                raise ConfigError(f"wildcard scope granted to non-break-glass principal {g.principal}")
            if g.principal == "*":
                raise ConfigError("wildcard principal is never allowed")

    def decide(self, principal: str, permission, tenant: str, environment: str) -> dict:
        try:
            perm = Permission(permission)
        except ValueError:
            return {"allow": False, "reason": "unknown permission", "policy_version": self.version}
        for g in self.grants:
            if g.matches(principal, perm, tenant, environment):
                return {"allow": True, "reason": "grant", "policy_version": self.version,
                        "wildcard": g.tenant == "*" or g.environment == "*"}
        return {"allow": False, "reason": "no grant", "policy_version": self.version}


class Authorizer:
    def __init__(self, policy_provider, audit=None):
        self._provider = policy_provider
        self._audit = audit

    def require(self, principal: str, permission, tenant: str, environment: str) -> dict:
        try:
            decision = self._provider().decide(principal, permission, tenant, environment)
        except Exception as exc:  # provider outage -> deny (fail closed)
            decision = {"allow": False, "reason": f"policy unavailable: {type(exc).__name__}", "policy_version": None}
        if self._audit is not None and (not decision["allow"] or decision.get("wildcard")
                                        or permission not in (Permission.WRITE, Permission.REPLICATE, "write",
                                                              "replicate")):
            self._audit.append("authz", principal=principal, permission=str(getattr(permission, "value", permission)),
                               tenant=tenant, environment=environment, decision=decision)
        if not decision["allow"]:
            raise AuthorizationError(f"{principal} lacks {getattr(permission, 'value', permission)} on "
                                     f"{tenant}/{environment}: {decision['reason']}")
        return decision
