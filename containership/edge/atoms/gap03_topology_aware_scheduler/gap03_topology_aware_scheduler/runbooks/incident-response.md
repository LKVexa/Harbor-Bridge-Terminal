# Runbook: Incident response (MC-043)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires a tabletop/game day)

## 1. Severity levels

| Sev | Scheduler-specific examples | Impact criteria | Security escalation | Required response |
|---|---|---|---|---|
| SEV1 | capacity overcommit, split brain / fencing rejections from two writers, audit integrity failure, forged topology accepted | placement safety or tenant isolation at risk | always page security on-call | Page primary + secondary now; IC assigned in 5 min |
| SEV2 | commits blocked > 15 min (identity/coordination/ledger outage), SLO fast burn | new placements unavailable | if auth failures or replay events spike | Page primary + secondary |
| SEV3 | degraded scoring quality (stale inventory/gravity), fairness denial spike | wrong-but-safe placements | on any SECURITY log event | ticket, business hours |
| SEV4 | single-tenant issue, cosmetic explain problem | one tenant | none | ticket queue |

## 2. Roles

Incident commander, operations lead, communications lead, security lead, scribe. Names/contacts: UNASSIGNED
(production blocker, see OWNERS.json). The IC owns every decision to create/clear controls.

## 3. Detection sources and first-response triage

| Class | Detection | Triage |
|---|---|---|
| Overload | GAP03Overload, gap03_admission_rejected_total | see overload.md; shed by priority, never drop committed state |
| State corruption / drift | GAP03ReconciliationDrift, INTEGRITY_FAILURE codes | stop writes (disable-commit), reconcile, see reconciliation.md |
| Split-brain / fencing | GAP03FencingRejections, two terms observed | see split-brain.md; drain stale replica |
| Topology errors | GAP03StaleTopology, NOT_IN_TOPOLOGY spike | see topology.md |
| Fairness anomalies | GAP03PolicyDenialSpike, starved tenants gauge | see fairness.md; verify entitlement snapshot |
| Dependency outage | GAP03DependencyDown | see degraded-mode.md |
| Security | GAP03AuthFailures, GAP03AuditWriteFailure, downgrade/replay audit events | see security.md / audit.md |

## 4. Diagnosis sources (authoritative)

- Dashboard "GAP-03 Topology-aware scheduler" (controlplane/alerts.py DASHBOARD) and recording rules (metrics.RECORDING_RULES)
- `GET /healthz/deep` (authorized) for generations, lease term, dependency stale ages
- Explain API (`Explain.query` by txn/workload) and `Explain.replay` for divergence
- Transaction journal (TxnJournal state: PREPARED / UNKNOWN / orphan entries)
- Audit log (`AuditLog.query`, `AuditLog.verify`) for privileged mutations
- Ledger point-in-time snapshots (`LedgerStore.point_in_time(seq)`) and topology export bundles

## 5. Contain

1. Scoped freeze-new control (tenant/site/node) with the incident ticket.
2. Admission reduction (tenant_rps / shed thresholds via config dry-run then activate).
3. Replica fencing: drain the suspect replica (`Coordinator.drain`), never hand-edit fencing tokens.
4. Dependency isolation: breakers open automatically; do not override integrity dependencies.
5. Rollback via the rollout controller to the previous digest.
6. Escalate to disable-commit, then hard-stop (break-glass + dual approval) only for SEV1.

## 6. Forensics (evidence preservation)

Preserve before any repair: copy the audit, ledger, topology, journal and controls directories read-only; export the
audit log (`AuditLog.export`) and record its chain head; capture `/healthz/deep`; never truncate or rewrite a WAL.

## 7. Recover and validate

Check, in order: topology invariants (`check_invariants`), ledger invariants and `verify_history`, no pending/orphan
transactions after `recover_all`, a single coordination owner with the highest term, dependency freshness (no stale
ages over TTL), reconciliation drift empty; then clear controls and watch readiness hysteresis settle.

## 8. Communications (templates are DRAFT - approval blocked)

- Internal: "SEV{n} GAP-03: {impact}. Placements {available|blocked}. Next update {time}." (SEV1 every 30 min, SEV2 hourly)
- Customer/stakeholder: impact and ETA only; never tenant names, topology locations or internal identifiers.

## 9. Post-incident review

Within 5 business days: timeline, contributing factors, violated assumptions/invariants (compare with ADR-0001),
corrective actions with owners and due dates, verification that alerts fired as expected, and ADR/runbook updates.

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class
event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
