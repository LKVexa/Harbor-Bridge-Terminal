# INV-21 Incident Severity and Response

| Sev | Definition | Page | Examples |
|---|---|---|---|
| SEV-1 | isolation or integrity breach, or suspected | immediately, 24×7 | any executed cross-tenant hop; audit chain verify failure; handler ran after a refusal |
| SEV-2 | production call path unavailable/refusing broadly | immediately | `ready=0` fleet-wide; provider outage > 5 min; >5% `PK_CHAIN_INTERNAL` |
| SEV-3 | degraded, SLO burn | business hours | p99 above threshold; breaker flapping; stale_hits rising |
| SEV-4 | defect, no user impact | ticket | telemetry gap |

**Paging triggers** are the alerts in `ops/alerts.yaml` (label `severity`).

**Containment**: SEV-1 → `quarantine(reason=INC-id, actor=)` on affected hosts; revoke affected identity key id (`IdentityVerifier.retire`); invalidate policy cache (`policy.invalidate(min_policy_revision=)`).

**Evidence collection**: audit JSONL + exported head, `explain(trace_id)` output, `/readyz` JSON, config revision history (`ConfigStore.history`), release manifest digest. Do not edit audit files; copy them.

**Recovery validation**: `release()` only after (1) root cause fixed, (2) audit verify OK, (3) semantic-equivalence and adversarial suites pass on the fixed build, (4) canary stage 1% clean.

**Escalation**: on-call → component owner → security lead → Research Division head. Named contacts: see `governance/OWNERS.json` (status PROPOSED until confirmed by the owner).
