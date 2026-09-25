"""Single source of truth for the 40 v4.3.0 components: design record fields
used to render docs/COMPONENTS.md and to drive the evidence matrix."""

# id: (name, priority, modules, test-tag, scope, non_goals, fail_closed_default, identities/permissions,
#      limits/timeouts, signals, restart/recovery, docs)
C = {}


def c(i, name, pri, modules, scope, non_goals, fail_closed, perms, limits, signals, restart, docs=()):
    C[i] = dict(id=i, name=name, priority=pri, modules=list(modules), scope=scope, non_goals=non_goals,
                fail_closed=fail_closed, permissions=perms, limits=limits, signals=signals, restart=restart,
                docs=list(docs), test_tag=f"c{i:02d}")


c(1, "Authenticated telemetry adapter for GAP-09", "P0", ["production/telemetry.py", "production/keys.py"],
  "Verify, authorize, freshness-check and normalise PK_TELEMETRY_ENVELOPE/1 into CanonicalSample with provenance.",
  "Sensor attestation itself (GAP-09); transport.",
  "Any verification/parse/freshness failure rejects the sample with a GAP10-E-TEL code; node keeps its prior (or constrained) band.",
  "Reporter key needs capability telemetry.publish scoped to its node glob.",
  "64 KiB envelope, 64 sensors, 30 s max age, 5 s future skew, per-(identity,node) monotonic seq.",
  "gap10_telemetry_samples_total{outcome}, adapter.health()", "Last accepted seq persisted in node state; replay below it rejected after restart.",
  ["schemas/PK_TELEMETRY_ENVELOPE-1.schema.json", "fixtures/telemetry_envelope_*.json"])
c(2, "Downstream scheduler enforcement adapter", "P0", ["production/enforcement.py"],
  "Turn PK_POWER_CEILING/1 into a hard admission/placement limit with decision binding, TOCTOU revalidation, drain, divergence alarm.",
  "Placement scoring; real SCH-01 code (must implement SchedulerBackend).",
  "No limit applied -> limit 0; decision missing/stale -> FailClosedContract.absent_fraction (default 0).",
  "Adapter holds only scheduler set_limit/commit/drain rights.", "Admission serialised under adapter lock; floor rounding.",
  "gap10_enforcement_divergence{consumer=scheduler}", "Limits re-applied from current decisions on apply().")
c(3, "Elasticity-plane enforcement adapter", "P0", ["production/enforcement.py"],
  "Propagate pool-level sum of node ceilings as a hard scale cap with refill cooldown.", "Autoscaling policy itself (PLN-05).",
  "Missing decisions count as 0 capacity; cap raises held for refill_cooldown_s.", "Adapter holds only set_cap on PLN-05.",
  "Cooldown default 120 s.", "cap per pool (backend)", "Cap recomputed from view each apply().")
c(4, "Durable per-node state store", "P0", ["production/store.py"],
  "Atomic, checksummed, fenced per-node persistence of band, hysteresis band, last trusted sample/seq, policy revision, controls.",
  "Fleet inventory; multi-site replication (use an external linearizable store in production).",
  "Corrupt/missing record -> node starts critical; store outage -> decisions capped at critical and health unsafe.",
  "Filesystem write access to the state directory only.", "One document per node; retries bounded by store_retry/breaker.",
  "gap10_dependency_failures_total{dependency=state-store}", "Restart resumes max(persisted band, critical).")
c(5, "Atomic policy distribution and activation service", "P0", ["production/policy_service.py"],
  "Content-addressed immutable revisions, compare-and-swap activation, staged cohorts, rollback, provenance.",
  "Policy authoring UI; cross-scope inheritance.", "Invalid/unsigned/conflicting revisions are never activated; active revision unchanged.",
  "policy.author per scope glob.", "Single lock per service; history stack per scope.", "audit policy.* events",
  "In-memory in this package; production must back it with the same durable store (see ADR-0003).")
