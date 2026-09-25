# Telemetry retention, sampling, privacy and export (M65)

Source of truth: `fabric/telemetry.py::TELEMETRY_POLICY` (this page mirrors it).

- **Metrics** — 30 d retention. Labels restricted to `host, outcome, code, operation, tenant_class, region, state`; max 64 series per metric, overflow folded into `{overflow="true"}` and counted (`dropped_series`). Identities, tenants, components and link names are never labels.
- **Logs** — JSON lines, 2 KiB max per line, secrets redacted by key and by pattern; operational logs 30 d, security logs (`security: true`) 365 d.
- **Traces** — W3C `traceparent`; malformed headers start a new root. Default sample ratio 0.1 (config `telemetry.trace_sample_ratio`); errors and security denials always sampled. 7 d retention.
- **High-cardinality diagnostics** — only via `DecisionLog.query` (authorized `diagnostics.read`, paginated, max 200 rows).
- **Privacy** — no tenant payloads, secrets, tokens or full identities; identities appear only as key fingerprints.
- **Export** — Prometheus text exposition (`Metrics.exposition()`) and OTLP endpoint per site overlay; disconnected overlay disables export.
