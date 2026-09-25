# Runbook: Authentication failures / attack (GAP03AuthFailures)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. Group auth.verify_failed audit events by reason
2. Look for downgrade_attempt and replay events

## Mitigation / rollback / disable

- Revoke compromised keys via TrustStore.revoke (audited)
- Apply controls hard-stop only with dual approval

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
