# PLN-05 requirements traceability matrix (4.2.0)

Generated from `traceability/requirements.json` by `tools/traceability.py --write`; do not edit by hand.

| ID | Status | Implementation | Verification | Note |
|---|---|---|---|---|
| PLN-05-C001 | verified | spec.py::RESPONSIBILITY | tests/test_repo.py::RepoTest.test_scope_has_no_drift |  |
| PLN-05-C002 | verified | spec.py::OWNS<br>spec.py::NOT_OWNS | tests/test_repo.py::RepoTest.test_scope_has_no_drift |  |
| PLN-05-C003 | verified | spec.py::DEPENDENCIES | tests/test_repo.py::RepoTest.test_scope_has_no_drift |  |
| PLN-05-C004 | verified | spec.py::SOURCE_OF_TRUTH<br>spec.py::SOURCE_PRECEDENCE | tests/test_repo.py::RepoTest.test_scope_has_no_drift |  |
| PLN-05-C005 | verified | spec.py::ASSUMPTIONS<br>spec/pln05_semantics.md | tests/test_repo.py::RepoTest.test_required_documents_present |  |
| PLN-05-C006 | verified | spec.py::BOUNDARIES<br>security/isolation-model.md | tests/security/test_adversarial.py::Adversarial.test_T06_cross_tenant_and_site |  |
| PLN-05-C007 | verified | spec.py::MANDATORY<br>spec.py::OPTIONAL | tests/test_repo.py::RepoTest.test_scope_has_no_drift |  |
| PLN-05-C008 | verified | spec.py::NON_GOALS<br>spec/pln05_semantics.md | tests/test_repo.py::RepoTest.test_scope_has_no_drift |  |
| PLN-05-C009 | governance-pending | ops/oncall.json<br>CODEOWNERS | tests/test_repo.py::RepoTest.test_governance_files_present | roles defined; every assignee UNASSIGNED pending owner |
| PLN-05-C010 | governance-pending | docs/adr/ADR-0001-pln05-authoritative-scope.md | tests/test_repo.py::RepoTest.test_scope_has_no_drift | ADR status PROPOSED; needs architecture-owner approval |
| PLN-05-C011 | governance-pending | spec/pln05_semantics.md<br>docs/adr/ADR-0001-pln05-authoritative-scope.md | tests/test_repo.py::RepoTest.test_scope_has_no_drift | SHALL spec written for the capacity-control function; snapshot/microfunction/reassignment attributed to siblings pending ADR approval |
| PLN-05-C012 | implemented | spec/pln05_semantics.md<br>config/schema.json | tests/test_units.py::ConfigTest.test_defaults_valid_and_precedence | context profiles are configuration overlays; no per-context behavioural test beyond overlays |
| PLN-05-C013 | verified | spec/pln05_nfr.json<br>benchmarks/thresholds.json | ci/performance_gate.py<br>tests/scale/test_soak.py::Soak.test_soak_no_unbounded_growth_or_drift |  |
| PLN-05-C014 | verified | schemas/pk_capacity_target_v1.json<br>errors.py::CODES | tests/test_plane.py::PipelineTest.test_every_outcome_class_reachable<br>tests/test_units.py::ErrorsTest.test_released_codes_are_stable |  |
| PLN-05-C015 | verified | spec/pln05_state_machine.mmd<br>health.py::evaluate | tests/fault/test_faults.py::Faults.test_FS03<br>tests/test_plane.py::ControlsTest.test_drain<br>tests/fault/test_faults.py::Faults.test_FS12 |  |
| PLN-05-C016 | verified | docs/release-policy.md<br>tools/schema_compat.py<br>state.py::migrate | tests/compatibility/test_compat.py::Compat.test_current_schemas_compatible_with_released_baseline<br>tests/compatibility/test_compat.py::Compat.test_state_window |  |
| PLN-05-C017 | partial | controller.py::Limits<br>plane.py::ElasticityPlane.lower_ceiling | tests/test_controller.py::ControllerTest.test_lower_ceiling_is_monotonic_and_cannot_cross_floor | per-scope ceilings only; cross-tenant quota/fairness is not owned by PLN-05 (no shared pool) - needs owner confirmation |
| PLN-05-C018 | verified | plane.py::ElasticityPlane.tick<br>spec/pln05_semantics.md | tests/fault/test_faults.py::Faults.test_FS12<br>tests/fault/test_faults.py::Faults.test_FS07<br>tests/test_plane.py::PersistenceAndFailoverTest.test_coordination_outage_never_publishes_without_lease | network partitions are covered for the coordination service and the demand source; transport-level loss belongs to adapters |
| PLN-05-C019 | verified | spec/pln05_semantics.md | tests/test_plane.py::ControlsTest.test_limits_update_cannot_clear_freeze<br>tests/security/test_adversarial.py::Adversarial.test_T19_security_outage_never_expands<br>tests/test_plane.py::PipelineTest.test_lower_ceiling_via_boundary |  |
| PLN-05-C020 | verified | traceability/requirements.json<br>tools/traceability.py | tests/test_repo.py::RepoTest.test_traceability_is_valid |  |
| PLN-05-C021 | verified | spec/interface_reliability.md<br>spec.py::INTERFACES | tests/test_repo.py::RepoTest.test_scope_has_no_drift |  |
| PLN-05-C022 | verified | schemas/<br>wire.py::validate | tests/contract/test_fixtures.py::FixtureDecode.test_invalid_fixtures_fail_with_expected_code |  |
| PLN-05-C023 | verified | iam.py::Authenticator.authenticate<br>keys.py::TransportPolicy | tests/test_units.py::IamTest.test_tampered_token<br>tests/security/test_adversarial.py::Adversarial.test_T01_forged_and_spoofed_demand | transport adapters are not shipped; policy enforced at the adapter seam |
| PLN-05-C024 | verified | iam.py::Authenticator.authorize<br>security/capabilities.json | tests/test_units.py::IamTest.test_default_deny_every_action_not_granted<br>tests/security/test_adversarial.py::Adversarial.test_T09_read_only_escalation |  |
| PLN-05-C025 | verified | spec/interface_reliability.md<br>reliability.py::RetryPolicy | tests/test_units.py::ReliabilityTest.test_deadline_budget_stale_and_cancel |  |
| PLN-05-C026 | verified | errors.py::PlaneError<br>schemas/error_v1.json | tests/test_units.py::ErrorsTest.test_wire_form_validates_against_error_schema |  |
| PLN-05-C027 | verified | wire.py::negotiate | tests/compatibility/test_compat.py::Compat.test_peer_version_negotiation_mixed_fleet |  |
| PLN-05-C028 | verified | wire.py::MAX_BYTES<br>spec/interface_reliability.md | tests/security/test_adversarial.py::Adversarial.test_T07_parser_exhaustion<br>tests/security/test_adversarial.py::Adversarial.test_T14_exhaustion |  |
| PLN-05-C029 | verified | fixtures/protocol/manifest.json | tests/contract/test_fixtures.py::FixtureIntegrity.test_manifest_pins_every_file |  |
| PLN-05-C030 | blocked-external | state.py::FencedSink<br>state.py::LeaseService | tests/test_plane.py::PersistenceAndFailoverTest.test_failover_fences_the_old_leader | adjacent layers exercised through reference doubles; GAP-09/INV-26/SCH-01/pk_core not supplied |
| PLN-05-C031 | partial | pyproject.toml<br>security/approved-versions.json | tests/security/test_adversarial.py::Adversarial.test_T13_dependency_policy | pk_core declared but unresolvable |
| PLN-05-C032 | verified | configuration.py::ConfigStore<br>state.py::StateStore | tests/test_units.py::ConfigTest.test_snapshot_is_immutable<br>tests/test_units.py::ConfigTest.test_journal_restart_and_crash_safety<br>tests/test_units.py::StateTest.test_round_trip_and_scope_isolation |  |
| PLN-05-C033 | verified | config/schema.json<br>config/defaults.json | tests/test_units.py::ConfigTest.test_defaults_valid_and_precedence |  |
| PLN-05-C034 | verified | configuration.py::validate<br>controller.py::Limits | tests/test_units.py::ConfigTest.test_invalid_candidates_never_activate |  |
| PLN-05-C035 | verified | configuration.py::compose | tests/test_units.py::ConfigTest.test_defaults_valid_and_precedence |  |
| PLN-05-C036 | verified | configuration.py::Snapshot | tests/test_units.py::ConfigTest.test_activate_rollback_provenance_and_dry_run |  |
| PLN-05-C037 | verified | configuration.py::ConfigStore.activate | tests/test_units.py::ConfigTest.test_journal_restart_and_crash_safety |  |
| PLN-05-C038 | verified | configuration.py::ConfigStore.rollback<br>docs/release-policy.md | tests/test_units.py::ConfigTest.test_activate_rollback_provenance_and_dry_run | release-level automatic rollback is a documented canary rule, not executed here |
| PLN-05-C039 | verified | configuration.py::_scan_secrets<br>telemetry.py::redact | tests/test_units.py::ConfigTest.test_invalid_candidates_never_activate<br>tests/test_units.py::TelemetryTest.test_redaction |  |
| PLN-05-C040 | partial | docs/runbooks/day0-bootstrap.md<br>tools/ci.py | tools/ci.py::clean_install | library tier reproducible in a clean venv; framework tier blocked on pk_core |
| PLN-05-C041 | verified | security/threat-model.md<br>security/threats.json | tests/security/test_adversarial.py::Adversarial.test_T01_forged_and_spoofed_demand<br>tests/security/test_adversarial.py::Adversarial.test_T02_ceiling_bypass<br>tests/security/test_adversarial.py::Adversarial.test_T19_security_outage_never_expands<br>tests/test_repo.py::RepoTest.test_every_threat_has_a_test | review/approval by security contact pending |
| PLN-05-C042 | verified | security/capabilities.json | tests/test_units.py::IamTest.test_capability_escalation_in_token_is_refused |  |
| PLN-05-C043 | partial | security/iam-model.md<br>security/isolation-model.md | tests/test_repo.py::RepoTest.test_runtime_has_no_ambient_authority | library proven free of sockets/subprocess/env reads; container/VM enforcement is a deployment obligation |
| PLN-05-C044 | partial | iam.py<br>keys.py::TransportPolicy<br>supplychain.py::verify_artifact | tests/test_units.py::KeysTest.test_transport_policy | node/provider authentication happens in adapters not shipped here |
| PLN-05-C045 | partial | supplychain.py::verify_artifact<br>tools/build_release.py | tests/security/test_adversarial.py::Adversarial.test_T12_tampered_artifacts | digest+approved-version enforced; release signature is an ephemeral HMAC, managed signing identity absent |
| PLN-05-C046 | verified | security/isolation-model.md<br>plane.py::ElasticityPlane._principal | tests/security/test_adversarial.py::Adversarial.test_T06_cross_tenant_and_site<br>tests/test_plane.py::ReviewFindingsTest.test_site_scope_enforced_for_reads_and_tenant_controls |  |
| PLN-05-C047 | partial | security/crypto-policy.md<br>keys.py::KeyRing | tests/test_units.py::KeysTest.test_rotation_overlap_and_revocation | encryption at rest delegated to volume/KMS (external); integrity implemented |
| PLN-05-C048 | verified | security/security_dependency_failure_policy.md | tests/security/test_adversarial.py::Adversarial.test_T19_security_outage_never_expands<br>tests/fault/test_faults.py::Faults.test_FS15<br>tests/test_plane.py::ReviewFindingsTest.test_authority_expansion_refused_during_time_fault |  |
| PLN-05-C049 | verified | audit.py::AuditLog | tests/test_units.py::AuditTest.test_detects_edit_gap_reorder_truncation |  |
| PLN-05-C050 | verified | tests/security/test_adversarial.py | tests/test_repo.py::RepoTest.test_every_threat_has_a_test |  |
| PLN-05-C051 | verified | ops/reliability/failure_matrix.json | tests/test_repo.py::RepoTest.test_failure_matrix_scenarios_exist |  |
| PLN-05-C052 | verified | health.py::evaluate | tests/fault/test_faults.py::Faults.test_FS03 |  |
| PLN-05-C053 | verified | reliability.py::RetryPolicy | tests/test_units.py::ReliabilityTest.test_retry_bounds |  |
| PLN-05-C054 | verified | reliability.py::AdmissionController<br>reliability.py::CircuitBreaker | tests/test_units.py::ReliabilityTest.test_breaker_state_machine<br>tests/security/test_adversarial.py::Adversarial.test_T14_exhaustion |  |
| PLN-05-C055 | verified | plane.py::ElasticityPlane._lead<br>ops/reliability/degraded_modes.md | tests/test_plane.py::ReviewFindingsTest.test_stale_leader_reloads_shared_state_on_new_term<br>tests/test_plane.py::ReviewFindingsTest.test_takeover_inherits_idempotency_state<br>tests/fault/test_faults.py::Faults.test_FS07<br>tests/fuzz/test_multi_instance.py::MultiInstance.test_shared_state_two_instances_hold_invariants |  |
| PLN-05-C056 | verified | ops/reliability/degraded_modes.md | tests/fault/test_faults.py::Faults.test_FS09<br>tests/fault/test_faults.py::Faults.test_FS17 |  |
| PLN-05-C057 | verified | state.py::StateStore | tests/fault/test_faults.py::Faults.test_FS01<br>tests/test_units.py::StateTest.test_crash_mid_write_keeps_previous<br>tests/test_plane.py::ReviewFindingsTest.test_persist_failure_on_authority_changes_rolls_back |  |
| PLN-05-C058 | verified | state.py::LeaseService<br>state.py::FencedSink | tests/test_plane.py::ReviewFindingsTest.test_stale_leader_reloads_shared_state_on_new_term<br>tests/fault/test_faults.py::Faults.test_FS10<br>tests/concurrency/test_concurrency.py::Concurrency.test_concurrent_leader_contention<br>tests/fuzz/test_multi_instance.py::MultiInstance.test_shared_state_two_instances_hold_invariants |  |
| PLN-05-C059 | verified | plane.py::ElasticityPlane.control<br>plane.py::ElasticityPlane.resume | tests/test_plane.py::ControlsTest.test_two_person_resume<br>tests/test_plane.py::ReviewFindingsTest.test_resume_proposal_expires_and_binds_to_controls<br>tests/test_plane.py::PersistenceAndFailoverTest.test_tenant_wide_freeze_survives_restart |  |
| PLN-05-C060 | verified | ops/reliability/fault_scenarios.json | tests/fault/test_faults.py::Faults.test_manifest_has_a_test_per_scenario |  |
| PLN-05-C061 | partial | benchmarks/bench.py<br>benchmarks/baseline.json | benchmarks/bench.py | latency/throughput/startup/CPU/memory/persistence measured; network n/a in-process; power NOT_MEASURED |
| PLN-05-C062 | verified | benchmarks/thresholds.json<br>spec/pln05_nfr.json | tests/test_repo.py::RepoTest.test_performance_gate_thresholds<br>ci/performance_gate.py |  |
| PLN-05-C063 | verified | benchmarks/bench.py | benchmarks/bench.py<br>tests/scale/test_soak.py::Soak.test_burst_then_recovery_without_reset |  |
| PLN-05-C064 | partial | benchmarks/bench.py | benchmarks/bench.py | per-workload scaling measured (1/100/1000 scopes); per-tenant overhead not separately measured |
| PLN-05-C065 | verified | performance/efficiency-analysis.md | tests/test_repo.py::RepoTest.test_required_documents_present |  |
| PLN-05-C066 | waiver-proposed | performance/efficiency-analysis.md | tests/test_repo.py::RepoTest.test_required_documents_present | W-002 (PROPOSED) |
| PLN-05-C067 | verified | performance/efficiency-analysis.md | tests/scale/test_soak.py::Soak.test_soak_no_unbounded_growth_or_drift<br>tests/fault/test_faults.py::Faults.test_FS04 |  |
| PLN-05-C068 | waiver-proposed | governance/waivers.json | tests/test_repo.py::RepoTest.test_governance_files_present | W-001 (PROPOSED) |
| PLN-05-C069 | verified | controller.py::ElasticityController<br>health.py::evaluate | tests/test_controller.py::ControllerTest.test_target_never_escapes_active_envelope |  |
| PLN-05-C070 | partial | ci/performance_gate.py<br>benchmarks/thresholds.json | tests/test_repo.py::RepoTest.test_performance_gate_thresholds<br>ci/performance_gate.py | gate enforced locally; baseline PROPOSED, not APPROVED |
| PLN-05-C071 | verified | plane.py::ElasticityPlane.status<br>health.py::evaluate | tests/test_plane.py::ObservabilityTest.test_status_public_vs_admin |  |
| PLN-05-C072 | verified | telemetry.py::Metrics | tests/test_plane.py::ObservabilityTest.test_metrics_logs_and_traces_emitted |  |
| PLN-05-C073 | verified | telemetry.py::Logger<br>plane.py::ElasticityPlane._publish | tests/test_plane.py::ObservabilityTest.test_metrics_logs_and_traces_emitted |  |
| PLN-05-C074 | verified | telemetry.py::Tracer | tests/test_units.py::TelemetryTest.test_traceparent<br>tests/test_plane.py::ObservabilityTest.test_metrics_logs_and_traces_emitted |  |
| PLN-05-C075 | verified | telemetry.py::redact<br>telemetry.py::Metrics | tests/test_units.py::TelemetryTest.test_cardinality_cap_and_label_allowlist<br>tests/security/test_adversarial.py::Adversarial.test_T16_leakage |  |
| PLN-05-C076 | verified | controller.py::REASONS | tests/test_plane.py::PipelineTest.test_decisions_carry_contract_fields |  |
| PLN-05-C077 | verified | plane.py::ElasticityPlane.explain | tests/test_plane.py::ObservabilityTest.test_explain_by_decision_and_correlation |  |
| PLN-05-C078 | partial | plane.py::ElasticityPlane._record_explain | tests/test_plane.py::ObservabilityTest.test_explain_by_decision_and_correlation | release version recorded; live infrastructure graph correlation needs an external graph |
| PLN-05-C079 | verified | observability/telemetry-policy.md | tests/test_units.py::TelemetryTest.test_cardinality_cap_and_label_allowlist<br>tests/test_units.py::TelemetryTest.test_traceparent<br>tests/test_units.py::TelemetryTest.test_redaction |  |
| PLN-05-C080 | verified | observability/alerts.json<br>observability/dashboards.json | tests/test_ops.py::AlertScenarios.test_attack_pattern<br>tests/test_ops.py::AlertScenarios.test_dashboards_cover_required_views |  |
| PLN-05-C081 | verified | controller.py | tests/test_controller.py::ControllerTest.test_scale_down_requires_consecutive_grace_samples |  |
| PLN-05-C082 | verified | tests/contract/test_fixtures.py | tests/contract/test_fixtures.py::FixtureSequences.test_sequences_against_live_plane |  |
| PLN-05-C083 | blocked-external | tests/test_plane.py | tests/test_plane.py::PersistenceAndFailoverTest.test_failover_fences_the_old_leader<br>tests/test_component.py::ConformanceTest.test_all_100_requirements_are_assessed | framework-conformance tier skipped: pk_core not supplied; siblings not supplied |
| PLN-05-C084 | partial | compatibility/supported-versions.json | tests/compatibility/test_compat.py::Compat.test_declared_runtime | one platform (Linux x86_64, CPython 3.11) tested |
| PLN-05-C085 | verified | tests/fuzz/test_fuzz.py | tests/fuzz/test_fuzz.py::Fuzz.test_boundary_only_raises_plane_errors |  |
| PLN-05-C086 | verified | tests/concurrency/test_concurrency.py | tests/concurrency/test_concurrency.py::Concurrency.test_parallel_observe_status_control_config<br>tests/fuzz/test_multi_instance.py::MultiInstance.test_shared_state_two_instances_hold_invariants |  |
| PLN-05-C087 | verified | security/threats.json | tests/security/test_adversarial.py::Adversarial.test_T06_cross_tenant_and_site<br>tests/security/test_adversarial.py::Adversarial.test_T12_tampered_artifacts<br>tests/security/test_adversarial.py::Adversarial.test_T17_control_bypass<br>tests/test_repo.py::RepoTest.test_every_threat_has_a_test |  |
| PLN-05-C088 | partial | tests/scale/test_soak.py<br>benchmarks/bench.py | tests/scale/test_soak.py::Soak.test_fleet_scale_single_process | soak 60k decisions (release tier needs >= 1M); fleet single-process |
| PLN-05-C089 | verified | tests/fault/test_faults.py | tests/fault/test_faults.py::Faults.test_FS07<br>tests/fault/test_faults.py::Faults.test_FS10 |  |
| PLN-05-C090 | verified | tools/ci.py<br>tools/gate.py | tests/test_repo.py::RepoTest.test_gate_refuses_skips_and_self_approval |  |
| PLN-05-C091 | governance-pending | spec.py::SLOS<br>SECURITY.md<br>ops/oncall.json | tests/test_repo.py::RepoTest.test_governance_files_present | SLOs and budgets defined; support commitments need assigned owners |
| PLN-05-C092 | partial | docs/release-policy.md<br>tools/ci.py | tools/ci.py::clean_install | rollback rehearsed in a clean venv; canary not exercised |
| PLN-05-C093 | verified | compatibility/supported-versions.json | tests/compatibility/test_compat.py::Compat.test_declared_runtime |  |
| PLN-05-C094 | implemented | docs/release-policy.md<br>SECURITY.md | tests/test_repo.py::RepoTest.test_governance_files_present | policy text; owner approval pending |
| PLN-05-C095 | verified | docs/runbooks/backup-restore.md<br>state.py::migrate | tests/test_plane.py::PersistenceAndFailoverTest.test_restart_preserves_hysteresis_and_controls<br>tests/fault/test_faults.py::Faults.test_FS19 |  |
| PLN-05-C096 | implemented | docs/runbooks/ | tests/test_repo.py::RepoTest.test_required_documents_present | runbooks written; not yet executed by an operator |
| PLN-05-C097 | governance-pending | docs/runbooks/day2-incidents.md<br>ops/oncall.json | tests/test_repo.py::RepoTest.test_governance_files_present | process defined; paging roles UNASSIGNED |
| PLN-05-C098 | governance-pending | governance/reviews.json | tests/test_repo.py::RepoTest.test_governance_files_present | schedule defined; no review performed yet |
| PLN-05-C099 | verified | governance/waivers.json<br>tools/gate.py | tests/test_repo.py::RepoTest.test_gate_refuses_skips_and_self_approval |  |
| PLN-05-C100 | verified | tools/gate.py | tests/test_repo.py::RepoTest.test_gate_refuses_skips_and_self_approval | gate exists and runs; its current verdict is NO_GO |
| PLN05-S001 | verified | plane.py::ElasticityPlane._publish<br>wire.py::validate | tests/fuzz/test_fuzz.py::Fuzz.test_controller_invariants_long_random_sequences<br>tests/fuzz/test_multi_instance.py::MultiInstance.test_shared_state_two_instances_hold_invariants |  |
| PLN05-S002 | verified | plane.py::ElasticityPlane._lead | tests/fault/test_faults.py::Faults.test_FS10<br>tests/fuzz/test_multi_instance.py::MultiInstance.test_shared_state_two_instances_hold_invariants |  |
| PLN05-S003 | verified | plane.py::ElasticityPlane._publish | tests/fault/test_faults.py::Faults.test_FS06 |  |
| PLN05-S004 | verified | security/security_dependency_failure_policy.md | tests/security/test_adversarial.py::Adversarial.test_T19_security_outage_never_expands |  |
| PLN05-S005 | verified | audit.py::AuditLog<br>plane.py::ElasticityPlane._audit | tests/fault/test_faults.py::Faults.test_FS16 |  |
