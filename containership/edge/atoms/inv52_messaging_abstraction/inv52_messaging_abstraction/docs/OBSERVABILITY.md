# Observability — `DOC-INV52-OBS` v4.3.0 (C071-C080)

| Need | Implementation |
|---|---|
| Health, readiness, version, config, dependencies (C071) | `PubSub.health()`, `ManagedBus.health()` (lifecycle + dependency probes), `__version__`, `ConfigManager.active` provenance; schema PK_MSG_HEALTH/1 |
| Rate, errors, latency, saturation, backlog (C072) | `metrics()`: counters (`published`, `delivered`, `denied`, `invalid`, `oversize`, `shed`, `route_errors`, `sink_errors`, `duplicates`, `partial`, `quarantined`…), fixed-bucket latency histogram with p50/p95/p99, `dead_letter_backlog`, outcomes, dead-letter reasons; `prometheus_text` exposition. Process CPU/memory are exported by the host runtime (declared). |
| Structured logs with stable ids (C073) | `StructuredLogger`: `ts, level, node, tenant, workload, component, operation, release, event`; redacted; payload removed |
| Trace context (C074) | `traceparent` validated, propagated to subscribers, decisions and CloudEvents; `child_traceparent` for hops |
| Safe high-cardinality detail (C075) | message ids only in decisions/explain (bounded ring, operator-only); metric labels fixed: component, node, release, outcome, reason |
| Reason for every automated decision (C076) | PK_MSG_DECISION/1 for every attempt incl. refusals, one reason per route |
| Explain view (C077) | `PubSub.explain(message_id)`: outcome, per-route reason, topic state at decision and now, allowed publishers, limits |
| Release lineage & infra correlation (C078) | `release` and `node` on every log line and metric; decision ids are `d-<bus-instance>-<seq>`. Live infrastructure graph correlation: BLOCKED (needs the platform graph service). |
| Retention, sampling, privacy, export (C079) | `observability.TELEMETRY_POLICY` (PROPOSED): in-process bounds, deterministic sampling that never drops failures/security events, no payloads, no cross-tenant export |
| Dashboards and alerts (C080) | `deploy/observability/dashboard.json`, `alerts.yaml`; classes computed by `observability.classify`: normal_load, overload, degradation, policy_rejection, dependency_failure, attack_suspected, software_defect, client_defect. Thresholds PROPOSED. Not yet loaded into a live Grafana/Prometheus (BLOCKED). |
