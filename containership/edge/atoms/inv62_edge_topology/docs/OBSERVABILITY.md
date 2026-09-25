# Observability and explainability (MC-061 .. MC-070)

## Health / readiness / status — `TopologyService.health()`
`live`, `ready` (= config ∧ keys ∧ policy ∧ time ∧ state_store ∧ audit), `dependencies{}`, `mode`, `release{version,
artifact_digest, source_commit}`, `config{generation,digest}`, `tenants`, `links_down`, `oldest_measurement_age_s`,
`circuit`, `in_flight`, `protocols`. Contains no node names, tenant topology or secrets (tested).

## Metrics (Prometheus text via `Metrics.exposition()`)
| Metric | Type | Labels |
|---|---|---|
| `inv62_requests_total` | counter | family, op, outcome |
| `inv62_errors_total` | counter | code |
| `inv62_request_latency_ms` | histogram | family |
| `inv62_nodes` | gauge | tier |
| `inv62_links_down` | gauge | — |
| `inv62_partitions_total` | counter | — |
| `inv62_local_elections_total` | counter | — |
| `inv62_idempotent_replays_total` | counter | family |
| `inv62_admin_actions_total` | counter | action |
Cardinality: each label key admits `telemetry.max_label_values` distinct values; the rest collapse to `__overflow__`.
No tenant or node label is used on request metrics.

## Logs (JSON lines, schema v1)
Fields: `v ts level event component tenant op outcome code request_id trace_id span_id node site decision_id revision
config_generation release duration_ms mode detail`. Unknown fields are dropped; `detail` is redacted (keys matching
secret|credential|token|password|key; PKT1 strings); `node` is HMAC-pseudonymised unless `expose_node_names`.

## Traces
W3C `traceparent` accepted; child span created per request and returned in the response; head sampling
`trace_sample_rate`; spans bounded (5 000).

## Decision records and explain view
Every resolve stores `Decision{decision_id, tenant, inputs, graph_revision, config_generation, release,
considered[{node, latency_ms, verdict, layer, reason}], selected, outcome, mode}`; `explain(credential,
decision_id)` renders it (requires graph.read on that tenant). The `decision_id` is returned in the response and
in error details for `NO_CAPABLE_NODE`.

## Release lineage
`release_lineage()` reads `RELEASE_MANIFEST.json` (tree digest, source commit) or `INV62_ARTIFACT_DIGEST` /
`INV62_SOURCE_COMMIT`; it is attached to health, every log line, audit record and decision.

## Telemetry governance (proposed; owner approval pending)
| Data | Retention | Sampling | Privacy | Export | Deletion |
|---|---|---|---|---|---|
| metrics | 30 d (`retention_days`) | none | no tenant/node labels | Prometheus scrape | TSDB retention |
| logs | 30 d | all warnings+; info at `log_level` | pseudonymised nodes, redacted detail | stdout → collector | collector retention |
| traces | 7 d | `trace_sample_rate` (prod 1 %) | ids only | OTLP collector | backend retention |
| decisions | in-memory 10 k | all | tenant-scoped access | via logs | eviction |
| audit | ≥ 1 y (security owner to set) | all | allow-listed fields | SIEM with head anchoring | per legal hold |

## Dashboards and alerts
`ops/dashboards.json` and `ops/alerts.json` define the panels and an alert taxonomy that separates **load**,
**degradation**, **policy rejection**, **dependency failure**, **attack** and **software defect**.
