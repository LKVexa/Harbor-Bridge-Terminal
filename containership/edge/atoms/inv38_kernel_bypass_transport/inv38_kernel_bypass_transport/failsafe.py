"""INV-38-C048 — Safe behaviour when trust dependencies are unavailable."""
from __future__ import annotations
from dataclasses import dataclass

DEPENDENCIES = ("identity", "attestation", "policy", "key", "time")

@dataclass(frozen=True)
class DepStatus:
    name: str
    available: bool
    cache_age: float
    max_cache_age: float

def may_continue(dep: DepStatus) -> tuple[bool, str]:
    """Cached credentials/policy may be used only within a bounded age."""
    if dep.available:
        return True, "PK_BYPASS_OK"
    if dep.cache_age <= dep.max_cache_age:
        return True, f"PK_BYPASS_DEGRADED_CACHED:{dep.name}"
    return False, f"PK_BYPASS_FAIL_CLOSED:{dep.name}"

def fast_path_permitted(deps: list[DepStatus]) -> tuple[bool, str]:
    """Fast path resumes only when every dependency is fresh (C048-T06)."""
    for d in deps:
        ok, reason = may_continue(d)
        if not ok:
            return False, reason
        if not d.available:            # degraded-cached: no NEW privileged fast path
            return False, f"PK_BYPASS_HOLD_FASTPATH:{d.name}"
    return True, "PK_BYPASS_OK"
