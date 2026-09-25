# Telemetry: health, metrics, logs, traces, retention and privacy (C071–C079)

## Surfaces
- **Health/readiness** — `Broker.health()` (and wire op `health`): `live`, `ready`, `mode`, config digest, audit
  head, per-queue depth/breaker/frozen/stalled.
- **Metrics** — `Metrics.prometheus()`: `inv53_build_info{version,config_digest,…}` (release lineage),
  `inv53_ops_total{op,tenant,code}`, `inv53_refusals_total{op,code}`, `inv53_op_seconds` histogram,
  `inv53_ready|in_flight|dead_lettered{tenant,queue}`, `inv53_metrics_dropped_series`.
- **Logs** — one JSON object per line: ts, level, component, event, trace_id/span_id, redacted fields.
- **Traces** — W3C `traceparent` accepted on requests, a child span generated per operation and written into
  `message.headers.traceparent` on put so consumers continue the trace.
- **Decision events** — every refusal logs `inv53.decision/1 {action, code, reason}`.
- **Explain** — `explain` op / `store explain` CLI: where a message is and why.

## Cardinality and privacy rules
Label allow-list: queue, tenant, op, code, reason, state. Message ids, principals and lease tokens are never
labels. Series are capped (default 2,000); overflow is counted, not raised. Log fields whose names match
payload/body/secret/key/token/lease/mac/password/credential/authorization are replaced by a length + sha256
prefix marker; strings are truncated at 512 chars. Audit records refuse key/mac/lease_token/payload fields.

## Retention and sampling (policy; enforcement belongs to the telemetry backend)
| Signal | Retention | Sampling | Export |
|---|---|---|---|
| Audit log | ≥ 1 year, immutable storage; head anchored daily | none | shipped to the security archive |
| Metrics | 30 days raw, 13 months downsampled | none | Prometheus scrape |
| Info logs | 14 days | `StructuredLogger(sample={"op": r})` configurable | log pipeline |
| Warning/error logs, decision events | 90 days | none | log pipeline |
| Traces | 7 days | head-based 10 % default, 100 % on refusal | OTLP collector |

Export to GAP-09 Unified observability is **not integrated** (no collector reachable from this build).
