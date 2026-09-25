"""Authoritative disposition of the 72 MC-* components for v4.3.0.

status values:
  implemented     package-local code + automated tests exist (still needs independent review)
  draft           document/definition exists; owner approval required
  owner-required  only the accountable owner can supply it (names, licence, sign-off)
  external        requires infrastructure not in the package (cloud, KMS, hardware, CI farm)
  blocked         cannot proceed; input missing
"""

T = "tests/test_production.py"
C = "tests/test_component.py"

ITEMS = [
    # id, title, status, artifacts, tests
    ("MC-001", "Authoritative MASTER.md source package", "blocked", ["governance/SOURCE_PACKAGE.md"], []),
    ("MC-002", "Accountable owner and escalation registry", "owner-required", ["governance/OWNERS.yaml"], []),
    ("MC-003", "Approved Architecture Decision Record", "draft", ["governance/ADR-001-state-engine.md", "governance/ARCHITECTURE.md"], []),
    ("MC-004", "SHALL-level requirements specification", "draft", ["governance/REQUIREMENTS.md"], []),
    ("MC-005", "Requirements traceability matrix", "implemented", ["governance/TRACEABILITY.json", "tools/build_status.py"], []),
    ("MC-006", "Deployment/support matrix", "draft", ["governance/SUPPORT_MATRIX.md", "execution.py"], [T + "::ExecutionTest.test_platform_check"]),
    ("MC-007", "Compatibility/version policy", "draft", ["governance/COMPATIBILITY_POLICY.md", "durable.py"], [T + "::DurableBackendTest.test_migration_from_v0_and_refusal_of_unknown"]),
    ("MC-008", "Capacity/quota/fairness specification", "draft", ["governance/CAPACITY.md"], [T + "::DurableBackendTest.test_size_limit", T + "::SecurityTest.test_tenant_isolation"]),
    ("MC-009", "Constraint-precedence policy", "implemented", ["policy.py"], [T + "::PolicyTest.test_constraint_precedence"]),
    ("MC-010", "Durable remote-state backend", "implemented", ["durable.py"], [T + "::DurableBackendTest"]),
    ("MC-011", "Distributed lock/lease/fencing backend", "implemented", ["locking.py"], [T + "::LockingTest"]),
    ("MC-012", "Crash-safe transaction journal", "implemented", ["durable.py"], [T + "::DurableBackendTest.test_crash_between_revision_and_head_rolls_back", T + "::DurableBackendTest.test_crash_after_head_before_commit_rolls_forward"]),
    ("MC-013", "State rollback engine", "implemented", ["durable.py"], [T + "::RollbackBackupTest.test_rollback_creates_new_serial"]),
    ("MC-014", "Backup/restore/migration tooling", "implemented", ["durable.py"], [T + "::RollbackBackupTest"]),
    ("MC-015", "Terraform execution adapter", "implemented", ["execution.py"], [T + "::ExecutionTest.test_runner_with_stub_engine", T + "::ExecutionTest.test_plan_json_parser"]),
    ("MC-016", "HCL/configuration parser and compiler", "implemented", ["config.py"], [T + "::ConfigGraphTest"]),
    ("MC-017", "Resource-graph engine", "implemented", ["graph.py"], [T + "::ConfigGraphTest.test_graph_cycles_dangling_and_dependents"]),
    ("MC-018", "Provider plugin lifecycle manager", "implemented", ["execution.py"], [T + "::ExecutionTest.test_provider_pins"]),
    ("MC-019", "Cloud-provider adapters", "external", ["execution.py (Provider protocol + InMemoryProvider conformance reference)"], [T + "::ExecutionTest.test_provider_contract_and_partial_failure"]),
    ("MC-020", "Datacenter/bare-metal adapters", "external", ["execution.py (Provider protocol)"], []),
    ("MC-021", "Edge/disconnected execution adapter", "implemented", ["resilience.py"], [T + "::ResilienceTest.test_offline_queue_and_failover"]),
    ("MC-022", "GAP-13 policy-engine integration", "implemented", ["policy.py", "service.py"], [T + "::PolicyTest", T + "::ControlPlaneTest"]),
    ("MC-023", "INV-01/INV-07/INV-08 integration adapters", "implemented", ["policy.py"], [T + "::PolicyTest.test_inv_adapters"]),
    ("MC-024", "Site/environment configuration overlay system", "implemented", ["config.py"], [T + "::ConfigGraphTest.test_parse_compile_order", T + "::ConfigGraphTest.test_overlay_cannot_add_resources_or_unknown_layer"]),
    ("MC-025", "Configuration provenance ledger", "implemented", ["config.py"], [T + "::ConfigGraphTest.test_provenance_ledger"]),
    ("MC-026", "Timeout/cancellation/retry/idempotency layer", "implemented", ["resilience.py"], [T + "::ResilienceTest.test_retry_backoff_and_classification", T + "::ResilienceTest.test_idempotency"]),
    ("MC-027", "Admission/load-shedding/circuit-breaker controls", "implemented", ["resilience.py"], [T + "::ResilienceTest.test_admission_and_breaker", T + "::FaultSoakTest.test_burst_load_is_shed_not_queued_unboundedly"]),
    ("MC-028", "Degraded-dependency mode", "implemented", ["resilience.py", "service.py"], [T + "::ResilienceTest.test_degraded_freeze_watchdog"]),
    ("MC-029", "Failover and residency-aware continuity controller", "implemented", ["resilience.py"], [T + "::ResilienceTest.test_offline_queue_and_failover"]),
    ("MC-030", "Quarantine/freeze/emergency-disable controller", "implemented", ["resilience.py", "service.py"], [T + "::ResilienceTest.test_degraded_freeze_watchdog", T + "::ControlPlaneTest.test_policy_freeze_outage_partial"]),
    ("MC-031", "Health/stall watchdog", "implemented", ["resilience.py"], [T + "::ResilienceTest.test_degraded_freeze_watchdog"]),
    ("MC-032", "Formal threat model", "draft", ["governance/THREAT_MODEL.md"], []),
    ("MC-033", "Authentication integration", "implemented", ["security.py"], [T + "::SecurityTest.test_authn_rejects_forged_and_malformed"]),
    ("MC-034", "Authorization/capability engine", "implemented", ["security.py"], [T + "::SecurityTest.test_authn_authz_tenant_and_sod"]),
    ("MC-035", "Ambient-authority sandbox", "implemented", ["execution.py"], [T + "::ExecutionTest.test_sandbox_env"]),
    ("MC-036", "Artifact signature/provenance verifier", "implemented", ["security.py"], [T + "::SecurityTest.test_artifact_verification", T + "::SecurityTest.test_signed_plan_and_key_rotation"]),
    ("MC-037", "Tenant/workload isolation layer", "implemented", ["security.py"], [T + "::SecurityTest.test_tenant_isolation"]),
    ("MC-038", "Encryption and KMS integration", "external", ["security.py (KeyProvider protocol)"], []),
    ("MC-039", "Security-service outage policy", "implemented", ["security.py"], [T + "::SecurityTest.test_outage_policy"]),
    ("MC-040", "Durable signed audit service", "implemented", ["security.py"], [T + "::SecurityTest.test_signed_audit_log"]),
    ("MC-041", "Secret/redaction guard", "implemented", ["security.py", "observability.py"], [T + "::SecurityTest.test_redaction"]),
    ("MC-042", "Adversarial security test suite", "implemented", [T], [T + "::SecurityTest", T + "::AdversarialPropertyTest"]),
    ("MC-043", "Health/readiness/status interface", "implemented", ["observability.py", "service.py"], [T + "::ObservabilityTest.test_health"]),
    ("MC-044", "Metrics exporter", "implemented", ["observability.py"], [T + "::ObservabilityTest.test_metrics_exposition_and_guards"]),
    ("MC-045", "Structured logging pipeline", "implemented", ["observability.py"], [T + "::ObservabilityTest.test_logging_and_trace"]),
    ("MC-046", "Distributed tracing integration", "implemented", ["observability.py"], [T + "::ObservabilityTest.test_logging_and_trace"]),
    ("MC-047", "Decision/explainability view", "implemented", ["observability.py"], [T + "::ObservabilityTest.test_explain_and_lineage"]),
    ("MC-048", "Release-lineage/live-graph correlation", "implemented", ["observability.py"], [T + "::ObservabilityTest.test_explain_and_lineage"]),
    ("MC-049", "Telemetry governance policy", "draft", ["governance/TELEMETRY_GOVERNANCE.md"], []),
    ("MC-050", "Dashboards and alert rules", "draft", ["ops/prometheus_rules.yml"], []),
    ("MC-051", "Performance baseline/benchmark harness", "implemented", ["release.py", "evidence/benchmarks.json"], [T + "::ReleaseTest.test_bench_slo_capacity"]),
    ("MC-052", "Tail-latency/SLO thresholds", "implemented", ["release.py", "governance/SLO_SUPPORT.md"], [T + "::ReleaseTest.test_bench_slo_capacity"]),
    ("MC-053", "Tenant/workload overhead and capacity model", "implemented", ["release.py", "evidence/capacity_model.json"], [T + "::ReleaseTest.test_bench_slo_capacity"]),
    ("MC-054", "Serialization/copy/network efficiency audit", "implemented", ["release.py", "evidence/copy_audit.json"], [T + "::ReleaseTest.test_bench_slo_capacity"]),
    ("MC-055", "Edge power/thermal benchmark", "external", ["governance/EDGE_POWER.md"], []),
    ("MC-056", "Public-interface contract test suite", "implemented", [T, C], [T, C]),
    ("MC-057", "Adjacent-layer integration suite", "external", ["policy.py adapters (contract-level only)"], [T + "::PolicyTest.test_inv_adapters"]),
    ("MC-058", "Compatibility matrix test farm", "external", ["ops/ci-matrix.yml"], []),
    ("MC-059", "Fuzz/property-based test suite", "implemented", [T], [T + "::AdversarialPropertyTest"]),
    ("MC-060", "Fault-injection and partition test suite", "implemented", [T], [T + "::DurableBackendTest", T + "::LockingTest", T + "::FaultSoakTest", T + "::ExecutionTest.test_provider_contract_and_partial_failure"]),
    ("MC-061", "Soak/burst/fleet-scale test suite", "implemented", [T], [T + "::FaultSoakTest"]),
    ("MC-062", "Machine-readable acceptance evidence artifact", "implemented", ["release.py", "evidence/acceptance_evidence.json"], [T + "::ReleaseTest.test_evidence_roundtrip"]),
    ("MC-063", "Canary/staged rollout automation", "implemented", ["release.py"], [T + "::ReleaseTest.test_canary"]),
    ("MC-064", "Supported-version matrix and dependency pins", "implemented", ["pyproject.toml", "governance/SUPPORT_MATRIX.md", "execution.py"], [T + "::ReleaseTest.test_packaging_metadata_consistent", T + "::ExecutionTest.test_platform_check"]),
    ("MC-065", "Vulnerability/patch/EOL policy", "draft", ["governance/VULN_EOL_POLICY.md"], []),
    ("MC-066", "Incident response runbook", "draft", ["ops/RUNBOOK.md"], []),
    ("MC-067", "Recurring review program", "draft", ["governance/REVIEW_PROGRAM.md"], []),
    ("MC-068", "Exception/waiver/technical-debt ledger", "draft", ["governance/WAIVERS.json"], []),
    ("MC-069", "Formal production exit gate", "implemented", ["release.py", "tools/build_status.py", "evidence/PRODUCTION_GATE.json"], [T + "::ReleaseTest.test_gate_never_go_with_open_items"]),
    ("MC-070", "Production support/SLO commitment document", "draft", ["governance/SLO_SUPPORT.md"], []),
    ("MC-071", "Packaging metadata and reproducible build definition", "implemented", ["pyproject.toml", "MANIFEST.sha256"], [T + "::ReleaseTest.test_packaging_metadata_consistent"]),
    ("MC-072", "License/NOTICE provenance package", "owner-required", ["LICENSE", "THIRD-PARTY-NOTICES.md", "evidence/sbom.cdx.json"], []),
]

