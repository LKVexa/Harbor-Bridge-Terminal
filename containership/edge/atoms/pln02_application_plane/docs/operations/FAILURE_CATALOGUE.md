# Failure catalogue, health and stall detection (MC-23, C051, C052)

| # | Failure | Scope | Detection | Plane behaviour | Signal | Recovery |
|---|---|---|---|---|---|---|
| F1 | Required capability missing | request | resolver | `UNSATISFIED_CAPABILITY` terminal | `resolution_rejections_total{code}` | fix catalogue/app |
| F2 | No eligible provider under policy | request | `policy.select` | `NO_ELIGIBLE_PROVIDER` + rejected reasons | same | adjust policy/providers |
| F3 | Interface mismatch | request | resolver / WIT | `INCOMPATIBLE_INTERFACE` | same | fix versions |
| F4 | Catalogue source down | dependency | circuit breaker | stale → refuse, or degraded under lease | health `catalogue=fail/degraded` | reconnect, refresh |
| F5 | Catalogue poisoned / rolled back | dependency | signature/generation | `CATALOGUE_UNTRUSTED` | alert `CatalogueUntrusted` | rotate/revoke key, contact INV-65 |
| F6 | Process crash mid-write | process | startup `_recover` | tmp removed; corrupt revisions quarantined | `recovery_report` in log | none/backup restore |
| F7 | Disk full / I/O error | node | exception on write | request fails `INTERNAL`; nothing half-published | `resolution_rejections_total{code=INTERNAL}` | free space |
| F8 | Stale controller after failover | site | fencing epoch | `FENCED` | alert `Fenced` | stop stale controller |
| F9 | Audit write failure | node | exception | request fails (no unaudited success) | `audit_write_failures_total` | fix storage |
| F10 | Audit chain broken | node | `audit.verify` at startup | ledger refuses to open | `AUDIT_CHAIN_BROKEN` | incident SEV1 |
| F11 | Overload | process | admission | `OVERLOADED` / `QUOTA_EXCEEDED`, retryable | saturation gauge | scale out / quotas |
| F12 | Operation stall | process | `Watchdog` (> 2 s) | readiness `fail` | `stalled[]` in health | investigate, restart |
| F13 | Key service unavailable | dependency | `SecretStore` | `SECRET_UNAVAILABLE`, never default | health | restore KMS |
| F14 | Site partition | site | lease expiry | degraded within window, then refuse | `catalogue_degraded` | reconnect reconciliation |
| F15 | Control-plane (PLN-01) unavailable | upstream | no requests | idle; no action | request rate → 0 | upstream |

Health model: **live** = process serves `health.report()`; **ready** = no dependency `fail` and no stall;
**status** ∈ ok | degraded | fail. Thresholds: catalogue `max_age_seconds` (300), `max_offline_seconds` (3600),
stall 2 s, breaker 5 failures / 10 s.
