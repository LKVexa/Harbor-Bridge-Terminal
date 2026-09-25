"""Issuance policy, delegation limits, quota and constraint precedence
(MC-04, MC-15, MC-36, MC-62, MC-63).

``IssuancePolicy`` is the in-package reference authorizer.  A GAP-13 policy
engine plugs in through the ``PolicyEngine`` protocol; the service always asks
the engine and fails closed if it errors.  Precedence when rules conflict is
fixed and documented (``PRECEDENCE``): security > residency > SLO > cost.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Mapping, Protocol

from .grants import MAX_DELEGATION_DEPTH, Grant, SecurityPlaneError
from .identity import Principal

PRECEDENCE = ("security", "residency", "slo", "cost")


class PolicyDenied(SecurityPlaneError):
    code = "policy.denied"


class QuotaExceeded(SecurityPlaneError):
    code = "policy.quota"


@dataclass(frozen=True)
class Decision:
    allow: bool
    rule: str
    category: str = "security"
    reason: str = ""


class PolicyEngine(Protocol):
    def authorize_issue(self, principal: Principal, request: Mapping) -> Decision: ...


def resolve(decisions: list[Decision]) -> Decision:
    """Combine decisions: any deny wins; among denies the highest-precedence
    category is reported; with no decisions the result is deny (fail closed)."""
    if not decisions:
        return Decision(False, "default-deny", "security", "no applicable rule")
    denies = [d for d in decisions if not d.allow]
    if denies:
        return min(denies, key=lambda d: PRECEDENCE.index(d.category) if d.category in PRECEDENCE else 99)
    return decisions[0]


@dataclass
class IssuancePolicy:
    """Declarative reference policy.

    * ``issuers`` - role that may issue root grants.
    * ``tenant_capabilities`` - capabilities each tenant may ever hold.
    * ``max_ttl`` - maximum lifetime of a root grant (seconds).
    * ``depth_limits`` - per ``tenant``/``tenant:capability``/``env:<name>`` key;
      the smallest applicable limit wins, capped by MAX_DELEGATION_DEPTH.
    * ``residency`` - environment -> permitted sites.
    """

    issuer_role: str = "grant-issuer"
    tenant_capabilities: Mapping[str, frozenset[str]] = field(default_factory=dict)
    max_ttl: int = 3600
    depth_limits: Mapping[str, int] = field(default_factory=dict)
    residency: Mapping[str, frozenset[str]] = field(default_factory=dict)

    def authorize_issue(self, principal: Principal, request: Mapping) -> Decision:
        decisions: list[Decision] = []
        tenant = request["tenant"]
        if self.issuer_role not in principal.roles:
            decisions.append(Decision(False, "issuer-role", "security", "caller may not issue"))
        if principal.tenant != tenant:
            decisions.append(Decision(False, "tenant-bound", "security", "caller tenant mismatch"))
        allowed = self.tenant_capabilities.get(tenant, frozenset())
        extra = set(request["scope"]) - set(allowed)
        if extra:
            decisions.append(Decision(False, "tenant-capabilities", "security",
                                      f"capabilities not permitted: {sorted(extra)}"))
        ttl = request["not_after"] - request["now"]
        if ttl <= 0 or ttl > self.max_ttl:
            decisions.append(Decision(False, "max-ttl", "security", f"ttl {ttl} outside (0,{self.max_ttl}]"))
        env, site = request.get("environment"), request.get("site")
        if env in self.residency and site not in self.residency[env]:
            decisions.append(Decision(False, "residency", "residency", f"site {site!r} not permitted in {env!r}"))
        decisions.append(Decision(True, "baseline", "security"))
        return resolve(decisions)

    def depth_limit(self, grant: Grant) -> int:
        keys = [grant.tenant] + [f"{grant.tenant}:{c}" for c in grant.scope]
        if grant.environment:
            keys.append(f"env:{grant.environment}")
        limits = [self.depth_limits[k] for k in keys if k in self.depth_limits]
        return min([MAX_DELEGATION_DEPTH, *limits])


@dataclass
class QuotaLimiter:
    """Per-tenant outstanding-issuance quota with fair-share accounting."""

    per_tenant: Mapping[str, int] = field(default_factory=dict)
    default: int = 1000
    _used: dict[str, int] = field(default_factory=dict, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False, repr=False)

    def acquire(self, tenant: str) -> None:
        with self._lock:
            limit = self.per_tenant.get(tenant, self.default)
            used = self._used.get(tenant, 0)
            if used >= limit:
                raise QuotaExceeded("tenant issuance quota exhausted",
                                    details={"tenant": tenant, "limit": limit})
            self._used[tenant] = used + 1

    def release(self, tenant: str) -> None:
        with self._lock:
            if self._used.get(tenant, 0) > 0:
                self._used[tenant] -= 1

    def usage(self) -> dict[str, int]:
        with self._lock:
            return dict(self._used)
