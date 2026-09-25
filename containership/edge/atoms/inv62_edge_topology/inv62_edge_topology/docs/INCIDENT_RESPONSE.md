# Incident response (MC-086) — proposed, owner approval pending

| Severity | Definition | Page | Ack target | Examples |
|---|---|---|---|---|
| SEV1 | wrong routing across tenants/residency, split-brain, security compromise | on-call + security + incident commander | 15 min | A-ATK-1 sustained, two leases observed, audit verify fails |
| SEV2 | site(s) unable to resolve or partition handling failing | on-call | 30 min | A-DEP-*, A-DEF-1 |
| SEV3 | degraded performance or elevated shedding | business hours | 4 h | A-LOAD-*, A-LAT-1 |
| SEV4 | cosmetic / docs | ticket | 2 business days | |

Flow: detect (alert) → triage (health, metrics, explain, audit) → **contain** (freeze; quarantine node;
revoke credentials via `revoked_subjects`/key revoke; rollback config or binary) → recover (unfreeze; release;
verify gates) → post-incident review within 5 business days with timeline, root cause, action items entered in
`governance/debt.json`, and verification that the audit chain is intact. Escalation targets: `OWNERSHIP.md`.
