# GAP-10 Component Design Records

One record per component (checklist: *design/ADR section defining scope, non-goals, authoritative data, trust boundaries, dependencies*). Trust boundaries and authoritative data are fixed globally in ADR-0001.

## C01 — Authenticated telemetry adapter for GAP-09 [P0]

- **Scope:** Verify, authorize, freshness-check and normalise PK_TELEMETRY_ENVELOPE/1 into CanonicalSample with provenance.
- **Non-goals:** Sensor attestation itself (GAP-09); transport.
- **Fail-closed default:** Any verification/parse/freshness failure rejects the sample with a GAP10-E-TEL code; node keeps its prior (or constrained) band.
- **Identities/permissions:** Reporter key needs capability telemetry.publish scoped to its node glob.
- **Limits/timeouts:** 64 KiB envelope, 64 sensors, 30 s max age, 5 s future skew, per-(identity,node) monotonic seq.
- **Signals:** gap10_telemetry_samples_total{outcome}, adapter.health()
- **Restart/recovery:** Last accepted seq persisted in node state; replay below it rejected after restart.
- **Code:** `production/telemetry.py`, `production/keys.py` · **Artefacts:** `schemas/PK_TELEMETRY_ENVELOPE-1.schema.json`, `fixtures/telemetry_envelope_*.json`
- **Tests:** `test_c01_*`

## C02 — Downstream scheduler enforcement adapter [P0]

- **Scope:** Turn PK_POWER_CEILING/1 into a hard admission/placement limit with decision binding, TOCTOU revalidation, drain, divergence alarm.
- **Non-goals:** Placement scoring; real SCH-01 code (must implement SchedulerBackend).
- **Fail-closed default:** No limit applied -> limit 0; decision missing/stale -> FailClosedContract.absent_fraction (default 0).
- **Identities/permissions:** Adapter holds only scheduler set_limit/commit/drain rights.
- **Limits/timeouts:** Admission serialised under adapter lock; floor rounding.
- **Signals:** gap10_enforcement_divergence{consumer=scheduler}
- **Restart/recovery:** Limits re-applied from current decisions on apply().
- **Code:** `production/enforcement.py`
- **Tests:** `test_c02_*`

## C03 — Elasticity-plane enforcement adapter [P0]

- **Scope:** Propagate pool-level sum of node ceilings as a hard scale cap with refill cooldown.
- **Non-goals:** Autoscaling policy itself (PLN-05).
- **Fail-closed default:** Missing decisions count as 0 capacity; cap raises held for refill_cooldown_s.
- **Identities/permissions:** Adapter holds only set_cap on PLN-05.
- **Limits/timeouts:** Cooldown default 120 s.
- **Signals:** cap per pool (backend)
- **Restart/recovery:** Cap recomputed from view each apply().
- **Code:** `production/enforcement.py`
- **Tests:** `test_c03_*`

## C04 — Durable per-node state store [P0]

- **Scope:** Atomic, checksummed, fenced per-node persistence of band, hysteresis band, last trusted sample/seq, policy revision, controls.
- **Non-goals:** Fleet inventory; multi-site replication (use an external linearizable store in production).
- **Fail-closed default:** Corrupt/missing record -> node starts critical; store outage -> decisions capped at critical and health unsafe.
- **Identities/permissions:** Filesystem write access to the state directory only.
- **Limits/timeouts:** One document per node; retries bounded by store_retry/breaker.
- **Signals:** gap10_dependency_failures_total{dependency=state-store}
- **Restart/recovery:** Restart resumes max(persisted band, critical).
- **Code:** `production/store.py`
- **Tests:** `test_c04_*`

## C05 — Atomic policy distribution and activation service [P0]

- **Scope:** Content-addressed immutable revisions, compare-and-swap activation, staged cohorts, rollback, provenance.
- **Non-goals:** Policy authoring UI; cross-scope inheritance.
- **Fail-closed default:** Invalid/unsigned/conflicting revisions are never activated; active revision unchanged.
- **Identities/permissions:** policy.author per scope glob.
- **Limits/timeouts:** Single lock per service; history stack per scope.
- **Signals:** audit policy.* events
- **Restart/recovery:** In-memory in this package; production must back it with the same durable store (see ADR-0003).
- **Code:** `production/policy_service.py`
- **Tests:** `test_c05_*`

## C06 — Policy authorization/signature verification [P0]

