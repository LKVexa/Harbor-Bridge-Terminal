# Incident response (MC-061)

| Sev | Definition | Page | Ack |
|---|---|---|---|
| SEV1 | suspected escape, out-of-model boot, cross-tenant reuse, audit/key integrity failure, fleet-wide admission outage | primary+secondary+security | 5 min |
| SEV2 | boot SLO burn > 14.4×, node-level outage, breaker open > 15 min | primary | 15 min |
| SEV3 | single-instance failures, degraded but within SLO | ticket | next business day |

Containment: `freeze` → `quarantine(node|tenant|instance)` → preserve VMM logs, audit log, journal, decision records.
Evidence: copy + SHA-256 into incident folder; never edit originals. Recovery: `RUNBOOKS.md`. Post-incident: blameless review within 5 business days, actions into `release/WAIVERS.json` debt registry with owner and due date.
