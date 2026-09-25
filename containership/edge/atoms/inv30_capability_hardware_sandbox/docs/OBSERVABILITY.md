# Observability (INV30-GAP-048..055 · INV-30-C071–C080)

* **Health endpoint (C071):** `ops health` / `CapabilityService.health()` → INV30_HEALTH/1: status, ready, version,
  enforcement, config digest, dependency states (pk_core, GAP-02, PLN-04, INV-41, INV-45, backend, circuit),
  active capabilities, saturation, lease epoch, audit head.
* **Metrics (C072):** `inv30_requests_total{op,outcome}`, `inv30_latency_ms_bucket{op}`, `inv30_active_capabilities`,
  contract signals `inv30_capability_derivations_total{narrowing}`, `inv30_bounds_violations_total`,
  `inv30_permission_violations_total`, `inv30_invalidated_uses_total`. Series capped at 10 000.
* **Logs (C073):** JSON lines: ts, level, event, node, component, tenant_bucket, workload, operation,
  correlation_id, trace_id, redacted fields.
* **Traces (C074):** W3C `traceparent` accepted on every request; child span returned; invalid/all-zero ids replaced.
* **High-cardinality safety (C075):** tenants → 64 hashed buckets in metrics/logs/decisions; raw tenant ids only in
  the access-controlled audit ledger; handles/bases never logged.
* **Decisions & explain (C076, C077):** every allow/deny → INV30_DECISION/1 with reason, inputs, policy,
  correlation id; `DecisionLog.explain(correlation_id)`.
* **Lineage (C078):** every record carries `release` (component version) and `node`; health carries config digest
  and audit head for correlation with the infrastructure graph.
* **Retention/sampling/privacy/export (C079):** logs 30 d (edge 7–14 d), trace sampling 10 % (cloud 5 %, far-edge
  1 %), 100 % of refusals logged, decision log in-memory ring 10 000 + export; audit ledger retained for the support
  lifetime of the release; export over the host's OTLP/Prometheus pipeline; no raw tenant data leaves the node.
* **Dashboards & alerts (C080):** `ops/dashboards/inv30.json`, `ops/alerts/inv30-alerts.yaml` — separate panels and
  alerts for ordinary load, degradation, policy rejection, dependency failure and **invariant violation (page)**.

## Deletion and legal hold
Retention is enforced at the sink. A legal hold is recorded as an audit-ledger event (`legal_hold.set` with scope and
authoriser) and suspends deletion for the scoped window; releasing it is another audited event. Proof of retention
application = sink deletion job logs + the audit events. Telemetry export failure never blocks enforcement: buffers are
bounded and drop oldest (`Logger` keeps ≤10 000 records, `DecisionLog` ring 10 000).