- **Scope:** Signature on canonical bundle; two-person rule for any relaxation of safety limits.
- **Non-goals:** Key custody (HSM).
- **Fail-closed default:** Bad/unknown signature -> POLICY_UNSIGNED; relaxation without distinct approver -> POLICY_UNAUTHORIZED; audited as security.failure.
- **Identities/permissions:** policy.author + distinct policy.approve-relax identity.
- **Limits/timeouts:** n/a
- **Signals:** audit policy.rejected / security.failure
- **Restart/recovery:** Stateless verification.
- **Code:** `production/policy_service.py`, `production/keys.py`
- **Tests:** `test_c06_*`

## C07 — Explicit fail-closed scheduler behavior when GAP-10 is absent/unhealthy [P0]

- **Scope:** Consumer-side CeilingView: never interprets absence/staleness/unhealth as capacity.
- **Non-goals:** GAP-10 availability itself.
- **Fail-closed default:** absent_fraction (<= critical, default 0) and min with last decision.
- **Identities/permissions:** Consumer read-only.
- **Limits/timeouts:** max_decision_age_s default 15 s.
- **Signals:** effective()['fail_closed']
- **Restart/recovery:** Empty view after consumer restart -> admits nothing.
- **Code:** `production/enforcement.py`
- **Tests:** `test_c07_*`

## C08 — Controller ownership/leader fencing [P0]

- **Scope:** Per-shard lease with monotonically increasing fencing token checked by controller, store and consumers.
- **Non-goals:** Consensus implementation (production uses etcd/consul/DB CAS behind LeaseManager).
- **Fail-closed default:** No valid lease -> controller refuses to decide; stale token rejected by store and CeilingView.
- **Identities/permissions:** controller.lead.
- **Limits/timeouts:** Lease TTL default 10 s (harness 30 s); renewed on each decision.
- **Signals:** audit ownership.*
- **Restart/recovery:** New leader gets a strictly greater token.
- **Code:** `production/coordination.py`, `production/controller.py`, `production/store.py`, `production/enforcement.py`
- **Tests:** `test_c08_*`

## C09 — Hardware/site calibration inventory [P1]

- **Scope:** Validated per-hardware-class limits; derived policy always below vendor throttle.
- **Non-goals:** Hardware discovery (GAP-02).
- **Fail-closed default:** Uncalibrated nodes use the conservative UNKNOWN_PROFILE.
- **Identities/permissions:** Inventory edits require a named validator.
- **Limits/timeouts:** n/a
- **Signals:** calibration revision in node policy
- **Restart/recovery:** Inventory is configuration; reloaded at start.
- **Code:** `production/calibration.py`
- **Tests:** `test_c09_*`

## C10 — Multi-sensor aggregation model [P1]

- **Scope:** Worst-case aggregation with per-kind offsets; weighted mode floored at worst sensor; required kinds.
- **Non-goals:** Sensor fusion/ML.
- **Fail-closed default:** Missing required or untrusted sensor -> incomplete -> at least critical.
- **Identities/permissions:** n/a
- **Limits/timeouts:** 64 sensors/node.
- **Signals:** limiting_sensor in explain
- **Restart/recovery:** Stateless.
- **Code:** `production/telemetry.py`
- **Tests:** `test_c10_*`

## C11 — Thermal rate-of-rise predictor [P1]

- **Scope:** Least-squares slope over sliding window; predicted crossing raises band early.
- **Non-goals:** Physical thermal modelling.
- **Fail-closed default:** Predictor can only raise severity, capped at critical (never excludes); implausible slopes ignored.
- **Identities/permissions:** n/a
- **Limits/timeouts:** Window 8 samples, horizon 60 s, |slope| <= 5 C/s.
- **Signals:** prediction_c in explain
- **Restart/recovery:** History rebuilt from fresh samples.
- **Code:** `production/predictive.py`
- **Tests:** `test_c11_*`

## C12 — Battery discharge/remaining-runtime estimator [P1]

- **Scope:** Runtime above reserve from capacity, health, discharge curve and load.
- **Non-goals:** Battery management firmware.
- **Fail-closed default:** Unknown load on battery -> critical.
- **Identities/permissions:** n/a
- **Limits/timeouts:** required_runtime_s configurable.
- **Signals:** gap10_battery_runtime_seconds
- **Restart/recovery:** Stateless.
- **Code:** `production/predictive.py`
- **Tests:** `test_c12_*`

