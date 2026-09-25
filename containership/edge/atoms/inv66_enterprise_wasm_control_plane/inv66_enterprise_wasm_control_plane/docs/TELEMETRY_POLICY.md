# Telemetry retention, privacy, sampling and export (MC-051, MC-052, MC-054)

| Signal | Data class | Contents | Retention (config) | Sampling | Sink |
|---|---|---|---|---|---|
| Journal (audit) | **Security record, integrity-critical** | decisions, refusals, admin actions | `limits.retention_days` (default 400) + legal holds | **never sampled** | journal + SIEM exporter |
| Metrics | operational, no PII | counters/gauges/histograms; labels are bounded (tenant only on quota/shed metrics, capped at 1000 series per metric; excess goes to `overflow="true"`) | `telemetry.metrics_retention_days` (90) | n/a | Prometheus scrape `/metrics` |
| Logs | operational, pseudonymous | `PK_ECP_LOG/1` allow-listed keys; `redact_subjects` hashes the subject | `telemetry.log_retention_days` (30) | refusals/errors always logged at warning/error; success at info | stderr → collector |
| Traces | operational | span names, trace/span ids, tenant, lattice (bounded) | backend-defined | `trace_sample_ratio`, with parent-based sampling | in-process ring (OTLP exporter = adapter slot) |
| Explain | security record (derived) | read from the journal, so it is immutable | as journal | — | API |

**Never emitted:** bearer tokens, signatures, private keys, secret values, raw manifests (in logs
and traces), and request headers other than `traceparent`.

**Trust:** an incoming `traceparent` from an unauthenticated caller is used **only** for
correlation and never for authorization. Baggage is not propagated.

**Backpressure:** the logger writes synchronously to a stream (no unbounded buffer). The metrics
registry is bounded. The SIEM exporter's memory is bounded by `batch_size`, and it never skips records.

**Residency:** telemetry backends must be in the region named by `site`. That is an operator deployment
requirement and isn't enforced in code.

Dashboards: `ops/dashboards/inv66-overview.json`. Alerts: `ops/alerts/inv66-rules.yml`, each
with a runbook link. `tools/ci.py` lane `observability` checks that every metric referenced by
dashboards/alerts exists in a live `/metrics` render (catches observability drift).