c(6, "Policy authorization/signature verification", "P0", ["production/policy_service.py", "production/keys.py"],
  "Signature on canonical bundle; two-person rule for any relaxation of safety limits.", "Key custody (HSM).",
  "Bad/unknown signature -> POLICY_UNSIGNED; relaxation without distinct approver -> POLICY_UNAUTHORIZED; audited as security.failure.",
  "policy.author + distinct policy.approve-relax identity.", "n/a", "audit policy.rejected / security.failure", "Stateless verification.")
c(7, "Explicit fail-closed scheduler behavior when GAP-10 is absent/unhealthy", "P0", ["production/enforcement.py"],
  "Consumer-side CeilingView: never interprets absence/staleness/unhealth as capacity.", "GAP-10 availability itself.",
  "absent_fraction (<= critical, default 0) and min with last decision.", "Consumer read-only.", "max_decision_age_s default 15 s.",
  "effective()['fail_closed']", "Empty view after consumer restart -> admits nothing.")
c(8, "Controller ownership/leader fencing", "P0", ["production/coordination.py", "production/controller.py", "production/store.py", "production/enforcement.py"],
  "Per-shard lease with monotonically increasing fencing token checked by controller, store and consumers.",
  "Consensus implementation (production uses etcd/consul/DB CAS behind LeaseManager).",
  "No valid lease -> controller refuses to decide; stale token rejected by store and CeilingView.",
  "controller.lead.", "Lease TTL default 10 s (harness 30 s); renewed on each decision.", "audit ownership.*", "New leader gets a strictly greater token.")
c(9, "Hardware/site calibration inventory", "P1", ["production/calibration.py"],
  "Validated per-hardware-class limits; derived policy always below vendor throttle.", "Hardware discovery (GAP-02).",
  "Uncalibrated nodes use the conservative UNKNOWN_PROFILE.", "Inventory edits require a named validator.", "n/a",
  "calibration revision in node policy", "Inventory is configuration; reloaded at start.")
c(10, "Multi-sensor aggregation model", "P1", ["production/telemetry.py"],
  "Worst-case aggregation with per-kind offsets; weighted mode floored at worst sensor; required kinds.", "Sensor fusion/ML.",
  "Missing required or untrusted sensor -> incomplete -> at least critical.", "n/a", "64 sensors/node.", "limiting_sensor in explain", "Stateless.")
c(11, "Thermal rate-of-rise predictor", "P1", ["production/predictive.py"],
  "Least-squares slope over sliding window; predicted crossing raises band early.", "Physical thermal modelling.",
  "Predictor can only raise severity, capped at critical (never excludes); implausible slopes ignored.", "n/a",
  "Window 8 samples, horizon 60 s, |slope| <= 5 C/s.", "prediction_c in explain", "History rebuilt from fresh samples.")
c(12, "Battery discharge/remaining-runtime estimator", "P1", ["production/predictive.py"],
  "Runtime above reserve from capacity, health, discharge curve and load.", "Battery management firmware.",
  "Unknown load on battery -> critical.", "n/a", "required_runtime_s configurable.", "gap10_battery_runtime_seconds", "Stateless.")
c(13, "Cooling-domain/site correlation", "P1", ["production/predictive.py"],
  "Hierarchical domains (rack->room); quorum-hot or hot-inlet raises every member.", "Facility BMS integration.",
  "Unknown member state counts as critical for quorum.", "n/a", "quorum 0.5.", "reason text in decision", "Rebuilt from reports.")
c(14, "Accelerator thermal integration with GAP-11", "P1", ["production/predictive.py"],
  "PK_ACCEL_THERMAL/1 device hotspot/power mapped onto node bands.", "Accelerator allocation (GAP-11).",
  "Missing/untrusted device telemetry -> critical.", "n/a", "n/a", "reason text", "Stateless.")
c(15, "Workload-class-aware shedding policy", "P1", ["production/shedding.py"],
  "Deterministic per-class allocation within ceiling; lowest class shed first; protected shares.", "Eviction mechanics (scheduler).",
  "Exclusion -> every class 0; unknown classes rejected.", "n/a", "n/a", "n/a", "Stateless.")
c(16, "Constraint-precedence engine", "P1", ["production/shedding.py", "production/controller.py"],
  "Ordered sources; result is the minimum bound; increase requests never override.", "Business policy.",
  "Unknown source rejected.", "n/a", "n/a", "precedence_trail in decision", "Stateless.")
