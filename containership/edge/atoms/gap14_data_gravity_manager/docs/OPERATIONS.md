# GAP-14 v4.3.0 — Operations Guide

Covers `F01`–`F05` for every component and P1-17/18/19/20.

## 1. Configuration knobs (`F01`)

Configuration is a signed `PK_GAP14_CONFIG/1` document (`schemas/PK_GAP14_CONFIG-1.schema.json`) activated through `ConfigManager.activate` / `load_file`. **Reloadable** knobs take effect on the next decision after activation (`DecisionService._sync_config`); **restart-bound** knobs (breaker thresholds, `max_concurrent`, `max_per_tenant`) need a process restart.

| Knob | Default | Safe range | Reload | Purpose |
|---|---|---|---|---|
| `compute_relocation_cost` | 25 | 0 – 1e+06 | reloadable | Base cost units to relocate compute |
| `decision_deadline_s` | 0.05 | 0.005 – 5 | reloadable | End-to-end decision budget (SLO p99 50 ms) |
| `dependency_timeout_s` | 0.02 | 0.001 – 2 | reloadable | Per-dependency call timeout cap |
| `retry_max_attempts` | 2 | 1 – 5 | reloadable | Attempts for idempotent reads |
| `breaker_failure_threshold` | 5 | 1 – 100 | restart-bound | Consecutive failures before circuit opens |
| `breaker_reset_s` | 10 | 0.1 – 600 | restart-bound | Open-circuit cool-down |
| `max_concurrent` | 4 | 1 – 10000 | restart-bound | Admission: concurrent decisions per process (CPU-bound; scale with processes) |
| `max_per_tenant` | 0 | 0 – 10000 | restart-bound | Admission: per-tenant concurrent decisions (0 = max_concurrent) |
| `max_payload_bytes` | 262144 | 1024 – 1.67772e+07 | reloadable | Admission: request size |
| `max_batch` | 500 | 1 – 100000 | reloadable | Admission: datasets per batch/DAG |
| `clock_skew_s` | 5 | 0 – 60 | reloadable | Allowed future-dating of artifacts |
| `ttls.policy_verdict` | 300 s | 1 – 86400 | reloadable | Freshness TTL |
| `ttls.topology_snapshot` | 600 s | 1 – 86400 | reloadable | Freshness TTL |
| `ttls.convergence_proof` | 60 s | 1 – 86400 | reloadable | Freshness TTL |
| `ttls.placement_snapshot` | 120 s | 1 – 86400 | reloadable | Freshness TTL |
| `ttls.price_feed` | 3600 s | 1 – 86400 | reloadable | Freshness TTL |

Other signed-config sections: `site_jurisdictions` (jurisdiction tags forwarded to GAP-13), `site_economics` (per-site carbon/power/thermal/storage/IOPS pricing — the *only* place prices come from), `shadow_model` (`revision`, `compute_relocation_cost`), `canary_percent` (0–100, requires `shadow_model`), `dev_flags` (refused in production).

Ownership of each knob: the GAP-14 service owner; `ttls.policy_verdict` additionally requires sign-off from the GAP-13 owner, `ttls.convergence_proof` from GAP-05.

## 2. Deployment and upgrade order (`F02`)

1. Publish new schemas; upgrade **producers** (GAP-13, GAP-03, GAP-05, SCH-01) to emit signed artifacts and distribute their keys to GAP-14's trust store.
2. Deploy GAP-14 v4.3.0 in `staging` mode (non-executable) against live producers; compare with v4.2.0 decisions (shadow).
3. Upgrade PLN-06 to verify `PK_DATA_MOVE_HANDOFF/1` signatures and honour `handoff_id` idempotency.
4. Activate a `production` config revision; roll replicas one at a time.

**Mixed versions:** v4.2.0 callers using `GravityManager.recommend` directly are unaffected (engine API unchanged). A v4.3.0 replica and a v4.2.0 replica can coexist, but only v4.3.0 envelopes are accepted by an upgraded PLN-06. Replay detection is per-replica (DESIGN R-3): route by tenant during a rollout.

**Process model:** CPU-bound; run one worker per core with `max_concurrent` ≤ 4 (see `evidence/bench_v4.3.0*.json`).

## 3. Health, metrics, logs, traces, explain

