# Observability  (components 72-81)

| # | Capability | Implementation |
|---|---|---|
| 72 | health/readiness/version/config/dependency surface | `BrokerService.health()` → `schemas/health.schema.json` |
| 73 | metrics | `telemetry.Metrics`: `published`, `appended`, `replays`, `consumer_lag`, `authz_denied`, `backlog_rejects`, `lifecycle_transitions`, `publish_latency_s`, `append_latency_s`; Prometheus text via `prometheus()` |
| 74 | structured logs | `telemetry.StructuredLogger` JSON lines: ts, level, component, event, version, trace ids; payloads never logged; secret keys redacted |
| 75 | trace propagation | W3C `traceparent` parse/child/header (`TraceContext`) |
| 76 | high-cardinality safety | per-metric label-set cap → `__overflow__` + counter |
| 77 | decision records | `DecisionLog` of allow/deny with reasons (bounded) |
| 78 | operator explain view | `DecisionLog.explain(request_id)` |
| 79 | lineage | `build_lineage()` (version, build digest, config digest, site, env) in health |
| 80 | telemetry policy | `TELEMETRY_POLICY.md` |
| 81 | dashboards/alerts | `ops/alerts.yaml`, `ops/dashboard.json` (Prometheus rules; **not deployed/tested against a live Prometheus**) |

Exporter to a real backend (OTLP/Prometheus scrape endpoint) is not implemented → PARTIAL.