c(17, "Health/readiness API", "P1", ["production/controller.py"],
  "PK_GAP10_HEALTH/1: live/ready/safe_to_enforce, policy revisions, sample age, dependency and store health.", "HTTP serving.",
  "safe_to_enforce false unless every check passes.", "Read-only.", "n/a", "gap10_safe_to_enforce", "Recomputed on each call.",
  ["schemas/PK_GAP10_HEALTH-1.schema.json"])
c(18, "Quarantine/freeze/emergency-disable control", "P1", ["production/coordination.py"],
  "Signed restrict-only controls with release capability, TTL and audit.", "Node lifecycle.",
  "Controls only lower bounds; emergency-disable pins a static conservative ceiling.", "control.operate / control.release.",
  "n/a", "gap10_controls_active; audit control.*", "Active control ids persisted in node records.")
c(19, "Structured error taxonomy", "P2", ["production/errors.py"], "Stable GAP10-E-XXX-NNN codes, categories, fail-closed flag.",
  "Localisation.", "Every code is fail-closed.", "n/a", "n/a", "code label on metrics/logs", "n/a", ["docs/ERROR_CODES.json"])
c(20, "Tamper-evident audit sink", "P2", ["production/observability.py"], "Hash-chained, fsynced JSONL; verify with external head anchor.",
  "WORM storage (ship to external immutable store).", "Unknown event types rejected.", "Append-only file access.", "fsync per entry.",
  "audit head", "Reloaded and verified on start.")
c(21, "Metrics exporter", "P2", ["production/observability.py"], "Prometheus text exposition of the METRIC_CATALOG.", "HTTP server.",
  "Cardinality cap drops new series rather than growing unbounded.", "Read-only.", "MAX_SERIES 100k.", "all gap10_*", "In-memory.")
c(22, "Structured logging and trace propagation", "P2", ["production/observability.py"], "JSONL logs with trace/span ids, W3C traceparent, redaction, pseudonymised workloads.",
  "Log shipping.", "Sensitive keys redacted; oversized fields truncated.", "n/a", "512-char fields.", "logs", "n/a")
c(23, "Operator explain endpoint/UI", "P2", ["production/controller.py"], "explain(): decision, source sample, policy, crossings, hysteresis, precedence, controls, downstream status.",
  "UI rendering.", "No decision -> states consumers must fail closed.", "Read-only.", "n/a", "n/a", "n/a")
c(24, "Dashboards and alerts", "P2", ["ops/alerts.json", "ops/dashboard.json"], "Alert classes separating derating, stale telemetry, cooling, battery, forged input, defects, fleet-wide.",
  "Paging integration.", "n/a", "n/a", "n/a", "all", "n/a", ["docs/RUNBOOK.md"])
c(25, "Retry/backoff/circuit-breaker policy", "P2", ["production/coordination.py", "production/controller.py"], "Bounded jittered retries with deadline plus circuit breaker; used for the state store.",
  "Transport clients.", "Exhaustion -> DEPENDENCY_TIMEOUT/CIRCUIT_OPEN -> caller fails closed.", "n/a", "max_attempts, deadline_s.", "gap10_dependency_failures_total", "Breaker state in memory.")
c(26, "Partition/reconnect semantics", "P2", ["production/coordination.py"], "Local authority capped while partitioned; autonomy window; min-reconcile on reconnect.",
  "Network detection.", "Past autonomy window -> critical fraction.", "n/a", "partition_cap 0.6, max_autonomy_s 900.", "health.partitioned", "Reconciling set cleared per node on confirm.")
c(27, "Clock-source/time-service strategy", "P2", ["production/clock.py"], "Monotonic-anchored wall time, authenticated sync, jump detection, sync expiry.",
  "NTP/PTP implementation.", "Untrusted clock -> temperature evidence unusable -> critical.", "n/a", "max_sync_age 300 s, max_jump 2 s.", "health.clock", "Must resync after restart (untrusted until then).")
