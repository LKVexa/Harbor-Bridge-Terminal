# Runbook: Reconciliation drift (GAP03ReconciliationDrift)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. Run ledger reconcile(repair=False) with SCH-01 placed set
2. Run entitlement reconcile(); run GAP-02 Inventory.reconcile()
3. Classify drift: orphan_committed, unknown_placements, entitlement_drift

## Mitigation / rollback / disable

- Repair only after the drift report is reviewed; use reconcile(repair=True) for orphan commits
- Unknown placements are escalated to SCH-01 owners - never adopted silently

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
