# Observability (INV29-MC079 – MC092)

## Endpoints (`telemetry.serve`)
| Path | Purpose | Status codes |
|---|---|---|
| `/healthz` | liveness — process responds | 200 |
| `/readyz` | readiness — pk_core compatible, required deps AVAILABLE, not disabled, signing key present | 200 / 503 |
| `/version` | version, release digest, policy generation, schema versions | 200 |
| `/dependencies` | per-dependency state (`AVAILABLE/ABSENT/INCOMPATIBLE/DEGRADED/UNAVAILABLE`) | 200 / 503 |
| `/metrics` | Prometheus text | 200 |
| `/decisions` | last 100 decision-reason events (redacted) | 200 |
| `/explain?module=&tenant=` | operator explain view (MC088) | 200 |

Bind to localhost or a management network only; the endpoints are unauthenticated by design and expose no secrets.

## Metrics
`inv29_compositions_total{outcome,code}` · `inv29_import_refusals_total` · `inv29_layer_failures_total{code}` · `inv29_admission_latency_ms` (histogram) · `inv29_dependency_available{dependency}` · `inv29_replay_cache_fill_ratio` · `inv29_hybrid_instances{state}` · `inv29_metric_series_dropped_total`. These realise the contract's `signals` (compositions, import_refusals, layer_failures, hybrid_instances).

## Logs
JSON lines: `ts, level, component, version, release, event, trace_id` + event fields, passed through `records.redact`. Tenant ids are logged (they are identifiers, not secrets); key material never is.

## Traces
W3C `traceparent` accepted from the caller and propagated to dependency calls; a malformed header starts a new trace instead of failing the request.

## High-cardinality safety (MC086)
≤ 200 series per metric; overflow folds into `__other__` and increments `inv29_metric_series_dropped_total`. Label values are sanitised. Per-module/tenant detail goes to the decision stream, not to metric labels.

## Release / topology correlation (MC089)
Every log line carries `version` and `release` (release manifest digest); `/version` exposes the same, so incidents can be tied to an exact build.

## Retention, sampling, privacy, export (MC090)
Decisions and warnings: 100 % kept. Debug: sampled (default 0). Retention proposal: logs 30 d hot / 1 y cold; decision stream 90 d; evidence ledger for the life of the release + 2 y. Export only redacted records. Owner to ratify (`governance/SLO.md`).

## Dashboards (MC091, P2) — `ops/dashboard.json`
## Alerts and failure classes (MC092) — `ops/alerts.yaml` (generated from `telemetry.ALERT_RULES`)