c(28, "Secret/key isolation model", "P2", ["production/keys.py"], "Capability- and scope-bound keys, rotation overlap, revocation, secret-free inventory.",
  "HSM/KMS; transport encryption (deployment).", "Unknown/revoked/expired/out-of-scope keys reject.", "Explicit capabilities only.", ">= 32-byte secrets.", "describe()", "Keys loaded from secret store at start.")
c(29, "End-to-end integration test harness", "P3", ["tests/harness.py", "tests/test_prod_p3.py"], "GAP-09 envelope -> GAP-10 -> scheduler/elasticity scenarios.",
  "Real peer binaries.", "n/a", "n/a", "n/a", "n/a", "n/a")
c(30, "Contract/schema validator tests", "P3", ["production/schema_validate.py", "tests/test_prod_p3.py"], "Fixture and live-output validation; fuzzing telemetry and policy boundaries.",
  "Full JSON-Schema implementation.", "Unsupported schema keywords raise.", "n/a", "2000 telemetry + 500 policy fuzz cases.", "n/a", "n/a")
c(31, "Concurrency/race test suite", "P3", ["tests/test_prod_p3.py"], "Parallel admission during transition, policy CAS, duplicates, node recreation, concurrent store writes.",
  "Distributed model checking.", "n/a", "n/a", "n/a", "n/a", "n/a")
c(32, "Fault-injection suite", "P3", ["tests/test_prod_p3.py"], "Sensor dropout, stuck values, delay, store/scheduler outage, crash/restart, partition.",
  "Chaos tooling.", "n/a", "n/a", "n/a", "n/a", "n/a")
c(33, "Benchmark/soak/fleet-scale harness", "P3", ["tools/bench.py"], "p50/p95/p99 latency, throughput, CPU, memory, soak growth.", "Distributed load.",
  "n/a", "n/a", "Budget p99 5 ms, 16 KiB/node.", "n/a", "n/a")
c(34, "Cross-platform/hardware compatibility matrix", "P3", ["ops/compatibility_matrix.json"], "Machine-readable support status per runtime/arch/OS/peer schema/scheduler.",
  "n/a", "Anything unverified is marked unverified, never supported.", "n/a", "n/a", "n/a", "n/a")
c(35, "SBOM, dependency pinning, and vulnerability policy", "P3", ["SBOM.cdx.json", "docs/DEPENDENCY_POLICY.md"], "CycloneDX SBOM; stdlib-only pin; CVE SLA; EOL policy; undeclared-import test.",
  "Registry scanning.", "Undeclared import fails the build.", "n/a", "n/a", "n/a", "n/a")
c(36, "Artifact signing/provenance and reproducible release build", "P3", ["tools/build_release.py"], "Deterministic ZIP, digest manifest, signed provenance, verify().",
  "Sigstore integration.", "Tampered artifact fails verify.", "release.sign.", "n/a", "n/a", "n/a")
c(37, "Canary/staged rollout controller", "P3", ["production/rollout.py"], "Cohorts by site x hardware class, soak, guards, automatic rollback, audit.",
  "Code deployment tooling.", "Guard failure -> staged revision withdrawn, active unchanged.", "policy activation rights.", "stages 1/5/25/100%, soak 600 s.", "audit rollout.*", "Restart resumes from PolicyService state.")
c(38, "Backup/restore/reconstruction runbook", "P3", ["production/store.py", "docs/RUNBOOK.md"], "Digest-verified backup/restore; safe ownership recovery; no reopen before fresh telemetry.",
  "Offsite storage.", "Digest mismatch / unsafe archive member rejects restore.", "n/a", "n/a", "audit state.restored", "Restored nodes resume >= critical.")
c(39, "Incident severity/paging/escalation definitions", "P3", ["docs/INCIDENT_SEVERITY.md"], "SEV1-4 definitions mapped to alert classes, paging and escalation.",
  "Paging tool config.", "n/a", "n/a", "n/a", "n/a", "n/a")
c(40, "Architecture decision record and exception register", "P3", ["docs/ADR.md", "docs/EXCEPTION_REGISTER.md"], "ADRs for scope/trust, fail-closed, fencing, signing, precedence; exception register.",
  "n/a", "Exceptions must be owned and time-bounded.", "n/a", "n/a", "n/a", "n/a")
