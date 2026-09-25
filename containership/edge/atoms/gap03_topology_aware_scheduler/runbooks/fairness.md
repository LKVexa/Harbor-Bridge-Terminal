# Runbook: Fair-share denial spike (GAP03PolicyDenialSpike)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. Check reservation_deficit / oversubscription via entitlement authority snapshot
2. Run entitlement reconcile() and look for drift events
3. Inspect explain records: reason protected_reservation vs capacity_exhausted

## Mitigation / rollback / disable

- Denials are correct behaviour when reservations protect other tenants - do not override
- If entitlement drift: repair ledger reservations from the signed entitlement snapshot

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