## C13 — Cooling-domain/site correlation [P1]

- **Scope:** Hierarchical domains (rack->room); quorum-hot or hot-inlet raises every member.
- **Non-goals:** Facility BMS integration.
- **Fail-closed default:** Unknown member state counts as critical for quorum.
- **Identities/permissions:** n/a
- **Limits/timeouts:** quorum 0.5.
- **Signals:** reason text in decision
- **Restart/recovery:** Rebuilt from reports.
- **Code:** `production/predictive.py`
- **Tests:** `test_c13_*`

## C14 — Accelerator thermal integration with GAP-11 [P1]

- **Scope:** PK_ACCEL_THERMAL/1 device hotspot/power mapped onto node bands.
- **Non-goals:** Accelerator allocation (GAP-11).
- **Fail-closed default:** Missing/untrusted device telemetry -> critical.
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** reason text
- **Restart/recovery:** Stateless.
- **Code:** `production/predictive.py`
- **Tests:** `test_c14_*`

## C15 — Workload-class-aware shedding policy [P1]

- **Scope:** Deterministic per-class allocation within ceiling; lowest class shed first; protected shares.
- **Non-goals:** Eviction mechanics (scheduler).
- **Fail-closed default:** Exclusion -> every class 0; unknown classes rejected.
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** Stateless.
- **Code:** `production/shedding.py`
- **Tests:** `test_c15_*`

## C16 — Constraint-precedence engine [P1]

- **Scope:** Ordered sources; result is the minimum bound; increase requests never override.
- **Non-goals:** Business policy.
- **Fail-closed default:** Unknown source rejected.
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** precedence_trail in decision
- **Restart/recovery:** Stateless.
- **Code:** `production/shedding.py`, `production/controller.py`
- **Tests:** `test_c16_*`

## C17 — Health/readiness API [P1]

- **Scope:** PK_GAP10_HEALTH/1: live/ready/safe_to_enforce, policy revisions, sample age, dependency and store health.
- **Non-goals:** HTTP serving.
- **Fail-closed default:** safe_to_enforce false unless every check passes.
- **Identities/permissions:** Read-only.
- **Limits/timeouts:** n/a
- **Signals:** gap10_safe_to_enforce
- **Restart/recovery:** Recomputed on each call.
- **Code:** `production/controller.py` · **Artefacts:** `schemas/PK_GAP10_HEALTH-1.schema.json`
- **Tests:** `test_c17_*`

## C18 — Quarantine/freeze/emergency-disable control [P1]

- **Scope:** Signed restrict-only controls with release capability, TTL and audit.
- **Non-goals:** Node lifecycle.
- **Fail-closed default:** Controls only lower bounds; emergency-disable pins a static conservative ceiling.
- **Identities/permissions:** control.operate / control.release.
- **Limits/timeouts:** n/a
- **Signals:** gap10_controls_active; audit control.*
- **Restart/recovery:** Active control ids persisted in node records.
- **Code:** `production/coordination.py`
- **Tests:** `test_c18_*`

## C19 — Structured error taxonomy [P2]

- **Scope:** Stable GAP10-E-XXX-NNN codes, categories, fail-closed flag.
- **Non-goals:** Localisation.
- **Fail-closed default:** Every code is fail-closed.
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** code label on metrics/logs
- **Restart/recovery:** n/a
- **Code:** `production/errors.py` · **Artefacts:** `docs/ERROR_CODES.json`
- **Tests:** `test_c19_*`

## C20 — Tamper-evident audit sink [P2]

- **Scope:** Hash-chained, fsynced JSONL; verify with external head anchor.
- **Non-goals:** WORM storage (ship to external immutable store).
- **Fail-closed default:** Unknown event types rejected.
- **Identities/permissions:** Append-only file access.
- **Limits/timeouts:** fsync per entry.
- **Signals:** audit head
- **Restart/recovery:** Reloaded and verified on start.
- **Code:** `production/observability.py`
- **Tests:** `test_c20_*`

## C21 — Metrics exporter [P2]

- **Scope:** Prometheus text exposition of the METRIC_CATALOG.
- **Non-goals:** HTTP server.
- **Fail-closed default:** Cardinality cap drops new series rather than growing unbounded.
- **Identities/permissions:** Read-only.
- **Limits/timeouts:** MAX_SERIES 100k.
- **Signals:** all gap10_*
- **Restart/recovery:** In-memory.
- **Code:** `production/observability.py`
- **Tests:** `test_c21_*`

