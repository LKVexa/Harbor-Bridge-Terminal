# Telemetry governance — PLN-06 (WP #40, C079)

The machine-readable policy is `observability.TELEMETRY_POLICY`; this document explains it.

| Signal | Retention | Sampling | Contains | Never contains | Access |
|---|---|---|---|---|---|
| Logs (`PK_LOG/1`) | 30 days | 100 % ≥ INFO; DEBUG off in prod | node, component, release, operation, tenant (as supplied by caller), trace/span IDs, redacted fields | payload bytes, secrets, keys, MACs, credentials (redacted by key pattern) | SRE, security |
| Metrics (Prometheus text) | 395 days | n/a | counters/gauges/histograms; labels: tier, code, op | tenant IDs (hash only), payload | SRE, service owner |
| Traces (W3C trace-context) | 7 days | 10 % default; 100 % errors and security events | span names, destination, adapter, codes | payload, credentials | SRE |
| Audit ledger | 7 years (2555 days) or legal hold | 100 % | security events, hashed tenant, digests | payload, secrets | security read-only; no writer except the service |
| Explain view | not stored | on demand | hashed tenant/workload, decision inputs | raw tenant IDs, payload | `diagnostics.read` capability |

**Cardinality:** each metric name is capped at 1000 series; overflow collapses into `overflow="__other__"` and increments `MetricsRegistry.overflowed`.
**Export:** Prometheus text exposition (`GovernedDataPlane.metrics_text()`), JSON-lines logs to the configured sink, spans from `Tracer.spans` (OTLP exporter binding is a deployment concern).
**Deletion:** tenant off-boarding purges tenant-keyed logs/traces within 30 days; audit is retained per legal requirement.
**Change control:** changes to this policy require security + service-owner approval and a CHANGELOG entry.
