# INV-35 Observability (C071–C080)

## Status surface (C071)
`ControlPlane.status()` → `INV35_STATUS/1` (`schemas/status/status.schema.json`):
`live`, `ready` (all queues serving/degraded, no stall, key service ok), `version`,
config `digest`/`generation`, interface majors, dependencies (key_service,
time_service, control_plane, pk_core), capabilities, saturation, per-queue state.

## Metrics (C072) — Prometheus text exposition (`Metrics.exposition()`)

| Metric | Type | Labels | Meaning |
|---|---|---|---|
| `inv35_descriptors_validated_total` | counter | outcome, code | descriptors accepted / chains refused |
| `inv35_bounds_violations_total` | counter | queue | E105 refusals |
| `inv35_chain_violations_total` | counter | queue | E102/E103 refusals |
| `inv35_security_refusals_total` | counter | code | E30x refusals |
| `inv35_decisions_total` | counter | action, outcome, code | every automated decision |
| `inv35_idempotent_replays_total` | counter | queue | replayed submits |
| `inv35_suppressed_notifications_total` | counter | queue | notifications correctly elided |
| `inv35_queue_depth` | gauge | queue | in-flight descriptors |
| `inv35_saturation` | gauge | — | host capacity used (0–1) |
| `inv35_stalled` | gauge | queue | 1 when stalled |
| `inv35_submit_latency_us` | histogram | queue | submit latency buckets 1 µs–10 ms |

These cover every signal named in `contract.py::signals`.

## Structured logs (C073) — `INV35_LOG/1` JSON lines
Fields: `schema, ts, level, event, trace_id, span_id, code, tenant, queue, …` (redacted).
Correlation: `trace_id` is stable end-to-end (from the caller's `traceparent`);
`code` is the stable error code; `queue`/`tenant` are stable identifiers.
Schema: `telemetry/log_schema.json`.

## Trace context (C074)
W3C `traceparent` accepted on submit/complete; malformed or all-zero ids start a
new trace (never trusted blindly); results return `trace_id`; each call is a child span.

## High-cardinality safety and redaction (C075)
256 series per metric then `__overflow__`; tenant ids are **not** metric labels
(only queue ids, bounded by per-tenant queue caps); secret-named fields redacted.

## Reason recording (C076) and explain view (C077)
Every automated decision emits `INV35_DECISION/1` (action, outcome, code, rule, inputs, trace_id).
`Runtime.explain(queue)` renders the last decisions for operators; CLI: `python tools/inv35ctl.py explain`.

## Release lineage / infrastructure graph (C078)
Status reports `version` and config `digest`; evidence (`conformance/PK_GATE_RESULTS.json`)
records the release `tree_digest`; provenance binds tree digest to builder id.
Join key for infrastructure graphs: `(host, version, tree_digest, config.digest)`.

## Retention, sampling, privacy, export (C079)

| Stream | Retention | Sampling | Privacy | Export |
|---|---|---|---|---|
| metrics | 30 d raw, 13 mo 5-min rollups | none | no tenant labels | Prometheus scrape |
| logs | 14 d hot, 90 d cold | `telemetry_sample_rate` for `info`; `warn`+ never sampled | redacted | JSON lines to collector |
| decisions | 90 d | none | redacted inputs | with logs |
| audit | 400 d minimum, immutable store | none | redacted | SIEM, chain verified on ingest |
| traces | 7 d | head-based per `traceparent` flag | no payload | OTLP (collector-side) |

## Dashboards and alerting (C080)
`dashboards/inv35_overview.json` (Grafana-style JSON); `alerts/inv35_alerts.json`
(Prometheus rule groups) differentiating **page** (safety/liveness) from **ticket** (capacity/perf).
