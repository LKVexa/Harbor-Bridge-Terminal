# Incident severity, paging, escalation, containment and recovery (C097)

| Sev | Definition | Page | Ack | Escalate to | Containment default |
|---|---|---|---|---|---|
| SEV1 | memory-safety/isolation breach suspected; key compromise; component not ready fleet-wide | on-call + security_owner | 15 min | accountable_owner at 30 min | quarantine affected queues; rotate+retire keys |
| SEV2 | bounds-violation or security-refusal spike; stalled queues; audit chain break | on-call | 30 min | security_owner at 2 h | quarantine offending guest's queues; NO_SUPPRESSION for stalls |
| SEV3 | saturation critical; SLO burn; single-host not ready | on-call (business hours) | 4 h | operations_owner | reduce depth/rate via site override |
| SEV4 | perf regression, dashboard gaps | ticket | 1 business day | code_owner | none |

**Flow:** detect (alert) → declare sev → contain (runbook) → preserve evidence
(`status`, `explain`, audit export, journal snapshot) → recover → verify
(`audit.verify()`, fixtures on affected hosts) → post-incident review within 5
business days → actions into `governance/WAIVERS.json#technical_debt`.

Paging destination: `governance/OWNERS.json#escalation.oncall_destination` (**UNASSIGNED — blocker**).
