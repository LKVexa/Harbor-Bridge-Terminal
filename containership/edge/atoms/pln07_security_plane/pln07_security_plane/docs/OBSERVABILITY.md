# Observability and audit (MC-39 .. MC-48)

| Signal | Implementation |
|---|---|
| Health/readiness/version/config/dependency/capability | `service.health()`; HTTP `/livez`, `/readyz`, `/healthz` |
| Metrics | `observability.Metrics` → `/metrics` (Prometheus text). `pln07_requests_total{op,outcome}`, `pln07_<op>_latency_ns{quantile}` |
| Structured logs | `Telemetry.log` JSON lines with `trace_id`/`span_id`, redacted |
| Tracing | W3C `traceparent` accepted per request; spans per operation |
| Audit | `AuditLog` — hash-chained `PK_AUDIT/1` events for issue/attenuate/verify/revoke, allow and deny; `verify()` detects tampering |
| Explain | `service.explain()` / `POST /v1/explain` — every link, every check, no secrets |
| Redaction | secret-looking keys redacted, bytes elided, long strings truncated, identifiers pseudonymised on demand |
| Cardinality | ≤ 64 values per metric label, then `__overflow__` |

## Telemetry policy (MC-47)
- Retention: audit 400 days (compliance), logs 30 days, metrics 13 months at 1-minute resolution, traces 7 days.
- Sampling: audit and metrics unsampled; spans `sample_rate` (default 1.0; 0.1 recommended at >1k ops/s).
- Privacy: no secrets, signatures or tokens leave the process; subjects appear only in audit (access-controlled) and are pseudonymised in logs when exported off-tenant.
- Export: audit to write-once storage; the chain head is checkpointed daily into the evidence bundle.

## Release lineage (MC-46)
Every health response carries version, config digest and key ids; every evidence bundle carries artifact digests. Correlating the two ties a running instance to its release and config.

## Dashboards and alerts (MC-48)
See `deploy/alerts.yaml` and `deploy/dashboard.json`.
