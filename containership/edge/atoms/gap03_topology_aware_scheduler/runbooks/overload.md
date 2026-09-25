# Runbook: Overload / load shedding (GAP03Overload, GAP03SaturationHigh)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. Check gap03_admission_rejected_total by reason
2. Identify noisy tenant via logs (pseudonymised tenant field) - never via metric labels
3. Compare rps against capacity.plan() envelope

## Mitigation / rollback / disable

- Scale scoring replicas (commit path does NOT scale: single leader)
- Lower tenant_rps for the noisy tenant via config (dry-run first)
- Apply a tenant-scoped freeze-new control only with an incident ticket

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
