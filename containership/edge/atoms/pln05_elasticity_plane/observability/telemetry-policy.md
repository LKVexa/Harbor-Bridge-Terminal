# PLN-05 telemetry policy (1.0.0)

| Class | Content | Sensitivity | Retention | Sampling | Export |
|---|---|---|---|---|---|
| metrics | counters/gauges/histograms, labels from `telemetry.label_allowlist` only (`outcome`, `reason_code`, `direction`, `dependency`, `state`, `site`) | internal | 13 months (downsampled after 30 d) | none | Prometheus scrape over mTLS |
| logs | structured JSON (`telemetry.Logger`), redacted | internal; may contain tenant ids in `decision` events | 30 days | all WARN+; INFO decision logs may be sampled 10 % at > 1k/s | OTLP/HTTPS to the tenant-separated log store |
| traces | W3C traceparent in/out; spans `pln05.decide` | internal | 7 days | `telemetry.trace_sample_ratio` (10 %); **errors always kept** | OTLP/HTTPS |
| audit | `PK_AUDIT/1` | restricted | 400 days, write-once | none | security SIEM only |
| explain | `PLN05_EXPLAIN/1` per decision | internal, tenant-scoped access via `explain.read` | in-memory `explain.retention` (10 000) | none | not exported; queried via API |

- Tenant and workload identifiers are **never** metric label values (cardinality + privacy); the series count is hard-capped (`telemetry.max_series`), overflow counted in `dropped_series`.
- Redaction: keys matching secret/token/password/credential/api_key/private_key/mac/authorization and values that look like PLN-05 tokens, bearer tokens, PEM blocks or AWS keys become `<redacted>` (`tests/test_units.py::TelemetryTest.test_redaction`).
- Deletion: tenant offboarding deletes that tenant's state files (by scope hash) and log partitions; audit is retained per legal hold.
- Alerts: `observability/alerts.json` (routes and runbooks), dashboards `observability/dashboards.json`; alert expressions are tested against synthetic scenarios (`tests/test_ops.py`). Noise review: monthly in the operations review; any alert that fired > 5× without action is tuned or removed through a reviewed change.