## C22 — Structured logging and trace propagation [P2]

- **Scope:** JSONL logs with trace/span ids, W3C traceparent, redaction, pseudonymised workloads.
- **Non-goals:** Log shipping.
- **Fail-closed default:** Sensitive keys redacted; oversized fields truncated.
- **Identities/permissions:** n/a
- **Limits/timeouts:** 512-char fields.
- **Signals:** logs
- **Restart/recovery:** n/a
- **Code:** `production/observability.py`
- **Tests:** `test_c22_*`

## C23 — Operator explain endpoint/UI [P2]

- **Scope:** explain(): decision, source sample, policy, crossings, hysteresis, precedence, controls, downstream status.
- **Non-goals:** UI rendering.
- **Fail-closed default:** No decision -> states consumers must fail closed.
- **Identities/permissions:** Read-only.
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `production/controller.py`
- **Tests:** `test_c23_*`

## C24 — Dashboards and alerts [P2]

- **Scope:** Alert classes separating derating, stale telemetry, cooling, battery, forged input, defects, fleet-wide.
- **Non-goals:** Paging integration.
- **Fail-closed default:** n/a
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** all
- **Restart/recovery:** n/a
- **Code:** `ops/alerts.json`, `ops/dashboard.json` · **Artefacts:** `docs/RUNBOOK.md`
- **Tests:** `test_c24_*`

## C25 — Retry/backoff/circuit-breaker policy [P2]

- **Scope:** Bounded jittered retries with deadline plus circuit breaker; used for the state store.
- **Non-goals:** Transport clients.
- **Fail-closed default:** Exhaustion -> DEPENDENCY_TIMEOUT/CIRCUIT_OPEN -> caller fails closed.
- **Identities/permissions:** n/a
- **Limits/timeouts:** max_attempts, deadline_s.
- **Signals:** gap10_dependency_failures_total
- **Restart/recovery:** Breaker state in memory.
- **Code:** `production/coordination.py`, `production/controller.py`
- **Tests:** `test_c25_*`

## C26 — Partition/reconnect semantics [P2]

- **Scope:** Local authority capped while partitioned; autonomy window; min-reconcile on reconnect.
- **Non-goals:** Network detection.
- **Fail-closed default:** Past autonomy window -> critical fraction.
- **Identities/permissions:** n/a
- **Limits/timeouts:** partition_cap 0.6, max_autonomy_s 900.
- **Signals:** health.partitioned
- **Restart/recovery:** Reconciling set cleared per node on confirm.
- **Code:** `production/coordination.py`
- **Tests:** `test_c26_*`

## C27 — Clock-source/time-service strategy [P2]

- **Scope:** Monotonic-anchored wall time, authenticated sync, jump detection, sync expiry.
- **Non-goals:** NTP/PTP implementation.
- **Fail-closed default:** Untrusted clock -> temperature evidence unusable -> critical.
- **Identities/permissions:** n/a
- **Limits/timeouts:** max_sync_age 300 s, max_jump 2 s.
- **Signals:** health.clock
- **Restart/recovery:** Must resync after restart (untrusted until then).
- **Code:** `production/clock.py`
- **Tests:** `test_c27_*`

## C28 — Secret/key isolation model [P2]

- **Scope:** Capability- and scope-bound keys, rotation overlap, revocation, secret-free inventory.
- **Non-goals:** HSM/KMS; transport encryption (deployment).
- **Fail-closed default:** Unknown/revoked/expired/out-of-scope keys reject.
- **Identities/permissions:** Explicit capabilities only.
- **Limits/timeouts:** >= 32-byte secrets.
- **Signals:** describe()
- **Restart/recovery:** Keys loaded from secret store at start.
- **Code:** `production/keys.py`
- **Tests:** `test_c28_*`

## C29 — End-to-end integration test harness [P3]

- **Scope:** GAP-09 envelope -> GAP-10 -> scheduler/elasticity scenarios.
- **Non-goals:** Real peer binaries.
- **Fail-closed default:** n/a
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `tests/harness.py`, `tests/test_prod_p3.py`
- **Tests:** `test_c29_*`

## C30 — Contract/schema validator tests [P3]

