# Runbook: Orphan / in-doubt transactions (GAP03OrphanTransactions)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. List journal txns in UNKNOWN/PREPARED
2. Query SCH-01 status(txn) for each
3. Check pending claims past expiry

## Mitigation / rollback / disable

- Run PlacementCoordinator.recover_all() on the leader
- reclaim_expired runs automatically inside recover_all

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
