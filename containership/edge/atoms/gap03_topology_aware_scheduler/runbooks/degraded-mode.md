# Runbook: Dependency loss / degraded mode (GAP03DependencyDown)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. GET /healthz/deep -> dependency stale ages
2. Check breaker state gauge
3. Confirm which operations the MATRIX blocks for this dependency

## Mitigation / rollback / disable

- Commits stay blocked for identity/coordination/audit/ledger/topology/time/SCH-01 loss - this is by design
- Scoped break-glass override (degraded.override) only for stale_ok dependencies, <=1h, with written risk acknowledgement
- After restoration: follow reconciliation.md BEFORE mark_reconciled()

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
