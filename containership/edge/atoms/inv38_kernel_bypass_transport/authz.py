"""INV-38-C023/C024/C044 — Authentication + capability authorization (model).

Model-level trust boundary enforcement: a Principal must be authenticated and
hold a Capability scoped to the tenant/workload before a privileged operation is
allowed.  MR keys are bound to (tenant, workload, generation).  All denials use
stable reason codes and allocate no resource before success (C023-T08/C044-T08).
"""
from __future__ import annotations

from dataclasses import dataclass, field

CAPABILITIES = frozenset({"register", "deregister", "post", "poll",
                          "configure", "drain", "reset", "diagnose", "administer"})


class AuthnError(PermissionError):
    code = "PK_BYPASS_AUTH_FAILED"


class AuthzError(PermissionError):
    code = "PK_BYPASS_UNAUTHORIZED"


@dataclass(frozen=True)
class Principal:
    identity: str
    tenant: str
    workload: str
    caps: frozenset[str]
    authenticated: bool = True
    expired: bool = False


@dataclass(frozen=True)
class MRKeyBinding:
    key: int
    tenant: str
    workload: str
    generation: int


def authenticate(p: Principal) -> Principal:
    if not p.authenticated or p.expired:
        raise AuthnError(f"principal {p.identity} not authenticated")
    return p


def authorize(p: Principal, capability: str, *, tenant: str, workload: str) -> None:
    authenticate(p)
    if capability not in CAPABILITIES:
        raise AuthzError(f"unknown capability {capability!r}")
    if capability not in p.caps:
        raise AuthzError(f"{p.identity} lacks {capability}")
    if p.tenant != tenant or p.workload != workload:
        raise AuthzError("identity/context mismatch")


def check_key(binding: MRKeyBinding, *, tenant: str, workload: str, generation: int) -> None:
    """Reject cross-tenant reuse and stale-generation keys (C024-T03/C058)."""
    if binding.tenant != tenant or binding.workload != workload:
        raise AuthzError("cross-tenant/workload key reuse")
    if binding.generation != generation:
        raise AuthzError("stale key generation")