assert len(ITEMS) == 72 and len({i[0] for i in ITEMS}) == 72

CODE = {i[0] for i in ITEMS if i[2] == "implemented"}

# Baseline CHK-nnn -> components for which that control is evidenced package-locally.
# "CODE" expands to every implemented component.  Anything not listed stays open.
ALL = "CODE"
CHECK_RULES: dict[int, set[str] | str] = {
    1: ALL, 2: ALL, 4: ALL, 6: ALL,                      # scope, SHALL (REQUIREMENTS.md), deps, acceptance (tests)
    5: {"MC-006", "MC-064"},
    7: ALL,                                               # ARCHITECTURE.md
    8: ALL, 9: ALL, 10: ALL, 11: ALL, 15: ALL,           # interfaces, ids, validation, concurrency, error taxonomy
    12: {"MC-010", "MC-012", "MC-013", "MC-014", "MC-025", "MC-040"},
    13: {"MC-007", "MC-010", "MC-014", "MC-016", "MC-018", "MC-064"},
    14: {"MC-016", "MC-024", "MC-025"},
    16: ALL,                                              # THREAT_MODEL.md
    17: {"MC-033", "MC-022", "MC-030", "MC-043"},        # wired in service.ControlPlane
    18: {"MC-034", "MC-037", "MC-030", "MC-013"},
    19: {"MC-041", "MC-040", "MC-044", "MC-045", "MC-047", "MC-035"},
    21: {"MC-010", "MC-014", "MC-015", "MC-018", "MC-025", "MC-036", "MC-040", "MC-062", "MC-023"},
    22: {"MC-039", "MC-022", "MC-033"},
    23: ALL,
    24: {"MC-026", "MC-015", "MC-027"},
    25: {"MC-010", "MC-011", "MC-012", "MC-013", "MC-014", "MC-060"},
    26: {"MC-027", "MC-008", "MC-021", "MC-044"},
    27: {"MC-028", "MC-030", "MC-039"},
    28: {"MC-013", "MC-014", "MC-063", "MC-021"},
    29: {"MC-030", "MC-063"},
    30: ALL,                                              # ops/RUNBOOK.md
    31: {"MC-043", "MC-031"},
    32: {"MC-044"},
    33: {"MC-045"},
    34: {"MC-046"},
    35: {"MC-052", "MC-051"},
    36: {"MC-008", "MC-053"},
    37: ALL, 38: ALL,
    40: {"MC-042", "MC-033", "MC-034", "MC-036", "MC-010", "MC-014", "MC-016", "MC-022", "MC-025", "MC-040", "MC-041", "MC-059"},
    41: {"MC-010", "MC-011", "MC-026", "MC-027", "MC-061"},
    42: {"MC-059", "MC-016", "MC-042"},
    43: {"MC-060", "MC-010", "MC-011", "MC-012", "MC-022", "MC-027"},
    45: ALL,                                              # evidence/acceptance_evidence.json binds all files
    47: ALL,                                              # ops/RUNBOOK.md
    48: {"MC-064", "MC-007"},
    49: ALL,                                              # TRACEABILITY.json
}
OWNER_CHECKS = {3, 50}          # named owners, independent review
EXTERNAL_CHECKS = {20, 39, 44, 46}  # KMS/at-rest crypto, real adjacent integration, production-scale load, vuln scan
DRAFT_DOC_CHECKS = {1, 2, 5, 7, 16}  # draft-status docs evidence these for draft components (pending approval)
