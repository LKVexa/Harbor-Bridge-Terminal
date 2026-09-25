# Incident severity, paging and escalation (C097)

| Sev | Definition for INV-53 | Page | Ack | Commander |
|---|---|---|---|---|
| SEV1 | Possible message loss (`E_CORRUPT`, storage failure on acknowledged data), security-dependency outage, cross-tenant exposure | 24×7 | 15 min | service_owner |
| SEV2 | Stall or sustained refusals for a tenant; auth failure spike | 24×7 | 30 min | operations_owner |
| SEV3 | DLQ growth, shedding, latency regression | business hours | next business day | operations_owner |
| SEV4 | Cardinality drops, documentation defects | none | backlog | technical_owner |

Steps: declare → stabilise (freeze / emergency disable if data safety is in doubt — safety beats
availability) → preserve evidence (copy store directory and audit log before any repair; record audit head) →
diagnose (`health`, `store inspect`, `explain`, audit verify) → repair → post-incident review within 5
business days with a debt item in `governance/WAIVERS.json` → `debt` for every follow-up.
Escalation routes and names: `governance/owners.json` (currently UNASSIGNED — paging cannot work until bound).
