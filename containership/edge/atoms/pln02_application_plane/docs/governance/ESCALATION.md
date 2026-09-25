# Escalation — PLN-02

| Trigger | First responder | Escalate to | Max escalation latency |
|---|---|---|---|
| SEV1 security incident (key compromise, cross-tenant access, poisoned catalogue accepted) | security-lead | incident-commander → plane-owner | 15 min |
| SEV1 outage (no revisions publishable in any environment) | operations-lead | incident-commander | 15 min |
| Data-integrity failure (`REVISION_INTEGRITY_ERROR`, `AUDIT_CHAIN_BROKEN`) | operations-lead | security-lead + plane-owner | 30 min |
| SEV2 degradation (catalogue degraded > 1 h, p99 SLO breach) | operations-lead | plane-owner | 4 h |
| Unresolved compatibility conflict between adjacent planes | schema-governance | plane-owner | 2 business days |

Named contacts and paging handles live in the owner's on-call system; this archive records roles only.
