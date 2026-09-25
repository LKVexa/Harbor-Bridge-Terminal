# INV-37 observability and explainability

**Version:** 4.3.0 · Covers INV-37-C071–C080. Implementation: `telemetry.py`, `service.py`.

## Health / readiness (C071)
`BulkDataPlane.health()` → `status` (ok | degraded | frozen), `live`, `ready`, `version`, `artifact_digest`, `config_digest`, `policy_digest`, `profile`, `dependencies` (checkpoint, telemetry_export, policy, time), `capabilities` (shared_memory, host_guest, mode), `limits`, `utilization`, `uptime_s`. The embedding service exposes it on its own endpoint (INV-37 opens no sockets).

## Metrics (C072)
Pull via `metrics.snapshot()` or Prometheus text (`metrics.prometheus()`, prefix `inv37_`). Labels are bounded (no tenant or transfer ids).

| Signal | Metric |
|---|---|
| Rate | `transfers_created_total{transport}`, `transfers_verified_total`, `chunks_verified_total`, `bytes_verified_total`, `transfers_cancelled_total`, `transfers_recovered_total` |
| Errors | `errors_total{code,outcome}`, `digest_failures_total{level}`, `security_rejections_total{reason}`, `recovery_failures_total{code}`, `quarantines_total` |
| Latency | `chunk_accept_seconds`, `finalize_seconds`, `manifest_validate_seconds`, `resume_token_seconds` (p50/p95/p99/max) |
| Saturation / backlog | `transfers_active`, `transfers_stalled`, `admission.metrics()` (saturation, pending, throttle_reasons, per-tenant usage) |
| Resource / efficiency | `bytes_resent_total`, `duplicate_chunks_total`, per-transfer `copies` in diagnostics, `transitions_total{to}` |

## Structured logs (C073)
JSONL records: `ts, level, node, component, op, msg, tenant (pseudonym), workload, transfer_id, trace_id, span_id` + fields. Fields matching `payload|token|secret|key|password|data_bytes` are redacted. Export: stdout/file; failures increment `export_errors` and degrade health, never block transfers.

## Tracing (C074)
W3C `traceparent` accepted by `create_transfer`; malformed/all-zero ids start a new trace; `trace_id` appears on every log line and decision for the transfer; the response carries a child `traceparent` for downstream propagation. Sampling: `telemetry.trace_sample_ratio`. Cross-process propagation into INV-36/INV-38 is the embedding service's responsibility (not tested in-repo).

## Safe high-cardinality diagnostics (C075)
`diagnostics(token, tid)` returns state, last transition reason, verified count, transport, copy counts, trace id; tenant is a keyed pseudonym (`t_<hmac16>`) unless the caller holds `inspect`. No payload bytes are ever exposed.

## Decisions and explain (C076, C077)
Every automated decision is a `Decision{decision, outcome, reason_code, inputs, policy, constraints, transfer_id, trace_id, config_digest, artifact}`: admission (admit/reject), transport_select, stall_detect, quarantine, resume_reconcile, freeze. `explain(admin_token, tid)` renders them for operators.

## Release lineage (C078)
`telemetry.release_lineage()` = package, version, `source_digest` (SHA-256 over module sources), python, platform, `INV37_BUILD_COMMIT`, `INV37_NODE_ID`. Decision records and gate evidence carry the artifact digest and config digest so events correlate with a release and a node. A live infrastructure graph is external.

## Retention, sampling, privacy, export (C079)
| Stream | Default retention | Sampling | Privacy | Export |
|---|---|---|---|---|
| Metrics | embedding scraper policy (proposed 90 d) | none | aggregate only | pull |
| Logs | `telemetry.retention` (prod 30 d, edge 7 d) | level filter | pseudonymised tenants; redaction | stdout / file |
| Traces | 7 d (proposed) | `trace_sample_ratio` (prod 5 %) | ids only | via logs |
| Decisions | in-memory ring 5000 | none | pseudonymised inputs | explain |
| Audit | security policy (proposed 1 y), ship to SIEM | none | no payload/tokens | JSONL |

## Dashboards and alerts (C080)
Definitions: `observability/dashboard.json`, `observability/alerts.json` — alert classes separate ordinary load, degradation, policy rejection, dependency failure, attack and software defect. **Defined, not deployed**; validation during live failure/load testing is gate criterion `dashboards_alerts_deployed`.
