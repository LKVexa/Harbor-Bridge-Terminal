# INV-06 Traditional IaC — Normative Requirements (MC-004)

Status: **Draft — derived from implemented behaviour; requires owner approval.** Each requirement is verified by the test(s) named. `TRACEABILITY.json` is generated from this file by `tools/build_status.py`.

Key words SHALL / SHALL NOT per RFC 2119.

| ID | Requirement | Source | Verified by |
|---|---|---|---|
| REQ-001 | The engine SHALL compute a plan against the current state serial before every change. | C011 | test_component.CoreStateTest.test_plan_apply_and_detached_snapshots |
| REQ-002 | The engine SHALL NOT apply a plan whose serial differs from the state serial. | C013 | test_component.CoreStateTest.test_stale_plan_is_refused_atomically |
| REQ-003 | The engine SHALL NOT apply or plan the destruction of a protected resource. | C014 | test_component.CoreStateTest.test_protection_is_read_only_and_invalidates_outstanding_plan |
| REQ-004 | The engine SHALL refuse structurally invalid or digest-mismatched plans without mutating state. | C015 | test_production.AdversarialPropertyTest.test_fuzz_plan_validation_never_mutates_on_bad_input |
| REQ-005 | Drift detection SHALL distinguish a missing resource from a present JSON null. | C016 | test_component.CoreStateTest.test_drift_distinguishes_missing_from_json_null |
| REQ-006 | The state backend SHALL publish revisions by compare-and-swap on the serial and SHALL NOT accept a stale writer. | MC-010 | test_production.DurableBackendTest.test_commit_load_roundtrip_and_cas; FaultSoakTest.test_concurrent_writers_to_backend_one_wins_per_serial |
| REQ-007 | The backend SHALL detect revision corruption before use. | MC-010 | test_production.DurableBackendTest.test_corruption_detected_before_use |
| REQ-008 | Interrupted commits SHALL be resolved deterministically on restart. | MC-012 | test_production.DurableBackendTest.test_crash_between_revision_and_head_rolls_back; test_crash_after_head_before_commit_rolls_forward |
| REQ-009 | Rollback SHALL create a new, higher serial and SHALL record actor, reason and source revision. | MC-013 | test_production.RollbackBackupTest.test_rollback_creates_new_serial |
| REQ-010 | Restore SHALL verify every revision digest and the revision chain and SHALL refuse a non-empty target. | MC-014 | test_production.RollbackBackupTest.test_backup_restore_verifies; test_restore_rejects_tampered_archive |
| REQ-011 | Only the current lease holder with the newest fencing token SHALL commit. | MC-011 | test_production.LockingTest.test_mutual_exclusion_and_fencing; test_cross_process_exclusion |
| REQ-012 | The configuration parser SHALL refuse any construct outside `inv06-hcl-subset/1`. | MC-016 | test_production.ConfigGraphTest.test_parser_refuses_outside_subset; AdversarialPropertyTest.test_fuzz_hcl_parser_only_raises_config_error |
| REQ-013 | Overlays SHALL apply in order global < environment < site and SHALL NOT introduce resources. | MC-024 | test_production.ConfigGraphTest.test_overlay_cannot_add_resources_or_unknown_layer |
| REQ-014 | The resource graph SHALL refuse cycles and dangling references and SHALL order destroys dependents-first. | MC-017 | test_production.ConfigGraphTest.test_graph_cycles_dangling_and_dependents |
| REQ-015 | Every configuration activation SHALL record digest, source revision, actor, environment, approval and rollback link. | MC-025 | test_production.ConfigGraphTest.test_provenance_ledger |
| REQ-016 | Apply SHALL be refused unless the policy engine returns an allow decision bound to the plan digest and required policy version. | MC-022 | test_production.PolicyTest.test_fail_closed; test_deny_with_reasons |
| REQ-017 | Constraint resolution SHALL follow security > residency > consistency > availability > SLO > cost > operator override. | MC-009 | test_production.PolicyTest.test_constraint_precedence |
| REQ-018 | Every request SHALL carry an authenticated identity; expired, forged, wrong-audience or malformed credentials SHALL be refused. | MC-033 | test_production.SecurityTest.test_authn_rejects_forged_and_malformed |
| REQ-019 | Authorization SHALL be default-deny, tenant-scoped, and SHALL NOT let a plan author approve their own plan. | MC-034 | test_production.SecurityTest.test_authn_authz_tenant_and_sod |
| REQ-020 | Signed plans SHALL bind approver, digest and serial; revoked keys SHALL NOT verify. | MC-036 | test_production.SecurityTest.test_signed_plan_and_key_rotation |
| REQ-021 | Engine binaries and providers SHALL be verified against pinned SHA-256 digests before use. | MC-018, MC-036 | test_production.ExecutionTest.test_runner_refuses_without_pinned_engine; test_provider_pins; SecurityTest.test_artifact_verification |
| REQ-022 | Tenants SHALL have separate state namespaces and quotas; path escapes SHALL be refused. | MC-037 | test_production.SecurityTest.test_tenant_isolation |
| REQ-023 | Mutations SHALL fail closed when identity, policy, key, audit, time or attestation services are unavailable. | MC-039 | test_production.SecurityTest.test_outage_policy |
| REQ-024 | Audit events SHALL be hash-chained, signed, fsync'd and redacted. | MC-040 | test_production.SecurityTest.test_signed_audit_log |
| REQ-025 | Secrets SHALL NOT appear in logs, audit events, metric labels or explanations. | MC-041 | test_production.SecurityTest.test_redaction; ObservabilityTest.test_logging_and_trace; test_metrics_exposition_and_guards |
| REQ-026 | Fallible calls SHALL have deadlines, cancellation, bounded jittered retry of retryable errors only, and idempotency keys. | MC-026 | test_production.ResilienceTest.test_retry_backoff_and_classification; test_idempotency |
| REQ-027 | Overload SHALL be shed with a typed error rather than queued without bound; failing dependencies SHALL trip a breaker. | MC-027 | test_production.ResilienceTest.test_admission_and_breaker; FaultSoakTest.test_burst_load_is_shed_not_queued_unboundedly |
| REQ-028 | Loss of a critical dependency SHALL switch to read-only mode. | MC-028 | test_production.ResilienceTest.test_degraded_freeze_watchdog |
| REQ-029 | Freeze SHALL block mutation while reads continue; unfreeze SHALL require a distinct second approver. | MC-030 | test_production.ResilienceTest.test_degraded_freeze_watchdog |
| REQ-030 | Stalled operations SHALL be reported and SHALL make readiness false. | MC-031, MC-043 | test_production.ResilienceTest.test_degraded_freeze_watchdog; ObservabilityTest.test_health |
| REQ-031 | Offline-queued plans SHALL be reconciled by serial on reconnect; expired or conflicting plans SHALL NOT be forced. | MC-021 | test_production.ResilienceTest.test_offline_queue_and_failover |
| REQ-032 | Failover SHALL select only a site within the residency set holding at least the committed serial. | MC-029 | test_production.ResilienceTest.test_offline_queue_and_failover |
| REQ-033 | Metrics SHALL be exported in Prometheus text format with an allowlisted, bounded label set. | MC-044 | test_production.ObservabilityTest.test_metrics_exposition_and_guards |
| REQ-034 | Logs SHALL be JSON with schema, severity, component, tenant, operation and trace identifiers. | MC-045, MC-046 | test_production.ObservabilityTest.test_logging_and_trace |
| REQ-035 | Every plan SHALL be explainable per resource with changed fields and policy decision. | MC-047 | test_production.ObservabilityTest.test_explain_and_lineage |
| REQ-036 | A partially executed provider run SHALL NOT be committed to state. | MC-019 contract | test_production.ExecutionTest.test_provider_contract_and_partial_failure |
| REQ-037 | Engine execution SHALL use a scrubbed environment and SHALL refuse ambient cloud credentials. | MC-035 | test_production.ExecutionTest.test_sandbox_env |
| REQ-038 | Reference latency thresholds SHALL block release when exceeded. | MC-052 | test_production.ReleaseTest.test_bench_slo_capacity |
| REQ-039 | Release evidence SHALL bind file digests, runtime and test results and SHALL be signed. | MC-062 | test_production.ReleaseTest.test_evidence_roundtrip |
| REQ-040 | Rollout SHALL halt and roll back when a stage health gate fails. | MC-063 | test_production.ReleaseTest.test_canary |
| REQ-041 | The production gate SHALL NOT return GO while any owner, external or blocked item is open. | MC-069 | test_production.ReleaseTest.test_gate_never_go_with_open_items |
| REQ-042 | Package metadata SHALL declare version and zero runtime dependencies consistently. | MC-071 | test_production.ReleaseTest.test_packaging_metadata_consistent |