- **Scope:** Fixture and live-output validation; fuzzing telemetry and policy boundaries.
- **Non-goals:** Full JSON-Schema implementation.
- **Fail-closed default:** Unsupported schema keywords raise.
- **Identities/permissions:** n/a
- **Limits/timeouts:** 2000 telemetry + 500 policy fuzz cases.
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `production/schema_validate.py`, `tests/test_prod_p3.py`
- **Tests:** `test_c30_*`

## C31 — Concurrency/race test suite [P3]

- **Scope:** Parallel admission during transition, policy CAS, duplicates, node recreation, concurrent store writes.
- **Non-goals:** Distributed model checking.
- **Fail-closed default:** n/a
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `tests/test_prod_p3.py`
- **Tests:** `test_c31_*`

## C32 — Fault-injection suite [P3]

- **Scope:** Sensor dropout, stuck values, delay, store/scheduler outage, crash/restart, partition.
- **Non-goals:** Chaos tooling.
- **Fail-closed default:** n/a
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `tests/test_prod_p3.py`
- **Tests:** `test_c32_*`

## C33 — Benchmark/soak/fleet-scale harness [P3]

- **Scope:** p50/p95/p99 latency, throughput, CPU, memory, soak growth.
- **Non-goals:** Distributed load.
- **Fail-closed default:** n/a
- **Identities/permissions:** n/a
- **Limits/timeouts:** Budget p99 5 ms, 16 KiB/node.
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `tools/bench.py`
- **Tests:** `test_c33_*`

## C34 — Cross-platform/hardware compatibility matrix [P3]

- **Scope:** Machine-readable support status per runtime/arch/OS/peer schema/scheduler.
- **Non-goals:** n/a
- **Fail-closed default:** Anything unverified is marked unverified, never supported.
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `ops/compatibility_matrix.json`
- **Tests:** `test_c34_*`

## C35 — SBOM, dependency pinning, and vulnerability policy [P3]

- **Scope:** CycloneDX SBOM; stdlib-only pin; CVE SLA; EOL policy; undeclared-import test.
- **Non-goals:** Registry scanning.
- **Fail-closed default:** Undeclared import fails the build.
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `SBOM.cdx.json`, `docs/DEPENDENCY_POLICY.md`
- **Tests:** `test_c35_*`

## C36 — Artifact signing/provenance and reproducible release build [P3]

- **Scope:** Deterministic ZIP, digest manifest, signed provenance, verify().
- **Non-goals:** Sigstore integration.
- **Fail-closed default:** Tampered artifact fails verify.
- **Identities/permissions:** release.sign.
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `tools/build_release.py`
- **Tests:** `test_c36_*`

## C37 — Canary/staged rollout controller [P3]

- **Scope:** Cohorts by site x hardware class, soak, guards, automatic rollback, audit.
- **Non-goals:** Code deployment tooling.
- **Fail-closed default:** Guard failure -> staged revision withdrawn, active unchanged.
- **Identities/permissions:** policy activation rights.
- **Limits/timeouts:** stages 1/5/25/100%, soak 600 s.
- **Signals:** audit rollout.*
- **Restart/recovery:** Restart resumes from PolicyService state.
- **Code:** `production/rollout.py`
- **Tests:** `test_c37_*`

## C38 — Backup/restore/reconstruction runbook [P3]

- **Scope:** Digest-verified backup/restore; safe ownership recovery; no reopen before fresh telemetry.
- **Non-goals:** Offsite storage.
- **Fail-closed default:** Digest mismatch / unsafe archive member rejects restore.
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** audit state.restored
- **Restart/recovery:** Restored nodes resume >= critical.
- **Code:** `production/store.py`, `docs/RUNBOOK.md`
- **Tests:** `test_c38_*`

## C39 — Incident severity/paging/escalation definitions [P3]

- **Scope:** SEV1-4 definitions mapped to alert classes, paging and escalation.
- **Non-goals:** Paging tool config.
- **Fail-closed default:** n/a
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `docs/INCIDENT_SEVERITY.md`
- **Tests:** `test_c39_*`

## C40 — Architecture decision record and exception register [P3]

- **Scope:** ADRs for scope/trust, fail-closed, fencing, signing, precedence; exception register.
- **Non-goals:** n/a
- **Fail-closed default:** Exceptions must be owned and time-bounded.
- **Identities/permissions:** n/a
- **Limits/timeouts:** n/a
- **Signals:** n/a
- **Restart/recovery:** n/a
- **Code:** `docs/ADR.md`, `docs/EXCEPTION_REGISTER.md`
- **Tests:** `test_c40_*`
