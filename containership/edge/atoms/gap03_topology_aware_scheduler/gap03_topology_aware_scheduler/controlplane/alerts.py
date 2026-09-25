"""MC-023 - Dashboards and alert definitions as code (GAP03-OPS/1).

Alerts classify failure as overload / policy / dependency / stale-state /
security / software-defect, use multi-window multi-burn-rate SLO rules,
carry owner/severity/runbook/first-diagnostics, and honour maintenance
signals (suppression, not deletion).  ``evaluate`` is a tiny rule engine used
to replay synthetic incidents in tests.
"""
from __future__ import annotations

OWNER = "team:gap03-scheduler (UNASSIGNED - see governance/OWNERS.json)"
RUNBOOK = "runbooks/"

ALERTS = [
    {"alert": "GAP03SLOBurnFast", "class": "availability", "severity": "page",
     "windows": [["1h", 14.4], ["5m", 14.4]], "signal": "error_ratio", "slo": 0.999, "runbook": RUNBOOK + "slo-burn.md"},
    {"alert": "GAP03SLOBurnSlow", "class": "availability", "severity": "ticket",
     "windows": [["6h", 6.0], ["30m", 6.0]], "signal": "error_ratio", "slo": 0.999, "runbook": RUNBOOK + "slo-burn.md"},
    {"alert": "GAP03Overload", "class": "overload", "severity": "page", "signal": "overload_ratio", "threshold": 0.05,
     "for_s": 300, "runbook": RUNBOOK + "overload.md"},
    {"alert": "GAP03PolicyDenialSpike", "class": "policy", "severity": "ticket", "signal": "fairness_denial_ratio",
     "threshold": 0.5, "for_s": 900, "runbook": RUNBOOK + "fairness.md"},
    {"alert": "GAP03DependencyDown", "class": "dependency", "severity": "page", "signal": "dependency_down", "threshold": 1,
     "for_s": 60, "runbook": RUNBOOK + "degraded-mode.md"},
    {"alert": "GAP03FencingRejections", "class": "stale_state", "severity": "page", "signal": "fenced_writes", "threshold": 1,
     "for_s": 0, "runbook": RUNBOOK + "split-brain.md"},
    {"alert": "GAP03AuditWriteFailure", "class": "security", "severity": "page", "signal": "audit_write_failures",
     "threshold": 1, "for_s": 0, "runbook": RUNBOOK + "audit.md"},
    {"alert": "GAP03ReconciliationDrift", "class": "stale_state", "severity": "ticket", "signal": "drift_events",
     "threshold": 5, "for_s": 600, "runbook": RUNBOOK + "reconciliation.md"},
    {"alert": "GAP03OrphanTransactions", "class": "stale_state", "severity": "ticket", "signal": "orphan_txns",
     "threshold": 10, "for_s": 600, "runbook": RUNBOOK + "transactions.md"},
    {"alert": "GAP03StaleTopology", "class": "stale_state", "severity": "ticket", "signal": "topology_age_s",
     "threshold": 600, "for_s": 300, "runbook": RUNBOOK + "topology.md"},
    {"alert": "GAP03AuthFailures", "class": "security", "severity": "page", "signal": "auth_failures_per_min",
     "threshold": 50, "for_s": 120, "runbook": RUNBOOK + "security.md"},
    {"alert": "GAP03InternalErrors", "class": "software_defect", "severity": "page", "signal": "internal_errors_per_min",
     "threshold": 1, "for_s": 300, "runbook": RUNBOOK + "software-defect.md"},
    {"alert": "GAP03SaturationHigh", "class": "overload", "severity": "ticket", "signal": "utilization", "threshold": 0.8,
     "for_s": 900, "runbook": RUNBOOK + "capacity.md"},
]
for _a in ALERTS:
    _a.setdefault("owner", OWNER)
    _a.setdefault("escalation", "secondary on-call after 15 min unacknowledged")
    _a.setdefault("first_diagnostics", "GET /healthz/deep; gap03 explain --since 15m; check gap03_dependency_up")

