# Runbook: Audit write failure / integrity failure (GAP03AuditWriteFailure)

**Service:** GAP-03 topology-aware scheduler v4.3.0  
**Owner:** UNASSIGNED (see governance/OWNERS.json)  
**Exercise status:** NOT EXERCISED in a production-like environment (blocked - requires ops rehearsal)

## First diagnostics

1. Check disk/quota on the audit volume
2. Run AuditLog.verify(trust_store) and record break_at
3. Preserve the audit directory read-only for forensics

## Mitigation / rollback / disable

- Privileged mutations fail closed while audit is down - expected
- Restore capacity; never truncate or edit the WAL
- If integrity failed: open a SECURITY incident (incident-response.md)

## Degraded operation

Read-only explain and health stay available in every degraded mode; commits fail closed whenever ownership, identity, audit or durable state cannot be proven (controlplane/degraded.py MATRIX).

## Escalation

Primary on-call -> secondary after 15 min unacknowledged -> service owner -> security on-call for any SECURITY-class event. Contacts: see governance/OWNERS.json (currently UNASSIGNED - production blocker).
