# GAP-12 incident severity / paging / escalation matrix

| Severity | Trigger (alert or reason) | Paging | Escalation role | First safe action |
|---|---|---|---|---|
| SEV1 | G12SecurityEvent; audit chain broken; AUTH_* burst; relay tenancy breach | page immediately | security on-call -> platform lead | kill switch the affected mechanism; quarantine peers |
| SEV2 | G12EstablishBurn1h/6h; G12RetryStorm; G12RelaySaturation | page | network on-call | open breaker scope override; pre-warm relay; pause rollout |
| SEV3 | G12DnsFailure; G12TraversalRegression; G12EstablishBurn3d | ticket | owning team | investigate with explain(); roll back last config generation |

Paging integrations (PagerDuty/Opsgenie routes) and the people holding each role are **not configured
in this package**; they are owner decisions and are reported NOT-EVIDENCED.