ENV_THRESHOLDS = {"prod": 1.0, "staging": 2.0, "dev": 10.0}

DASHBOARD = {
    "title": "GAP-03 Topology-aware scheduler", "version": 1,
    "rows": [
        {"title": "Golden signals", "panels": ["gap03_requests_total", "gap03_score_latency_ms", "gap03_commit_latency_ms",
                                               "gap03_admission_rejected_total"]},
        {"title": "Correctness & fairness", "panels": ["gap03_fairness_denials_total", "gap03_starved_tenants",
                                                       "gap03_reservation_utilization_ratio", "gap03_stale_rejections_total"]},
        {"title": "State & coordination", "panels": ["gap03_coordination_term", "gap03_coordination_is_leader",
                                                     "gap03_orphaned_reservations", "gap03_reconciliation_drift_total",
                                                     "gap03_generation_lag", "gap03_store_write_latency_ms"]},
        {"title": "Capacity headroom", "panels": ["gap03_reservation_utilization_ratio", "gap03_admission_utilization_ratio",
                                                  "gap03_candidate_set_size", "gap03_chosen_locality_cost"]},
        {"title": "Dependencies", "panels": ["gap03_dependency_up", "gap03_breaker_state", "gap03_retry_attempts_total",
                                             "gap03_dependency_latency_ms"]},
        {"title": "Security & controls", "panels": ["gap03_audit_write_failures_total", "gap03_control_blocks_total",
                                                    "gap03_active_controls", "gap03_trust_verifications_total"]},
    ],
}


def validate_definitions() -> list[str]:
    from .metrics import CATALOG
    problems = []
    for a in ALERTS:
        for k in ("alert", "class", "severity", "owner", "runbook", "escalation", "first_diagnostics"):
            if not a.get(k):
                problems.append(f"{a.get('alert')}: missing {k}")
        if a["class"] not in ("availability", "overload", "policy", "dependency", "stale_state", "security", "software_defect"):
            problems.append(f"{a['alert']}: unknown class")
    for row in DASHBOARD["rows"]:
        for p in row["panels"]:
            if p not in CATALOG:
                problems.append(f"dashboard panel {p} not in metric catalog")
    return problems


def evaluate(samples: list[dict], *, env: str = "prod", maintenance: bool = False) -> dict[str, list[int]]:
    """samples: [{"t": seconds, signal: value, ...}] at 1 sample / 60 s. Returns firing intervals per alert."""
    mult = ENV_THRESHOLDS[env]
    firing: dict[str, list[int]] = {}
    for a in ALERTS:
        if "windows" in a:
            budget = 1 - a["slo"]
            fired = []
            for i, s in enumerate(samples):
                ok = True
                for win, burn in a["windows"]:
                    n = {"1h": 60, "5m": 5, "6h": 360, "30m": 30}[win]
                    w = samples[max(0, i - n + 1): i + 1]
                    ratio = sum(x.get("error_ratio", 0) for x in w) / len(w)
                    ok &= ratio > burn * budget * mult
                if ok and not maintenance:
                    fired.append(s["t"])
            if fired:
                firing[a["alert"]] = fired
            continue
        need = max(1, a["for_s"] // 60)
        run, fired = 0, []
        for s in samples:
            run = run + 1 if s.get(a["signal"], 0) >= a["threshold"] * (mult if a["class"] != "security" else 1) else 0
            if run >= need and not (maintenance and a["class"] in ("overload", "dependency", "stale_state")):
                fired.append(s["t"])
        if fired:
            firing[a["alert"]] = fired
    return firing


def precision(fired: dict[str, list[int]], actionable: set[str]) -> dict:
    total = len(fired)
    good = len([a for a in fired if a in actionable])
    return {"fired": total, "actionable": good, "precision": round(good / total, 3) if total else None,
            "retire_candidates": sorted(set(fired) - actionable)}
