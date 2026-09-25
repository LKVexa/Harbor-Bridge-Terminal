# Runbook: Error-budget burn (GAP03SLOBurnFast/Slow)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. GET /healthz/deep and note failing dependencies
2. Query gap03_requests_total by code to split OVERLOADED vs FAIRNESS_DENIED vs INTERNAL
3. gap03 explain --since 15m for a sample of failed transactions

## Mitigation / rollback / disable

- If one dependency dominates, follow degraded-mode.md
- If INTERNAL dominates after a release, follow rollout rollback (backup-restore.md is NOT the first step)

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
