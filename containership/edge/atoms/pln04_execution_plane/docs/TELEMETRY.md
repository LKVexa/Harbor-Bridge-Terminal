# PLN-04 telemetry, privacy and retention (PLN-04-C079, PLN-04-C080)

| Signal | Name | Labels (bounded) |
|---|---|---|
| counter | `pln04_admissions_total` | outcome, tier |
| counter | `pln04_admission_errors_total` | error_code |
| histogram | `pln04_admission_latency_ms` | — |
| counter | `pln04_provider_retries_total` | tier |
| counter | `pln04_attestation_failures_total` | tier |
| counter | `pln04_split_brain_detected_total` | — |
| gauge | `pln04_reaper_stuck` | — |
| counter | `pln04_export_backpressure_total` | — |

- Tenant IDs never become metric labels. In logs they are `hashed` by default (salted SHA-256 prefix); the mode can be `clear` or `omit`.
- Security and lifecycle events are never sampled. Debug logs follow `log_sample_rate`, and traces follow `trace_sample_rate` or an inbound W3C `traceparent`.
- Retention defaults: logs 30 d, metrics 90 d, audit 400 d. The policy rejects audit retention shorter than log retention.
- Alerts and dashboards: `ops/alerts.json`, `ops/dashboard.json` (defined, not deployed). Together they separate load, degradation, policy rejection, dependency failure and security events.
