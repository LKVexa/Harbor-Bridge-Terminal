# Observability and explainability (C071-C080) + telemetry policy (C079)

* **Health/readiness (C071):** `SnapshotService.health()` → `PK_SNAPSHOT_HEALTH/1`: live, ready, status
  (ok/degraded/not_ready/disabled), not-ready reasons, version, profile, config revision + digest, per-dependency
  status, active capability set, stalled ops. An HTTP exposure is not included (in-process API).
* **Metrics (C072):** catalog `ops/metrics.json` (generated from `telemetry.METRICS`): RED
  (`inv26_requests_total{op,outcome,code,tenant}`, `inv26_request_latency_ms`), restore/capture histograms,
  saturation (`inv26_inflight`, `inv26_queue_depth`, admission rejections, breaker state, stalled ops,
  stored bytes), security counters (cross-tenant refusals, model mismatches, reseeds). Prometheus text via
  `Metrics.prometheus()`. Label values are redacted and capped (64 chars, 200 series/metric, overflow bucket).
* **Logs (C073):** one JSON object per line: ts, level, component, event, correlation_id, trace_id, span_id,
  tenant, redacted fields. Log injection neutralised by JSON encoding. Exporter failures are counted, never raised.
* **Tracing (C074):** W3C `traceparent` accepted from the caller (argument or request field) and continued;
  trace/span ids on every log line. Propagation into VMM/KMS calls is not possible over their APIs.
* **High-cardinality detail (C075):** tenant label allowed only on allow-listed metrics; per-operation detail
  lives in decision records keyed by correlation id, not in metric labels.
* **Decision records (C076) / explain view (C077):** `PK_SNAPSHOT_DECISION/1` for every operation — inputs,
  ordered checks with pass/fail, deciding rule (error code or `all-checks-passed`), config revision, policy
  version; summary mirrored into the audit chain. `explain(op_id, text=True)` renders an incident table.
* **Lineage (C078):** allowlisted keys (`app_release`, `release_id`, `commit`, `cluster`, `node`,
  `topology`, `change_ref`, `pipeline_run`, …) attached per request, redacted, length-capped. Correlation
  with a *live* infrastructure graph needs that graph (not available here).
* **Alerts/dashboards (C080):** `ops/alerts.json` separates attack, dependency failure, defect, integrity and
  degradation; `tools/drills.py` shows the four traffic classes fire disjoint alert sets.
  `dashboards/inv26-overview.json` lays out the panels.

## Telemetry policy (C079)
| Stream | Retention | Sampling | Privacy | Export |
|---|---|---|---|---|
| security audit | ≥ 1 year, WORM/anchored | none (every event) | tenant ids, no payloads | reliable, fail-closed for privileged ops |
| decision records | 2 000 in memory; summaries in audit | none | redacted | via audit |
| metrics | 30 days | n/a | bounded labels | pull (Prometheus text) |
| logs | 14 days | info+ in production (debug forbidden) | redacted | stream, best-effort |
| traces | 7 days | `telemetry.trace_sample_ratio` (default 0.1) | ids only | best-effort |
