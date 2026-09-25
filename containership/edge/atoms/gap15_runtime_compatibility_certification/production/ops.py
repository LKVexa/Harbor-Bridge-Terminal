"""Alerting / dashboard pack (29), ownership metadata (43), runbook link checks (48).

Alerts are generated from one table so every alert carries severity, owner
role, runbook anchor, diagnostic query and first action (MC-29-05/06). Burn
alerts use two windows (1h/5m fast, 6h/30m slow). ``check_runbook_links``
fails the release when an alert points at a missing runbook section
(MC-48-10). Silences require an owner, reason and expiry, and critical
security/EOL alerts can be silenced for at most 4h (MC-29-07).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

ROLES = ("service-owner", "technical-owner", "security-owner", "data-owner", "incident-commander")

ALERTS = [
    # name, severity, expr, owner, runbook anchor, first action
    ("GAP15SLOBurnFast", "page", "error_ratio_1h > 14.4*budget and error_ratio_5m > 14.4*budget", "technical-owner", "rb-elevated-errors", "check /readyz and recent deploys"),
    ("GAP15SLOBurnSlow", "ticket", "error_ratio_6h > 6*budget and error_ratio_30m > 6*budget", "technical-owner", "rb-elevated-errors", "compare error categories"),
    ("GAP15ExpiryStorm", "page", "gap15_expiry_backlog > 0.2 * tested_keys", "service-owner", "rb-expiry-storm", "raise recert lab quota; do not extend TTL"),
    ("GAP15RecertBacklog", "ticket", "gap15_queue_depth{queue=\"recert\"} > 1000 for 30m", "service-owner", "rb-expiry-storm", "inspect dead jobs"),
    ("GAP15EOLAdmitted", "page", "gap15_eol_in_service > 0", "security-owner", "rb-eol-exposure", "emergency-disable the runtime"),
    ("GAP15CoverageLow", "ticket", "gap15_matrix_coverage_ratio < 0.8 for 1d", "service-owner", "rb-coverage", "schedule coverage-gap jobs"),
    ("GAP15SignatureFailures", "page", "rate(gap15_evidence_rejections_total{category=\"signature\"}[5m]) > 1", "security-owner", "rb-signature-failures", "identify signer; consider quarantine"),
    ("GAP15AttestationFailures", "page", "rate(gap15_evidence_rejections_total{category=\"attestation\"}[5m]) > 1", "security-owner", "rb-attestation-failures", "check baselines and firmware revocations"),
    ("GAP15ProvenanceFailures", "page", "rate(gap15_evidence_rejections_total{category=\"provenance\"}[5m]) > 1", "security-owner", "rb-provenance-failures", "check builder trust and SBOM subjects"),
    ("GAP15AuditChainBroken", "page", "gap15_audit_chain_ok == 0", "security-owner", "rb-audit-chain", "preserve evidence; stop admissions"),
    ("GAP15ReplayDetected", "page", "increase(gap15_evidence_rejections_total{category=\"auth\"}[5m]) > 20", "security-owner", "rb-replay", "revoke affected tokens"),
    ("GAP15RevocationLag", "page", "gap15_revocation_propagation_seconds > 60", "security-owner", "rb-revocation-lag", "stop admissions at lagging sites"),
    ("GAP15ConflictsOpen", "ticket", "gap15_conflicts_open > 0 for 4h", "service-owner", "rb-conflicts", "assign case owners"),
    ("GAP15TimeUntrusted", "page", "gap15_time_offset_seconds > 5", "technical-owner", "rb-time", "check NTS/PTP sources"),
    ("GAP15StorageSaturation", "page", "disk_free_ratio < 0.1", "data-owner", "rb-storage", "expand volume; never prune ledger"),
    ("GAP15BackupFailed", "page", "time() - last_verified_backup_ts > 26h", "data-owner", "rb-backup", "run backup and restore-verify"),
    ("GAP15ScrapeStale", "ticket", "gap15_exporter_scrape_age_seconds > 120", "technical-owner", "rb-observability", "check exporter and alert pipeline"),
    ("GAP15AlertPipelineDead", "page", "absent(ALERTS{alertname=\"GAP15Watchdog\"})", "technical-owner", "rb-observability", "notification path is down"),
    ("GAP15Watchdog", "none", "vector(1)", "technical-owner", "rb-observability", "always firing: proves the alert pipeline"),
    ("GAP15DependencyOutage", "page", "readiness_check_failed{check=~\"time|chains|key_provider\"} == 1", "technical-owner", "rb-dependency-outage", "follow fail-closed matrix"),
]
CRITICAL_UNSILENCEABLE_S = 4 * 3600


def alert_rules() -> dict:
    return {"groups": [{"name": "gap15", "rules": [
        {"alert": n, "expr": e, "labels": {"severity": s, "owner": o},
         "annotations": {"runbook": f"docs/RUNBOOKS.md#{rb}", "first_action": fa,
                         "diagnostics": f"python -m gap15_runtime_compatibility_certification.production.cli diagnose --alert {n}"}}
        for n, s, e, o, rb, fa in ALERTS]}]}


def dashboard() -> dict:
    panels = ["SLO / burn rate", "certify latency p50/p95/p99", "ingest latency p50/p95/p99", "verdicts by type",
              "rejections by category", "matrix coverage", "evidence age / expiry backlog", "EOL exposure",
              "revocation lag", "queue depth ingest/recert", "conflicts open", "time offset", "audit chain ok",
              "waivers active by risk", "storage / CPU / memory saturation"]
    return {"title": "GAP-15 runtime compatibility certification", "schemaVersion": 1,
            "panels": [{"id": i + 1, "title": t} for i, t in enumerate(panels)]}


def check_runbook_links(runbook_text: str) -> list:
    anchors = set(re.findall(r'<a id="([a-z0-9-]+)"></a>', runbook_text))
    return sorted({rb for _, _, _, _, rb, _ in ALERTS} - anchors)


@dataclass(frozen=True)
class Silence:
    alert: str
    owner: str
    reason: str
    starts: int
    ends: int


def validate_silence(s: Silence) -> list:
    sev = {n: sev for n, sev, *_ in ALERTS}.get(s.alert)
    problems = []
    if sev is None:
        problems.append("unknown alert")
    if not s.owner or not s.reason:
        problems.append("owner and reason are required")
    if s.ends <= s.starts:
        problems.append("silence must expire")
    if sev == "page" and s.ends - s.starts > CRITICAL_UNSILENCEABLE_S:
        problems.append("paging alerts may be silenced for at most 4h")
    return problems


def validate_owners(doc: dict) -> list:
    """Owner/contact references must be real (MC-43-07); placeholders are reported, never accepted."""
    problems = []
    for role in ROLES:
        entry = doc.get(role)
        if not entry or not entry.get("name") or entry.get("name", "").startswith("UNASSIGNED"):
            problems.append(f"{role}: unassigned")
        elif not re.fullmatch(r"[^@\s]+@[^@\s]+\.[a-z]{2,}", entry.get("contact", "")):
            problems.append(f"{role}: contact is not a resolvable address")
    return problems


def write_pack(directory: str) -> list:
    import os
    os.makedirs(directory, exist_ok=True)
    out = []
    for name, obj in (("alerts.gap15.json", alert_rules()), ("dashboard.gap15.json", dashboard())):
        p = os.path.join(directory, name)
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, sort_keys=True)
            fh.write("\n")
        out.append(p)
    return out
