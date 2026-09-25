# Runbook: Canary / staged rollout (MC-041)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. Exit gate result must be GO for the exact artifact digest

## Mitigation / rollback / disable

- Stages 1/10/50/100% with bake; automatic rollback on any breach
- Manual rollback: shift(previous, 100) and record

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
