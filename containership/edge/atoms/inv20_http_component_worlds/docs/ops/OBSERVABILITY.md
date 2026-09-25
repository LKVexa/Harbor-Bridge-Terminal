# Observability specification (component 16)

Metrics (declared in `observability.METRIC_SPECS`, max 1000 series, unknown label values → `other`):
`requests_handled{status_class}`, `egress_denials{reason}` (reason ∈ `egress.REASONS` — never the raw
host; this intentionally replaces the 4.2.0 contract wording "by attempted host", which was an unbounded
attacker-controlled label), `body_bytes{direction}`, `trailer_resolutions{outcome}`, `request_duration`,
`queue_wait`, `active_requests`, `active_connections`, `retries{code}`, `cancellations`,
`timeouts{stage}`, `dependency_up{dependency}`, `saturation{resource}`.

Logs: `INV20_LOG/1` JSON lines — ts, severity, event, node, site, env, release, config_revision,
pseudonymous tenant (`t_<sha256[:12]>`), workload, trace_id, reason code, redacted fields
(authorization/cookie/token/key…, secret query params), strings bounded to 256 chars.

Tracing: W3C `traceparent` continued only from trusted (authenticated same-tenant) peers; outbound
propagation only to trusted destinations. Spans: policy decision, queue wait, handler dispatch,
outgoing request, streaming lifecycle.

Explainability: every egress decision emits (reason, safe destination, policy version, config revision)
and an audit record (`AuditLog`), correlated by trace id and release.

Governance: retention — metrics 30 d, logs 14 d, audit 400 d (compliance owner to confirm); sampling
1 % traces (config `trace_sample_rate`); PII: tenant ids pseudonymised, bodies never logged
(`log_bodies` must be false); export per tenant boundary; read access to audit logs is itself audited.

Dashboards (definitions; no backend deployed): traffic/load, policy denials by reason, dependency
health, saturation/backlog, security/anomaly (denial spikes, capability-invalid bursts).
Alerts: `degradation` (phase=degraded > 5 min), `policy_rejection_spike` (denials ×5 baseline),
`dependency_failure` (dependency_up=0), `suspected_attack` (capability_invalid or dns_denied bursts),
`software_defect` (E_HANDLER_TRAP / E_ILLEGAL_STATE rate > 0.1 %).
