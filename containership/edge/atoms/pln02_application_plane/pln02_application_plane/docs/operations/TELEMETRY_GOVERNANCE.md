# Telemetry catalogue and governance (MC-30, MC-31, C071–C080)

## Catalogue
| Signal | Type | Labels | Source |
|---|---|---|---|
| `application_revisions_total` | counter | tenant, environment, site | service |
| `resolution_rejections_total` | counter | tenant, environment, site, code | service |
| `resolution_seconds` | histogram | tenant, environment, site | service |
| `provider_bindings` | gauge | provider, tenant, environment, site | service |
| `audit_write_failures_total` | counter | — | service |
| health report | JSON | version, config_digest, dependencies, stalled | `Health.report()` |
| structured logs | JSON lines | event, level, code, correlation_id, trace_id, tenant, environment, site | `StructuredLogger` |
| decision records | JSON | capability, chosen, eligible, rejected, policy_version | `provenance.explain` (stored with each revision) |

Trace context: W3C `traceparent` accepted on `submit`, child span id generated, `trace_id` stored in revision
provenance → correlates the revision with release lineage (C078).

## Governance
- **Privacy/redaction:** principals appear only in audit + provenance, never in metric labels. Sensitive keys are
  redacted in logs and audit. Label values outside `[A-Za-z0-9._:/-]{1,64}` become `_invalid`.
- **Cardinality:** ≤ 2 000 series per metric; overflow folded into `{overflow="true"}` and counted.
- **Retention:** metrics 30 d; logs 30 d (security 400 d); audit ledger 7 y or legal hold; revisions indefinite.
- **Sampling:** traces 10 % baseline, 100 % on error; logs unsampled at warn+.
- **Export:** Prometheus text (`Metrics.prometheus()`); logs to stdout sink; audit `export(tenant)` for tenant self-service.

Dashboards and alerts: `dashboards.json`, `alerts.json` (backend-neutral definitions). They have **not** been
deployed to a monitoring backend from this archive.
