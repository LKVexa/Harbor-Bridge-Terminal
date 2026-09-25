# INV-63 Telemetry Policy

| Field | Value |
|---|---|
| Document ID | INV63-REQ-TELEMETRY |
| INV-63 C-IDs covered | C073, C074, C075, C076, C077, C078, C079 |
| Status | DRAFT — pending approval (retention values are PROPOSED pending privacy review) |
| Owner | SRE lead (role) — UNASSIGNED |
| Reviewers | Privacy reviewer (role), Security reviewer (role) — UNASSIGNED |
| Revision | 4.3.0 |
| Approval date | pending |
| Supersedes | none |
| Change-review triggers | Revisit when interfaces, state ownership, topology or dependencies change, or when log/metric/decision fields change. |

## 1. Logs (C073) — `observability.py::Logger`
Required fields (`REQUIRED_LOG_FIELDS`): `ts, level, event, node, tenant, workload, component (default "INV-63"), operation, trace_id`. Extra fields are passed through `security.redact`. Records are JSON (`sort_keys`) to an injected `sink`; in-memory buffer bounded at 50,000 (halved on overflow).
Events emitted by `service.py`: `recovered` (records, epoch, torn_tail), `request_failed` (tenant, operation, trace_id, code, subject, message; level `warn`), `emergency_disable` (level `crit` when on).

## 2. Traces (C074) — `SpanContext`, `Tracer`
- Inbound W3C `traceparent` from the request envelope is honoured (version `00`, non-zero ids); malformed/absent → new trace, sampled with probability `telemetry_sampling`. Remote-parent sampled flag is respected.
- `handle` opens span `inv63.<op>` with `tenant`, `op` attrs (redacted). `trace_id` is returned in every `PK_DEPLOY_RESPONSE/1`, logged, and stored in every decision.
- Failed operations finish the span with status `ERROR:<code>`.
- Gap: trace context is **not** propagated to the lattice adapter (`LatticeAdapter` methods take no context) — waiver DEBT-003.

## 3. Sampling defaults

| Profile | `telemetry_sampling` | Source |
|---|---|---|
| secure default | 0.1 | `config.SECURE_DEFAULTS` |
| dev | 1.0 | `deploy/config/env/dev.json` |
| staging | 0.5 | `deploy/config/env/staging.json` |
| prod | 0.05 | `deploy/config/env/prod.json` |

Sampling applies to traces only; logs, metrics and decisions are not sampled.

## 4. Metrics — `Metrics.exposition` (Prometheus text, `inv63_` prefix)
Counters: `requests{op,outcome}`, `errors{op,code}`, `alerts{cls}`, `decisions{action}`, `reconciles{result}`, `actions{kind}`, `rollout_batches`, `rollbacks{kind}`, `idempotent_replays`. Gauges: `control_plane_up`, `stalled_workloads`. Histogram: `request_latency_ms{op}`. No tenant label is used (cardinality). Guard: 2000 label sets per store (`MAX_LABEL_SETS`).

## 5. Decisions and explain (C076–C078)
`DecisionLog.record` requires a non-empty reason; each `Decision` holds `seq, ts, tenant, component, action, reason, inputs, policies, constraints, trace_id, release, topology_digest` (`topology_digest` = first 16 hex of SHA-256 over hosts). `explain` op returns `INV63_EXPLAIN/1` (last 20). Actions recorded: `accept_desired`, `reconcile`, `defer_offline`, `rollout`, `auto_rollback`, `operator_rollback`, `frozen_add/remove`, `quarantined_add/remove`. `DecisionLog` is in memory (100k, halved on overflow); the durable audit record is the journal.

## 6. Retention (PROPOSED — pending privacy review, evidence `privacy-review`)

| Data | Proposed retention | Store |
|---|---|---|
| Metrics | 30 days | external Prometheus (deployment) |
| Logs | 14 days | external log pipeline (deployment) |
| Traces | 7 days (proposed) | external collector |
| Decision / audit journal (`journal.jsonl` + backups) | life of workload + 1 year | `state_dir`, backups |

None of this is enforced in code; the package has no exporter or retention job.

## 7. Privacy (C075, C079)
- Secrets: `security.redact` on log fields and span attrs; config secret scan rejects literals.
- Tenant pseudonymisation: `observability.tenant_hash(tenant)` = `"t-" + sha256("inv63:"+tenant)[:12]` for shared/exported diagnostics. `observability.export_records(records)` returns copies with `tenant` replaced by `tenant_hash` for shared sinks. In-process `Logger` records, decisions and `explain` keep the raw tenant id (tenant-scoped views); exporters must call `export_records`. The hash is unkeyed and the tenant namespace is small, so it is pseudonymisation, not anonymisation.
- Subject ids (`request_failed.subject`) are personal data if subjects are humans — covered by the privacy review.
- Error messages truncated to 512 chars (`DeploymentError.to_dict`).

## 8. Export
B-07 (`PK_DEPLOY_EVENT/1`, exporter-side mTLS), B-13 (Prometheus scrape). Log/trace sinks are injected callables. No exporter is bundled; the deployment supplies it.
