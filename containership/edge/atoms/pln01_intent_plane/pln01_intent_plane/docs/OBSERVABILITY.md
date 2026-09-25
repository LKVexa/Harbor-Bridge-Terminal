# Observability and telemetry policy (MC-022, MC-034–MC-037)

**Metrics** (Prometheus text via `svc.metrics.exposition()`): `pln01_requests_total{op,outcome}`,
`pln01_request_seconds{op}` histogram, `declaration_admission{result,reason}`, `plan_emission_seconds`,
`graph_version`, `drift_open`, `pln01_bulkhead_saturation`. Label sets are capped (1 000 per metric; overflow bucket)
— tenant/node names are **never** labels.

**Logs:** JSON lines, one per event, keys `ts, level, component, event, trace_id, span_id, …`; all fields pass
`redact_value`. **Traces:** W3C `traceparent` accepted and propagated; each response returns a child `traceparent`;
invalid headers start a new trace. **Sampling:** `telemetry.trace_sample_ratio` (default 10 %); errors always logged.

**Audit:** durable, hash-chained, HMAC-sealed `audit.jsonl` (actor, operation, targets, outcome, reason, version,
trace id, config digest). Retention default 400 days (`telemetry.audit_retention_days`); export by shipping the file
with its chain — verification is `DurableStore.verify()`. Audit carries node keys but never spec values (privacy).
External anchoring (e.g. periodic head hash to a WORM store) is an open item (W-006).

**Explainability:** `svc.explain(node)` returns every admission decision, constraint resolution, graph version and
release lineage (component version + config digest/provenance); plans carry `lineage` too.

**Dashboards/alerts:** `ops/dashboard.json`, `ops/alerts.yaml` — each alert links to a runbook section.
