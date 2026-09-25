# INV-17 Dashboards and Alerts

**Controls:** C080 (with C072, C052, C054)
**Owner:** UNASSIGNED — owner to fill
**Machine-readable:** `observability/dashboards/inv17-overview.json`, `observability/alert-rules.json` (maintained separately). Thresholds here are PROPOSED; none have been tuned against production data.

## Panels (`inv17-overview`)

| # | Panel | Query (PromQL sketch) |
|---|---|---|
| 1 | Build / lineage | `inv17_build_info` |
| 2 | Streams by state | `sum by (state)(inv17_streams_open)` |
| 3 | Throughput | `rate(inv17_elements_transferred_total[5m])`, `rate(inv17_elements_read_total[5m])` |
| 4 | Backlog | `inv17_elements_buffered` (vs configured `global_buffer_budget`) |
| 5 | Credit stall ratio | `rate(inv17_credit_stalls_total[5m]) / (rate(inv17_credit_stalls_total[5m]) + rate(inv17_elements_transferred_total[5m]))` |
| 6 | Shedding | `rate(inv17_load_shed_total[5m])` |
| 7 | Breaker / disable | `inv17_breaker_open`, `inv17_disabled` |
| 8 | Drops | `inv17_dropped_end_streams` by `end`, `rate(inv17_elements_dropped_total[5m])` |
| 9 | Idempotent retries | `rate(inv17_duplicate_writes_total[5m])` |
| 10 | Health/readiness | probe results of `/readyz` (`status().health`) |
| 11 | Security events | `inv17_audit_events_total{kind}` for `auth.denied`, `auth.replay`, `authz.denied`, `trust.unavailable`, `quota.denied`, `control.*`; detail from exported audit JSONL |

## Distinguishing failure classes

| Class | Signature | Distinguishing evidence |
|---|---|---|
| **Load** (legit overload) | buffered ↑, stall ratio ↑, shed rate ↑, breaker may open; auth denials flat | `explain()` reasons "instance buffer budget exhausted" / "tenant buffered quota reached"; throughput high |
| **Dependency failure** (keys/time) | `trust.unavailable` audit events; opens fail; throughput on existing streams continues; shed flat | `details.dependency` = `keys`/`time`; decision reason "trust service unavailable (fail closed)" |
| **Attack** | spikes in `auth.denied` (bad signature/malformed), `auth.replay`, `authz.denied` with reason cross-tenant; possibly one tenant hitting `quota.denied` | concentrated on few `tenant_hash` values; no dependency events |
| **Policy rejection** (working as intended) | `quota.denied`, `inv17_disabled=1`, frozen scopes, `PK_STREAM_FROZEN` / `PK_STREAM_DISABLED` | `control.freeze`/`control.disable` audit events precede it; `explain().policy` shows scopes |
| **Defect** | type-mismatch errors in logs, `EndDropped` without matching client drops, counters decreasing unexpectedly, health `unhealthy` with no load, `AuditLedger.verify()` problems | no corresponding load/dependency/policy signal |

## Alerts (PROPOSED)

| Alert | Condition | Class | Severity |
|---|---|---|---|
| INV17Disabled | `inv17_disabled == 1` for 1m | policy | info (page if unexpected) |
| INV17BreakerOpen | `inv17_breaker_open == 1` for 2m | load | page |
| INV17SheddingSustained | shed rate > 0 for 10m | load | ticket |
| INV17BacklogHigh | `inv17_elements_buffered` > 0.8 × configured budget for 5m | load | ticket |
| INV17CreditStallHigh | stall ratio > 0.75 for 10m (mirrors `HealthPolicy.stall_ratio_unhealthy`) | load/defect | ticket |
| INV17NotReady | `/readyz` 503 for 2m | any | page |
| INV17TrustUnavailable | any `trust.unavailable` in 5m | dependency | page |
| INV17AuthAnomaly | `auth.denied`+`auth.replay`+`authz.denied` rate > baseline × N | attack | security page |
| INV17AuditChainBroken | `AuditLedger.verify()` non-empty (integrator job) | attack/defect | security page |
| INV17ReaderDropSpike | rate of `inv17_elements_dropped_total` spikes | defect/load | ticket |

Alerts 7–9 depend on the integrator exporting audit events to a log pipeline; INV-17 has no
metrics for them. Alert tests: none exist yet (planned with `observability/alert-rules.json`).
Runbook links: to be added when the runbook exists.
