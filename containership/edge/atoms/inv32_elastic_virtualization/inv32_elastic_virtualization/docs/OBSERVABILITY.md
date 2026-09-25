# INV-32 Observability (v4.3.0)

Implementation: `telemetry.py`. Machine-readable dashboards/alerts: `ops/dashboards.json`, `ops/alerts.json`.

* **Health/inventory**: `controller.health()` (`PK_HEALTH/1`: live, ready, mode, checks, degraded) and
  `controller.inventory()` (version, schemas, config revision/digest, provider version/capabilities, epoch,
  circuit, feature gates). No secrets or cross-tenant identifiers are exposed.
* **Metrics**: `telemetry.METRIC_DEFS` fixes names, types, units and allowed label keys; tenant/guest IDs are
  never labels; refusal reasons are a closed set (others fold into `other`).
* **Logs**: JSON lines; `ts, severity, component, host, tenant_ref, guest_ref (keyed pseudonyms), operation_id,
  trace_id, controller_epoch, config_digest, outcome, audit_sequence, audit_hash, fields, message`. Severity
  policy: INFO commit; NOTICE validation/policy/overload rejections; WARNING dependency/security rejections;
  ERROR incidents/internal errors; CRITICAL integrity failure.
* **Tracing**: W3C `traceparent` accepted on requests (malformed → new root, never an error); spans
  `decode, authorize, state_read, decision, fence, provider_mutation, verification, commit, audit_append`;
  attributes restricted to `operation, outcome, code, phase, priority` (≤64 chars). Sampling: head flag,
  plus 100% of errors and slow (≥50 ms) spans. Provider propagation of trace context is BLOCKED (ADR-0001).
* **Explain**: `controller.explain(token, operation_id)` (action `explain.read`) returns request, live state
  version, floor/ceiling, reserve/free, policy version + decision id, capability generation, provider version,
  epoch, config digest/revision, release, plan, `controlling_rule`, outcome, provider request id; replays are
  marked `replayed: true` in the result.
* **Retention/privacy/export**: `telemetry.TELEMETRY_POLICY`.
