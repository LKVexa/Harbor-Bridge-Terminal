# SLOs, telemetry policy, dashboards and alerts (C071–C080, C091)

## SLOs (C091)

| SLO | SLI | Target | Window | Error budget | Owner |
|---|---|---|---|---|---|
| confinement | accesses outside the tenant partition observed by canary/escape suites | 0 | per release + continuous fuzz | **none — security invariant, never consumed** | security (UNASSIGNED) |
| verification | loaded modules with a valid proof bound to their digest | 100 % | continuous | **none** | engineering (UNASSIGNED) |
| availability | `health().ready` probes true / total | 99.9 % proposed | 30 d rolling | 43 min / 30 d | operations (UNASSIGNED) |
| verify latency | `sfi_submit_latency_ms` p95 | ≤ 2× release baseline | 7 d | 5 % of windows | engineering |
| overhead | V8 benchmark overhead p50 | ≤ 15 % (contract) | per release | **currently missed on load-bound workload** | performance (UNASSIGNED) |

Burn policy: availability budget burn rate > 2 over 1 h pages; > 1 over 6 h tickets. Security SLOs page
on the first violation (SEV-0). Support commitment: business-hours support plus 24×7 SEV-0/1 paging **once
on-call rotations exist** (OWNERSHIP.md) — none exist today.

## Metrics (C072)

| Metric | Type | Labels (bounded) | Meaning |
|---|---|---|---|
| `sfi_modules_verified_total` | counter | outcome | sealed submissions |
| `sfi_modules_loaded_total` | counter | outcome, code | rejected submissions by error code |
| `sfi_unmasked_accesses_total` | counter | — | accesses that failed verification |
| `sfi_loads_total` | counter | outcome, code | trusted-loader outcomes |
| `sfi_executions_total` | counter | outcome | engine jobs |
| `sfi_authn_failures_total` | counter | — | failed authentications |
| `sfi_quarantine_actions_total` | counter | action, scope | operator controls |
| `sfi_submit_latency_ms` | histogram | — | submit latency (RED) |
| admission snapshot (health) | gauges | — | active, waiting, shed, peak (USE / saturation / backlog) |

Label cardinality is capped at 256 series per metric (`__overflow__`). Tenant ids are never metric labels in
production code paths (they appear only in logs/audit, which have access control).

## Logs and traces (C073, C074)

JSON lines with `ts, level, node, component, operation, tenant, workload, trace_id, span_id` plus
allowlisted fields. W3C `traceparent` is accepted on submit/load/execute and returned by submit; malformed
headers start a new trace; the trace id is recorded in audit events so one operation correlates across
submit → load → execute without crossing tenant context (tenant comes from the authenticated principal,
never from trace headers).

## Diagnostics and explain (C075–C077)

Every automated decision (submit sealed/rejected, load loaded/rejected) creates an explain record with
inputs (digests, tenant, workload), policy (profile digest, config digest, generation), topology (node,
engine, service version) and the deciding constraint. Error envelopes carry the decision id. High-cardinality
detail (instruction offsets, function indices) is available in error details, allowlisted and redacted
(no bytes, no secrets). Explain records are bounded (10 000) and in memory; durable reasons are the audit
events (C076).

## Release lineage and infrastructure correlation (C078)

Audit events carry `profile_sha256`, `config_sha256`, `artifact_sha256`, `generation`; health carries
`version`; release/MANIFEST.json maps version → artifact digests. Correlation with the *live infrastructure
graph* (node inventory, placement) is an **open external item**: no infrastructure graph is available to
this component.

## Telemetry governance (C079)

| Stream | Retention | Sampling | Privacy | Export |
|---|---|---|---|---|
| audit | ≥ 400 days (proposed) | none (100 %) | allowlisted fields; no bytes/secrets | SIEM + checkpoints |
| logs | 30 days (`telemetry.retention_days`) | 100 % warnings+; info per config | allowlist + redaction | log pipeline |
| metrics | 400 days downsampled | n/a | no tenant labels | Prometheus |
| traces | 7 days | `telemetry.trace_sample_rate` | ids only | tracing backend |

Retention enforcement is the telemetry backend's job; the component only emits.

## Dashboards and alerts (C080)

`ops/dashboards/inv45-overview.json` separates: **ordinary load** (submit rate, latency), **degradation**
(health status, audit spool, breaker), **policy rejection** (rejections by code category `policy`/`input`),
**dependency failure** (`dependency` category, `SFI_TRUST_STALE`), **attack indicators** (`security`/`auth`
categories, replay, unmasked accesses, authn failures) and **software defect** (`SFI_INTERNAL_INVARIANT`).
`ops/alerts/inv45-rules.yml` routes each class to a runbook section. Neither has been loaded into a live
Grafana/Prometheus (open).
