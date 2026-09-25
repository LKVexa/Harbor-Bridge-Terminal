# Observability (G13-MC-021…027)

## Health {#health}
`GET /v1/health` liveness (unauthenticated). `GET /v1/ready` → 200/503 with `not_ready_reasons` and `degraded`. `GET /v1/status` (`policy.status`) → `PK_POLICY_STATUS/1`: engine release, active bundle identity, key id, trust-store version, verifier version, age, staleness thresholds/mode, anti-rollback floors, control state, dependency state, audit health, in-flight, configuration provenance.

## Metrics {#metrics}
Prometheus text at `GET /metrics`: `g13_verdicts_total{effect,tenant(pseudonymised)}`, `g13_default_denies_total`, `g13_specificity_ties_total`, `g13_rule_hits_total{rule}`, `g13_errors_total{code}`, `g13_evaluate_latency_ms_bucket/_sum/_count`, `g13_bundle_age_seconds`, `g13_bundle_time_to_expiry_seconds`, `g13_bundle_generation`, `g13_bundle_activations_total{kind}`, `g13_bundle_verifications_total{state}`, `g13_stale_refusals_total`, `g13_stale_evaluations_total{mode}`, `g13_overload_shed_total`, `g13_auth_denied_total{capability}`, `g13_dependency_failures_total{dependency}`, `g13_distribution_failures_total`, `g13_control_state{state}`. Series cardinality capped at 5 000.

## Logging {#logging}
JSON lines with registered event IDs `G13-L001…G13-L070` (`telemetry.EVENT_IDS`), always carrying component/node/site/environment. Only allow-listed fields are emitted.

## Tracing {#tracing}
W3C `traceparent` accepted on `/v1/*`; span `gap13.evaluate`/`gap13.explain`; verdict carries `trace_id`. Export via `Tracer(sink=...)` (wire to OTLP in deployment).

## Privacy {#privacy}
Field classes in `telemetry.FIELD_CLASSES`: public / pseudonymous (salted SHA-256: tenant, workload, subject) / sensitive (never exported: request, attributes, tokens). Retention: logs 30 d, metrics 395 d, traces 7 d, audit 7 y. Sampling: traces 5 %, errors always.

## Lineage {#lineage}
`Lineage(engine_release, engine_artifact_digest, topology_source, topology_snapshot)` annotates every service verdict; with `bundle.digest` this binds a decision to exact engine bytes, policy bytes and topology.

## Audit {#audit}
`audit.jsonl`, `PK_POLICY_AUDIT_EVENT/1`, hash-chained; verify with `python -c "from gap13_policy_engine.audit import read_log, verify_chain; print(verify_chain(list(read_log('state/audit.jsonl'))))"`.

## Alerts {#alerts}
`ops/alerts/gap13_alerts.yaml`; dashboard `ops/dashboards/gap13_overview.json`. Alerts distinguish: normal default-deny load, policy rejection, stale warning/hard, dependency failure, auth-denial spikes (attack indicator), overload, software faults (G13-E5xx/500).
