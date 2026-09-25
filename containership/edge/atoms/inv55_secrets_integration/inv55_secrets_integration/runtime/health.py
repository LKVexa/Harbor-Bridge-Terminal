"""Health / readiness / status endpoint and stall detector (checklist #52, #71)."""
from __future__ import annotations

import os

from . import PROTOCOLS, RUNTIME_VERSION


def status(svc, *, stall_after_s: float = 30.0, provider_timeout_s: float = 1.0) -> dict:
    ph = svc.provider.health(timeout_s=provider_timeout_s)
    now = svc.clock()
    stalled = svc.inflight > 0 and svc.last_success_at is not None and now - svc.last_success_at > stall_after_s
    audit_ok = True
    if svc.audit.path:
        d = os.path.dirname(os.path.abspath(svc.audit.path))
        audit_ok = os.access(d, os.W_OK)
    checks = {
        "config_active": svc.cfg_digest is not None,
        "provider_healthy": ph.healthy,
        "circuit_closed": svc.breaker.state != "open",
        "audit_writable": audit_ok,
        "not_globally_frozen": "global" not in svc.quarantine.active(),
        "not_stalled": not stalled,
    }
    return {
        "live": True,
        "ready": all(checks.values()),
        "checks": checks,
        "version": RUNTIME_VERSION,
        "protocols": list(PROTOCOLS),
        "config_digest": svc.cfg_digest,
        "provider": {"kind": svc.provider.name, "healthy": ph.healthy, "sealed": ph.sealed, "detail": ph.detail,
                     "server_version": ph.version},
        "breaker": svc.breaker.state,
        "quarantine": sorted(svc.quarantine.active()),
        "audit_head": svc.audit.head,
        "cache_entries": len(svc.cache),
    }
