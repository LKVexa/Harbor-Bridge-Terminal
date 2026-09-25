# Constraint precedence  (C019 · component 10)

When constraints conflict, the higher rule wins; the losing constraint is reported, never silently dropped.

1. **Security** (authn/authz, tenant isolation, secret handling, fail-closed on security-service outage)
2. **Data residency** (failover never promotes a replica outside `allowed_sites`)
3. **Integrity/consistency** (fencing, high watermark, no partial fan-out under `reject`)
4. **Durability** (fsync policy, quorum)
5. **Availability / SLO** (degraded modes permitted only if 1–4 hold)
6. **Cost / efficiency**

Examples encoded in code: key-service outage → refuse (1 over 5); no in-region replica → partition unavailable (2 over 5); backlog full under `reject` → refuse whole publish (3 over 5).
