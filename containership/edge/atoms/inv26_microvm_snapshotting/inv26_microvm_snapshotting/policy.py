"""Deployment-tier applicability, conflict precedence, residency and
dependency-outage policy (C012, C018, C019, C048, C055, C056).

All three tables are data (exported to ``ops/policy.json`` and versioned with
:data:`POLICY_VERSION`), evaluated by the service before any side effect, and
every evaluation returns a decision record (see :mod:`explain`).
"""
from __future__ import annotations

from .errors import SnapshotServiceError

POLICY_VERSION = "PK_SNAPSHOT_POLICY/1.0.0"

# C012 -- operation support per tier: supported | degraded | prohibited
APPLICABILITY = {
    "cloud":      {"capture": "supported", "restore": "supported", "delete": "supported",
                   "replicate": "prohibited", "emergency_disable": "supported",
                   "min_kernel": "5.10", "kvm": True, "tpm_required": False,
                   "max_kms_outage_s": 0, "restore_p99_ms": 10.0},
    "datacenter": {"capture": "supported", "restore": "supported", "delete": "supported",
                   "replicate": "prohibited", "emergency_disable": "supported",
                   "min_kernel": "5.10", "kvm": True, "tpm_required": False,
                   "max_kms_outage_s": 0, "restore_p99_ms": 10.0},
    "near-edge":  {"capture": "supported", "restore": "supported", "delete": "supported",
                   "replicate": "prohibited", "emergency_disable": "supported",
                   "min_kernel": "5.10", "kvm": True, "tpm_required": True,
                   "max_kms_outage_s": 300, "restore_p99_ms": 25.0},
    "far-edge":   {"capture": "degraded", "restore": "supported", "delete": "supported",
                   "replicate": "prohibited", "emergency_disable": "supported",
                   "min_kernel": "5.10", "kvm": True, "tpm_required": True,
                   "max_kms_outage_s": 3600, "restore_p99_ms": 50.0},
}

# C019 -- lower number wins. Encoded, not interpreted by operators.
PRECEDENCE = [
    (1, "isolation_security", "tenant/workload/environment binding, authn/authz, integrity, entropy"),
    (2, "legal_residency", "site/region residency constraints"),
    (3, "integrity_consistency", "lifecycle, fencing, generation checks"),
    (4, "operator_safety", "quarantine, emergency disable, freeze"),
    (5, "slo_availability", "restore latency, retries, degraded operation"),
    (6, "cost_efficiency", "caching, pooling, compression"),
]

CONFLICTS = [
    {"id": "PC-01", "conflict": "restore SLO vs KMS unavailable",
     "winner": "isolation_security", "action": "refuse restore (SNAP_KMS_UNAVAILABLE); never restore without key unwrap"},
    {"id": "PC-02", "conflict": "capacity pressure vs tenant isolation",
     "winner": "isolation_security", "action": "shed load (SNAP_OVERLOADED); never share snapshots across tenants"},
    {"id": "PC-03", "conflict": "failover vs residency",
     "winner": "legal_residency", "action": "refuse restore outside allowed sites/regions (SNAP_RESIDENCY_VIOLATION)"},
    {"id": "PC-04", "conflict": "restore latency vs entropy reseed",
     "winner": "isolation_security", "action": "never resume a guest without entropy ack, even past budget"},
    {"id": "PC-05", "conflict": "availability vs audit sink down",
     "winner": "isolation_security", "action": "privileged ops (delete/quarantine/config/break-glass) refused; capture/restore buffered-audited"},
    {"id": "PC-06", "conflict": "operator emergency disable vs SLO",
     "winner": "operator_safety", "action": "all capture/restore refused (SNAP_DISABLED)"},
]

# C048 / C018 / C056 -- per-dependency outage handling
OUTAGE = {
    "identity":   {"mode": "fail_closed", "cache_ttl_s": 0, "note": "trust store is local; revocation list must be current"},
    "kms":        {"mode": "fail_closed", "cache_ttl_s": 0, "note": "no DEK caching; restore/capture refused"},
    "storage":    {"mode": "fail_closed", "cache_ttl_s": 0, "note": "retryable failure; nothing committed"},
    "hypervisor": {"mode": "fail_closed", "cache_ttl_s": 0, "note": "guest destroyed on any load/resume failure"},
    "entropy":    {"mode": "fail_closed", "cache_ttl_s": 0, "note": "guest destroyed; never resumed"},
    "audit":      {"mode": "buffer_then_fail_closed", "cache_ttl_s": 0,
                   "note": "bounded buffer for capture/restore; privileged ops fail closed"},
    "telemetry":  {"mode": "degrade", "cache_ttl_s": None, "note": "best-effort; never blocks operations"},
    "time":       {"mode": "fail_closed", "cache_ttl_s": 0,
                   "note": "credential validity uses +/-30 s skew; beyond it tokens are refused"},
    "control_plane": {"mode": "degrade", "cache_ttl_s": 900,
                      "note": "already-issued restore grants honoured until exp; no new grants offline"},
}


def check_tier(tier: str, operation: str) -> str:
    row = APPLICABILITY.get(tier)
    if row is None or row.get(operation) in (None, "prohibited"):
        raise SnapshotServiceError("SNAP_TIER_UNSUPPORTED", f"{operation} is not supported on tier {tier}")
    return row[operation]


def check_residency(cfg: dict, site: str | None, region: str | None = None) -> None:
    r = cfg["residency"]
    if site is not None and site not in r["allowed_sites"]:
        raise SnapshotServiceError("SNAP_RESIDENCY_VIOLATION", f"site {site} not permitted")
    if region is not None and region not in r["allowed_regions"]:
        raise SnapshotServiceError("SNAP_RESIDENCY_VIOLATION", f"region {region} not permitted")


def document() -> dict:
    return {"schema": POLICY_VERSION, "applicability": APPLICABILITY, "precedence": PRECEDENCE,
            "conflicts": CONFLICTS, "outage": OUTAGE}