* `DecisionService.health()` → `PK_HEALTH/1`: `live` (process), `ready` = config active ∧ last audit write succeeded ∧ no decision-path breaker open. Map to `/livez` and `/readyz`; `reason_code: G14_NOT_READY` when not ready.
* Metrics (`Registry.exposition()`, Prometheus text 0.0.4): `gap14_gravity_recommendations_total{direction,outcome,mode}`, `gap14_illegal_options_eliminated_total{direction,code}`, `gap14_no_legal_option_total`, `gap14_refusals_total{code,category}`, `gap14_move_cost_estimate{direction}`, `gap14_decision_latency_seconds{mode}`, `gap14_dependency_latency_seconds{dependency,outcome}`, `gap14_pkcore_handshake_seconds{result}`, `gap14_audit_records_total{result}`, `gap14_config_activations_total{result}`, `gap14_admission_rejected_total{code}`, `gap14_shadow_divergence_total{model}`, `gap14_calibration_drift_alarms_total{dimension}`. Every metric has a fixed label set and a series cap; overflow folds into `__overflow__`. Tenant/workload/dataset/request/decision IDs are never labels (test-enforced).
* Logs: one JSON object per line; `tenant_id`, `workload_id`, `dataset`, `subject` are keyed-hash redacted; `token`, `sig`, `mac`, `secret`, `claims` are dropped.
* Traces: W3C `traceparent` accepted on `decide`; `trace_id`/`span_id` recorded in logs, provenance and refusal audit records.
* Explain: `DecisionService.explain(decision_id, token)` → `PK_GRAVITY_EXPLAIN/1` (needs `gravity:explain` for the decision's tenant). The explain cache is bounded (2048 per process); the audit log is the durable source.

### Suggested alerts

| Alert | Expression (PromQL sketch) | Runbook |
|---|---|---|
| Decision path not ready | readiness probe failing > 2 min | RB-01 |
| Audit write failures | `increase(gap14_audit_records_total{result="failed"}[5m]) > 0` | RB-02 |
| Fail-closed surge | `sum(rate(gap14_refusals_total{category=~"security|stale-data"}[5m])) > 1` | RB-03 |
| Latency SLO burn | p99 of `gap14_decision_latency_seconds` > 0.05 for 15 m | RB-04 |
| Drift | `increase(gap14_calibration_drift_alarms_total[1h]) > 0` | RB-06 |

## 4. Troubleshooting: reason codes (`F03`)

| Code | Category | Disposition | Meaning | Safe corrective action |
|---|---|---|---|---|
| `PK_GRAVITY_NO_LEGAL_OPTION` | policy | fail-closed | residency/capability leaves no legal option | Inspect elimination_details; do not override residency. |
| `PK_GRAVITY_COST_MODEL_ERROR` | dependency | fail-closed | a legal option cannot be honestly costed | Check topology/cost feed for the missing route. |
| `G14_INVALID_REQUEST` | caller | fail-closed | request failed strict validation | Fix the payload; see details.field. |
| `G14_PAYLOAD_TOO_LARGE` | caller | fail-closed | payload exceeds admission size bound | Split the batch or raise limits via signed config. |
| `G14_UNAUTHENTICATED` | security | fail-closed | no valid capability token | Obtain a token from the identity service. |
| `G14_FORBIDDEN` | security | fail-closed | principal lacks scope or tenant access | Grant the scope in the identity service; never bypass. |
| `G14_CROSS_TENANT` | security | fail-closed | workload tenant differs from dataset tenant | Tenancy boundary is absolute; no action short of re-tenanting data. |
| `G14_SIGNATURE_INVALID` | security | fail-closed | signature or MAC verification failed | Check key distribution; treat as possible tampering. |
| `G14_UNKNOWN_ISSUER` | security | fail-closed | issuer/key id not in trust store | Rotate trust store via signed config. |
| `G14_BINDING_MISMATCH` | security | fail-closed | artifact bound to a different request | Possible replay; investigate the producer. |
| `G14_REPLAY` | security | fail-closed | nonce/decision id already seen | Possible replay; investigate. |
| `G14_VERSION_ROLLBACK` | security | fail-closed | policy/config/snapshot version went backwards | Confirm the authority's revision; reset watermark only by operator action. |
| `G14_STALE_INPUT` | stale-data | fail-closed | decision input older than its TTL | Refresh the producing service; check its health. |
| `G14_CLOCK_SKEW` | stale-data | fail-closed | artifact issued in the future beyond skew allowance | Check NTP on producer and GAP-14 hosts. |
| `G14_DEPENDENCY_TIMEOUT` | dependency | retryable | dependency exceeded its deadline | Check dependency latency dashboards. |
| `G14_DEPENDENCY_UNAVAILABLE` | dependency | retryable | dependency returned an error or is partitioned | Check dependency health. |
| `G14_CIRCUIT_OPEN` | dependency | degradable | circuit breaker open for dependency | Wait for half-open probe; fix dependency. |
| `G14_DEADLINE_EXCEEDED` | dependency | retryable | end-to-end decision deadline exceeded | Retry with a new deadline; investigate slow dependency. |
| `G14_CANCELLED` | caller | retryable | caller cancelled the decision | None. |
| `G14_OVERLOADED` | dependency | retryable | admission control rejected (concurrency/queue) | Back off; scale out. |
| `G14_NOT_CONVERGED` | policy | fail-closed | dataset has no valid convergence proof | Wait for GAP-05 convergence. |
| `G14_COMPUTE_INCOMPATIBLE` | policy | fail-closed | compute site lacks arch/runtime/capacity | Check SCH-01 placement data. |
| `G14_QUOTA_EXCEEDED` | policy | fail-closed | destination quota/reservation insufficient | Request quota or choose another site. |
| `G14_HANDOFF_REJECTED` | dependency | operator-actionable | PLN-06 refused the handoff | Inspect PLN-06 response; decision remains unexecuted. |
| `G14_HANDOFF_DUPLICATE` | caller | degradable | idempotent duplicate handoff; original returned | None. |
| `G14_NOT_EXECUTABLE` | security | fail-closed | simulation/shadow artifact submitted for execution | Simulations never execute; run a real decision. |
| `G14_AUDIT_UNAVAILABLE` | internal | fail-closed | audit sink write failed; decision withheld | Restore audit storage; no decision is emitted without audit. |
| `G14_AUDIT_CHAIN_BROKEN` | security | operator-actionable | audit chain verification failed | Preserve evidence; start incident runbook RB-02. |
| `G14_CONFIG_INVALID` | caller | fail-closed | configuration failed schema/semantic validation | Fix config; previous revision stays active. |
| `G14_CONFIG_FORBIDDEN_IN_PRODUCTION` | security | fail-closed | dev/test convenience enabled in production mode | Remove the flag. |
| `G14_NOT_READY` | internal | retryable | service not ready (config/deps) | See /readyz details. |
| `G14_INTERNAL` | internal | operator-actionable | unexpected internal fault | Collect trace id; file incident. |
| `G14_PKCORE_MISSING` | dependency | fail-closed | pk_core runtime not importable | Install the certified pk_core build. |
| `G14_PKCORE_UNTRUSTED_PATH` | security | fail-closed | pk_core imported from user-global/unapproved path | Use the locked environment. |
| `G14_PKCORE_INCOMPATIBLE` | dependency | fail-closed | pk_core version/API/schema outside certified range | Install a certified version. |
| `G14_PKCORE_DIGEST_MISMATCH` | security | fail-closed | pk_core build digest differs from pin | Reinstall from the locked artifact. |
| `G14_GATE_PARTIAL` | internal | fail-closed | conformance gate did not attempt every check | Never report partial as PASS; fix skips. |
| `G14_DRIFT_DETECTED` | internal | operator-actionable | cost model predictions drifted from observations | Recalibrate; shadow the new model first. |

## 5. Rollback and disable (`F04`)

* **Config rollback:** `ConfigManager.rollback(revision, now, actor)` re-activates a previously verified revision and emits `config.rolled_back` into the audit chain. Forward activation afterwards must exceed the highest revision ever seen.
* **Code rollback:** redeploy the previous immutable artifact (verify `MANIFEST.sha256`). The audit file format (`PK_AUDIT_RECORD/1`) is unchanged across 4.x, so rollback does not invalidate retained evidence; `verify-audit` works on the full chain regardless of which version wrote each record.
* **Emergency disable:** stop routing `decide` traffic (estate registry); in-flight decisions without an audit record were never returned. Already-issued handoffs are idempotent at PLN-06; handoffs expire after 300 s.

## 6. Certification manifest (`F05`)

`CERTIFICATION_MANIFEST.json` lists every one of the 1,831 checklist items with status and evidence paths; regenerate with `python gap14_data_gravity_manager/tools/build_manifest.py`.
