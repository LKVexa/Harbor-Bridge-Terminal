# Incident response (C097)

| Sev | Examples | Page | Target |
|---|---|---|---|
| SEV1 | isolation violation, secret leak, audit chain break | immediate, security lead | contain 15 min |
| SEV2 | provider down / NO_GO in prod, breaker stuck open | on-call | mitigate 1 h |
| SEV3 | elevated OVERLOADED, SLO burn warning | ticket | 1 business day |

Containment: emergency disable (two-person), drain, revoke affected links, rotate authn/policy/state keys, invalidate secret refs. Recovery: restore from last verified backup, verify audit chain head against external record, re-run release gate.
