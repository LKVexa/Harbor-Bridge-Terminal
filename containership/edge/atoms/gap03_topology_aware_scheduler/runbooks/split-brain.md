# Runbook: Fencing rejections / suspected split brain (GAP03FencingRejections)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. Compare gap03_coordination_term across replicas
2. Identify writer presenting the stale token from audit/log correlation IDs
3. Check lease replica reachability

## Mitigation / rollback / disable

- Stale writers are already refused - do NOT raise any fencing token manually
- Drain the stale replica (Coordinator.drain) and restart it
- Run recover_all() on the current leader

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
