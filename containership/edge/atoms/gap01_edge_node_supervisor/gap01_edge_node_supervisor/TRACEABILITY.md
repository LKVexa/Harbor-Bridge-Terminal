# GAP-01 Requirements Traceability Matrix (v5.0.0)

**Summary:** 75 met · 20 partial · 5 exception (of 100). Owner for every row: unassigned (EXC-001).

| ID | Dimension | Status | Implementation | Evidence | Exception / gap |
|---|---|---|---|---|---|
| GAP-01-C001 | Architecture & Scope | met | README.md; docs/ARCHITECTURE_DECISIONS.md#ADR-0001 | docs review |  |
| GAP-01-C002 | Architecture & Scope | met | README.md Owns/Does-not-own; ADR-0001 table | docs review |  |
| GAP-01-C003 | Architecture & Scope | met | ADR-0001 (scheduler, execution plane, GAP-02, control plane, reporters) | docs review |  |
| GAP-01-C004 | Architecture & Scope | met | store.py (persisted intent) + runtime.observed() reconciled in controller.start | tests/test_controller.py::ReconciliationTest |  |
| GAP-01-C005 | Architecture & Scope | met | ADR-0005/0006; PLATFORMS_AND_COMPATIBILITY.md | docs review |  |
| GAP-01-C006 | Architecture & Scope | partial | trust classes; per-caller buckets; CAPACITY.md#Fairness | tests/test_controller.py::DrainTest | tenant boundaries delegated to scheduler (ADR-0001) |
| GAP-01-C007 | Architecture & Scope | met | REQUIREMENTS.md (SHALL vs MAY); optional pk_core, optional signals | docs review |  |
| GAP-01-C008 | Architecture & Scope | met | README Non-goals; PLATFORMS unsupported rows | docs review |  |
| GAP-01-C009 | Architecture & Scope | exception | OWNERS.md | - | EXC-001 |
| GAP-01-C010 | Architecture & Scope | partial | docs/ARCHITECTURE_DECISIONS.md | docs review | EXC-001 (approval) |
| GAP-01-C011 | Requirements & Semantics | partial | bootstrap.py, inventory.py, runtime.py | tests/test_bootstrap_inventory.py | EXC-004 (wasm/microVM/unikernel) |
| GAP-01-C012 | Requirements & Semantics | met | REQUIREMENTS.md#Environments; CAPACITY.md profiles | docs review |  |
| GAP-01-C013 | Requirements & Semantics | met | REQUIREMENTS.md; CAPACITY.md thresholds; tools/perf_gate.py | evidence/bench.json |  |
| GAP-01-C014 | Requirements & Semantics | met | REQUIREMENTS.md#Failure-semantics; errors.ERROR_CATALOG | tests/test_production.py::ErrorModelTest |  |
| GAP-01-C015 | Requirements & Semantics | met | supervisor.TRANSITIONS; controller._transition | tests/test_controller.py::PropertyTest |  |
| GAP-01-C016 | Requirements & Semantics | met | schemas/*.schema.json; store.migrate; PLATFORMS_AND_COMPATIBILITY.md | examples/fixtures/compat_* |  |
| GAP-01-C017 | Requirements & Semantics | met | config.SCHEMA; CAPACITY.md | tests/test_controller.py::test_capacity, test_rate_limit |  |
| GAP-01-C018 | Requirements & Semantics | met | controller partition machine; PARTITION_ALLOWED | tests/test_controller.py::test_partition_state_machine |  |
| GAP-01-C019 | Requirements & Semantics | met | REQUIREMENTS.md#Precedence | tests/test_controller.py::test_persistence_failure_enters_emergency |  |
| GAP-01-C020 | Requirements & Semantics | met | TRACEABILITY.json (this file) | tools/traceability.py |  |
| GAP-01-C021 | Interfaces & Integration | met | control socket, probes, state files, runtime adapter, sd_notify: README Interfaces + ADR-0003 | docs review |  |
| GAP-01-C022 | Interfaces & Integration | met | schemas/*.schema.json; schema_validator.py | tests/test_bootstrap_inventory.py::SchemaFixtureTest |  |
| GAP-01-C023 | Interfaces & Integration | met | security.Authenticator; socket 0600 | tests/test_controller.py::test_authn_replay_skew; tests/test_integration.py::test_socket_permissions |  |
| GAP-01-C024 | Interfaces & Integration | met | security.AuthorizationPolicy; OP_CAPABILITY | tests/test_controller.py::test_authz_denied_is_audited |  |
| GAP-01-C025 | Interfaces & Integration | met | request_id idempotency; RateLimiter; drain deadlines; REQUIREMENTS.md | tests/test_controller.py::test_idempotent_request_id |  |
| GAP-01-C026 | Interfaces & Integration | met | errors.py; gap01_error_1.schema.json | tests/test_production.py::ErrorModelTest |  |
| GAP-01-C027 | Interfaces & Integration | met | PLATFORMS_AND_COMPATIBILITY.md#Version-compatibility | examples/fixtures/compat_* |  |
| GAP-01-C028 | Interfaces & Integration | met | CAPACITY.md ceilings; systemd limits | tests/test_controller.py::test_oversized, test_capacity |  |
| GAP-01-C029 | Interfaces & Integration | met | examples/sequences/*.json; examples/fixtures/*.json | SchemaFixtureTest |  |
| GAP-01-C030 | Interfaces & Integration | partial | server.py + ProcessAdapter | tests/test_integration.py | EXC-014 (live control plane) |
| GAP-01-C031 | Implementation & Configuration | met | pyproject.toml; requirements*.txt; sbom.cdx.json | RELEASE_MANIFEST.json |  |
| GAP-01-C032 | Implementation & Configuration | met | package (immutable) vs /etc/gap01 (config) vs /var/lib/gap01 (state) | deploy/systemd |  |
| GAP-01-C033 | Implementation & Configuration | met | config.SupervisorConfig defaults | tests/test_production.py::ConfigTest |  |
| GAP-01-C034 | Implementation & Configuration | met | config.validate_knob; load_config signature | tests/test_production.py::ConfigTest |  |
| GAP-01-C035 | Implementation & Configuration | met | config file + signals file per site; profiles | CAPACITY.md |  |
| GAP-01-C036 | Implementation & Configuration | partial | config.provenance (source, sha256, signed); audit of reload_config | tests/test_production.py::test_signed_config | author identity = signer key only |
| GAP-01-C037 | Implementation & Configuration | met | frozen config; hot_reload whole-or-nothing; atomic_write | tests/test_controller.py::test_config_hot_reload |  |
| GAP-01-C038 | Implementation & Configuration | partial | RUNBOOKS Day-1 rollback, RB-12; migration forward-only | docs review | EXC-015 |
| GAP-01-C039 | Implementation & Configuration | met | config.SecretBoundary; observability.redact | tests/test_production.py::test_secret_boundary, test_redaction |  |
| GAP-01-C040 | Implementation & Configuration | met | bootstrap.run_phases; RUNBOOKS Day 0 | tests/test_bootstrap_inventory.py::BootstrapTest |  |
| GAP-01-C041 | Security, Trust & Isolation | met | docs/THREAT_MODEL.md | threat table test column |  |
| GAP-01-C042 | Security, Trust & Isolation | partial | roles/capabilities; systemd sandbox | tests/test_controller.py::test_authz_denied_is_audited | EXC-005 |
| GAP-01-C043 | Security, Trust & Isolation | partial | systemd ProtectSystem/PrivateDevices/IPAddressDeny | deploy/systemd | EXC-005 |
| GAP-01-C044 | Security, Trust & Isolation | partial | caller HMAC auth; config/artifact signatures; software node attestation | tests/test_production.py::SecurityTest | EXC-002 |
| GAP-01-C045 | Security, Trust & Isolation | met | security.verify_artifacts; RELEASE_MANIFEST.json | tests/test_production.py::test_artifact_verification |  |
| GAP-01-C046 | Security, Trust & Isolation | partial | reclaim proof; process groups | tests/test_controller.py::test_unproven_reclaim_never_stops_node | enforcement delegated to execution plane (ADR-0001); EXC-004 |
| GAP-01-C047 | Security, Trust & Isolation | exception | UNIX socket local-only; state has no secrets | - | EXC-003, EXC-007 |
| GAP-01-C048 | Security, Trust & Isolation | met | fail-closed: no keys -> boot recovery mode; stale time rejected; partition -> emergency | tests/test_bootstrap_inventory.py::test_bad_caller_key_permissions_enter_recovery_mode |  |
| GAP-01-C049 | Security, Trust & Isolation | met | store.AuditLog hash chain | tests/test_production.py::test_audit_chain_detects_tamper |  |
| GAP-01-C050 | Security, Trust & Isolation | partial | replay, spoofing, injection, escalation tests | tests/test_controller.py; tests/test_production.py | EXC-012 (independent review) |
| GAP-01-C051 | Resilience & Failure Handling | met | THREAT_MODEL + ADR-0005 degraded modes | docs review |  |
| GAP-01-C052 | Resilience & Failure Handling | met | Watchdog; liveness; health staleness | tests/test_controller.py::test_readiness_liveness_watchdog |  |
| GAP-01-C053 | Resilience & Failure Handling | met | bootstrap retry with exponential backoff; callers retry with request_id | tests/test_bootstrap_inventory.py |  |
| GAP-01-C054 | Resilience & Failure Handling | met | RateLimiter; pressure blocks admission | tests/test_controller.py::test_pressure_blocks_admission |  |
| GAP-01-C055 | Resilience & Failure Handling | met | no failover by design: single local authority; restart -> cordoned | tests/test_controller.py::ReconciliationTest |  |
| GAP-01-C056 | Resilience & Failure Handling | met | partitioned mode; optional health signals quorum | tests/test_production.py::HealthTest |  |
| GAP-01-C057 | Resilience & Failure Handling | met | WAL + checkpoint + replay | tests/test_controller.py::test_wal_replay_after_crash_before_checkpoint; tests/test_integration.py::ProcessChaosTest |  |
| GAP-01-C058 | Resilience & Failure Handling | met | RLock serialization; generations; duplicate-admission refusal; orphan termination | tests/test_controller.py::ConcurrencyTest |  |
| GAP-01-C059 | Resilience & Failure Handling | met | emergency mode; DISABLED flag; cordon | tests/test_controller.py::test_emergency_mode, test_emergency_disable_persists |  |
| GAP-01-C060 | Resilience & Failure Handling | met | chaos tests: SIGKILL, torn writes, ENOSPC, corrupt state, clock regression | tests/test_integration.py::ProcessChaosTest; tests/test_production.py::StoreTest |  |
| GAP-01-C061 | Performance & Resource Efficiency | met | tools/bench.py | evidence/bench.json |  |
| GAP-01-C062 | Performance & Resource Efficiency | met | CAPACITY.md; tools/perf_gate.py | evidence/bench.json |  |
| GAP-01-C063 | Performance & Resource Efficiency | partial | bench + soak (steady, burst churn, restart) | evidence/soak.json | EXC-014 (scale-out on real fleet) |
| GAP-01-C064 | Performance & Resource Efficiency | partial | per-workload drain/admit cost | evidence/bench.json | per-tenant overhead not measured |
| GAP-01-C065 | Performance & Resource Efficiency | met | non-blocking drain signalling (fixed in v5); single lock | CHANGELOG 5.0.0 |  |
| GAP-01-C066 | Performance & Resource Efficiency | met | local UNIX IPC; in-memory aggregation; not applicable beyond | ADR-0003 |  |
| GAP-01-C067 | Performance & Resource Efficiency | met | bounded rings, windows, queue, sizes | CAPACITY.md; evidence/soak.json |  |
| GAP-01-C068 | Performance & Resource Efficiency | exception | - | - | EXC-008 |
| GAP-01-C069 | Performance & Resource Efficiency | met | CAPACITY.md saturation signals | docs review |  |
| GAP-01-C070 | Performance & Resource Efficiency | met | tools/perf_gate.py in CI release job | .github/workflows/ci.yml |  |
| GAP-01-C071 | Observability & Explainability | met | /livez /readyz /metrics; status; diagnostics (config, version) | tests/test_integration.py::test_full_lifecycle_with_real_processes |  |
| GAP-01-C072 | Observability & Explainability | met | observability.Metrics | tests/test_production.py::test_metrics_low_cardinality |  |
| GAP-01-C073 | Observability & Explainability | met | JSON logs with event_id, request_id, trace_id | docs/OBSERVABILITY.md |  |
| GAP-01-C074 | Observability & Explainability | partial | Tracer traceparent; trace_id in audit | tests/test_production.py::test_trace_propagation | EXC-013 (exporter) |
| GAP-01-C075 | Observability & Explainability | met | diagnostics redacted | tests/test_production.py::test_redaction |  |
| GAP-01-C076 | Observability & Explainability | met | last_reason; audit per decision; drain escalation text | tests/test_controller.py::test_audit_chain_intact_after_run |  |
| GAP-01-C077 | Observability & Explainability | met | diagnostics explain bundle | docs/OBSERVABILITY.md |  |
| GAP-01-C078 | Observability & Explainability | partial | version + boot attestation in diagnostics | boot_attestation.json | release-lineage/infra-graph link needs control plane |
| GAP-01-C079 | Observability & Explainability | met | OBSERVABILITY.md retention/privacy | docs review |  |
| GAP-01-C080 | Observability & Explainability | partial | deploy/prometheus/gap01-alerts.yml | docs review | EXC-013 (dashboards) |
| GAP-01-C081 | Testing & Certification | met | unit tests | tests/test_supervisor.py; tests/test_production.py |  |
| GAP-01-C082 | Testing & Certification | met | schema fixtures + status/drain/health validation | SchemaFixtureTest; test_status_matches_schema |  |
| GAP-01-C083 | Testing & Certification | partial | process-runtime integration | tests/test_integration.py | EXC-004, EXC-014 |
| GAP-01-C084 | Testing & Certification | exception | CI matrix defined | .github/workflows/ci.yml | EXC-009 |
| GAP-01-C085 | Testing & Certification | met | FuzzTest (500 random inputs) | tests/test_controller.py::FuzzTest |  |
| GAP-01-C086 | Testing & Certification | met | ConcurrencyTest | tests/test_controller.py::ConcurrencyTest |  |
| GAP-01-C087 | Testing & Certification | met | THREAT_MODEL test column | tests |  |
| GAP-01-C088 | Testing & Certification | met | bench, soak, burst churn | evidence/*.json |  |
| GAP-01-C089 | Testing & Certification | met | partition, reconnect, restart tests | tests/test_controller.py::SafetyModesTest |  |
| GAP-01-C090 | Testing & Certification | met | tools/evidence.py -> evidence/evidence.json | evidence/evidence.json |  |
| GAP-01-C091 | Operations, Release & Governance | partial | SLOTracker; SUPPORT.md | tests/test_controller.py::PropertyTest (SLO violations = 0) | support commitments need owner (EXC-001) |
| GAP-01-C092 | Operations, Release & Governance | partial | RUNBOOKS Day-1, RB-13 | tests/test_controller.py::test_emergency_disable_persists | EXC-015 |
| GAP-01-C093 | Operations, Release & Governance | met | PLATFORMS_AND_COMPATIBILITY.md | docs review |  |
| GAP-01-C094 | Operations, Release & Governance | met | SECURITY.md; SUPPORT.md | docs review |  |
| GAP-01-C095 | Operations, Release & Governance | met | StateStore.backup/restore; migrate | tests/test_production.py::test_backup_restore, test_migration |  |
| GAP-01-C096 | Operations, Release & Governance | met | RUNBOOKS Day 0/1/2 | docs review |  |
| GAP-01-C097 | Operations, Release & Governance | met | RUNBOOKS incident severity | docs review |  |
| GAP-01-C098 | Operations, Release & Governance | exception | - | - | EXC-001 (recurring reviews need owners) |
| GAP-01-C099 | Operations, Release & Governance | met | EXCEPTIONS.md | docs review |  |
| GAP-01-C100 | Operations, Release & Governance | partial | tools/exit_gate.py | evidence/exit_gate.json | gate returns NO_GO/CONDITIONAL until blockers close |
