# INV-17 Severity Matrix

**Controls:** C096, C097 (checklist §58); thresholds from C052 (§26).

Health statuses come from `control::StreamRegistry.health()` using `HealthPolicy` (defaults: stall ratio degraded 0.25, unhealthy 0.75, stall 30 s unhealthy, min 20 attempts, buffer fill degraded 0.9). `/readyz` returns 503 when status is `unhealthy` or `disabled`; the current status is also exported as `inv17_health_status{status}`, and audit events as `inv17_audit_events_total{kind}`.

| Sev | Definition | INV-17 symptoms (signal) | Response |
|-----|------------|--------------------------|----------|
| **Sev0** | Integrity/security breach or total loss across tenants | `AuditLedger.verify()` returns problems (chain tamper); evidence of cross-tenant data delivery; auth accepting bad tokens; `TokenReplay` accepted | Page now; consider `emergency_disable`; security contact |
| **Sev1** | Service unavailable or unsafe for many tenants | `/readyz` 503 with `unhealthy` across many streams; trust outage (`trust.unavailable` audit events, all auth denied); `inv17_breaker_open` = 1 sustained; `emergency_disable` active unplanned; `global_buffer_budget` exhausted with `inv17_load_shed_total` rising fast | Page; runbook §§3–6 |
| **Sev2** | Degraded for one tenant/workload, or elevated errors | `health` = `degraded`; single stream credit-stalled ≥ 30 s; buffer ≥ 90 % of `max_buffer`; tenant `QuotaExceeded` spikes; `inv17_elements_dropped_total` rising (reader drops); config activation rolled back (`config.rollback` auto) | On-call ticket, same day |
| **Sev3** | Cosmetic / single client error | isolated `ElementTypeMismatch`, `VersionUnsupported` from an old client, occasional `StreamTimeout` | Ticket |

Upgrade severity one level if impact persists beyond 1 hour (PROPOSED) or affects a production tier listed in deployment/applicability-matrix.json. Numeric alert thresholds on metrics are not yet calibrated by measurement.
