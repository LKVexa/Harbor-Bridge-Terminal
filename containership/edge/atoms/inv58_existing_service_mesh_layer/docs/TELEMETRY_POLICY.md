# Telemetry retention, sampling, privacy and export (v4.3.0)

- **Metrics** (`telemetry.METRIC_CATALOG`): rate, errors, latency, saturation, backlog, resource. Label cardinality capped (`limits.max_label_cardinality`, overflow → `__overflow__`). Export: `Metrics.export()` (JSON) and `Metrics.prometheus()`.
- **Logs:** JSON lines with `ts, level, component, node, tenant, operation, event, trace_id, span_id, correlation_id, fields`. Subjects, SANs, source workloads and actors are keyed pseudonyms (`p:<16 hex>`), never raw; secret-looking values are redacted.
- **Traces:** W3C `traceparent` in; child span per operation; trace id is the correlation id on errors, audit and decisions.
- **Sampling:** `telemetry.sample_rate` (default 1.0) applies to logs/traces only; audit is never sampled.
- **Retention:** metrics 30 days (`telemetry.retention_days`), logs 30 days, audit per security policy (≥ 1 year recommended, owner to confirm), decision journal in-memory (5 000/tenant).
- **Privacy:** no payload bodies, no secret material, no raw workload names in logs; tenant ids are operational identifiers and are kept.
- **Export:** only via the host's collector; the component opens no connections.
