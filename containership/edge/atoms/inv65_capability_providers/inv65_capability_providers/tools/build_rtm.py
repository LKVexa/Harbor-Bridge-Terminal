"""Build traceability/INV65_RTM.json (M31) from the authored mapping below.

Status vocabulary (never upgraded by prose alone -- tools/check_rtm.py enforces
that every 'verified-local' row cites at least one existing test function):
  verified-local  executable tests in this archive pass for the requirement
  documented      requirement is itself a documentation duty; doc exists
  partial         implemented/tested locally but an external condition remains
  blocked         cannot be satisfied inside this archive; blocker named
Owner/reviewer fields stay "UNASSIGNED" until the owner records real people.
"""
from __future__ import annotations

import json
import pathlib
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
T = "tests/"
R = {
 1: ("documented", ["contract.py", "README.md"], [], []),
 2: ("documented", ["contract.py", "README.md"], [], []),
 3: ("documented", ["contract.py", "docs/architecture.md"], [], []),
 4: ("verified-local", ["state/store.py"], [T+"fault/test_state_recovery.py::test_process_restart_restores_non_revoked_and_not_revoked"], ["M05"]),
 5: ("documented", ["contract.py", "docs/architecture.md"], [], []),
 6: ("verified-local", ["identity/context.py", "docs/identity-trust-boundaries.md"], [T+"security/test_identity_binding.py::test_same_names_other_tenant_is_a_different_link"], ["M06"]),
 7: ("documented", ["contract.py"], [], []),
 8: ("documented", ["docs/architecture.md"], [], []),
 9: ("blocked", ["docs/ownership-escalation.md"], [], ["M32"], "owner must name accountable owner + reviewer (UNASSIGNED)"),
 10: ("blocked", ["docs/adr/ADR-0001-provider-runtime.md"], [], ["M32"], "ADR is PROPOSED; approval is a human act"),
 11: ("documented", ["docs/architecture.md"], [], []),
 12: ("partial", ["docs/architecture.md", "compatibility/matrix.json"], [], ["M28"], "edge tiers not exercised"),
 13: ("verified-local", ["slo/SLO.json"], [T+"test_runtime_units.py::Slo"], ["M39"]),
 14: ("verified-local", ["errors/mapping.py", "docs/error-catalog.md"], [T+"contract/test_error_compatibility.py::test_every_code_round_trips"], ["M13"]),
 15: ("verified-local", ["lifecycle/state_machines.py", "docs/lifecycle-state-machines.md"], [T+"test_runtime_units.py::Lifecycle"], ["M11"]),
 16: ("verified-local", ["schemas/COMPATIBILITY.md", "registry/model.py"], [T+"contract/test_golden_vectors.py::test_mixed_version_matrix"], ["M03", "M12"]),
 17: ("verified-local", ["runtime/admission.py", "runtime/quotas.py"], [T+"test_runtime_units.py::Admission"], ["M15"]),
 18: ("partial", ["resilience/failover.py", "docs/failure-mode-matrix.md"], [T+"fault/test_failover_splitbrain.py::test_degraded_mode_serves_reads_only_and_refuses_link_changes"], ["M17"], "no real network partition harness"),
 19: ("documented", ["docs/architecture.md"], [], []),
 20: ("verified-local", ["traceability/INV65_RTM.json", "tools/check_rtm.py"], [T+"test_release_tooling.py::test_rtm_is_consistent"], ["M31"]),
 21: ("verified-local", ["transport/http_adapter.py", "docs/architecture.md"], [T+"integration/test_host_http.py::test_full_link_call_unlink_over_http"], ["M04"]),
 22: ("verified-local", ["schemas/"], [T+"contract/test_golden_vectors.py::test_valid_fixtures_pass"], ["M03"]),
 23: ("verified-local", ["authn/authenticator.py", "docs/authentication.md"], [T+"security/test_authentication.py::test_service_refuses_unauthenticated_calls"], ["M07"]),
 24: ("verified-local", ["authz/decision.py", "docs/authorization-integration.md"], [T+"security/test_authorization_enforcement.py::test_wrong_action_link_contract_or_op"], ["M08"]),
 25: ("verified-local", ["runtime/call_control.py", "runtime/idempotency.py"], [T+"test_runtime_units.py::CallControl"], ["M14"]),
 26: ("verified-local", ["schemas/pk_provider_error/v1.json"], [T+"contract/test_error_compatibility.py::test_every_code_round_trips"], ["M13"]),
 27: ("verified-local", ["registry/model.py"], [T+"contract/test_golden_vectors.py::test_mixed_version_matrix", T+"contract/test_error_compatibility.py::test_newer_peer_unknown_code_degrades"], ["M12", "M13"]),
 28: ("verified-local", ["docs/limits.md", "transport/http_adapter.py"], [T+"integration/test_host_http.py::test_boundary_rejections"], ["M15"]),
 29: ("verified-local", ["conformance/fixtures/", "fixtures/providers/"], [T+"conformance/test_adapter_suite.py::test_contract_invariants_hold_for_every_capability_class"], ["M24", "M38"]),
 30: ("blocked", [T+"integration/test_adjacent_layers.py"], [T+"integration/test_adjacent_layers.py::test_inv61_wire_roundtrip_and_error_envelope"], ["M23"], "tested only against contract stubs; real INV-60/55/64/61 not in archive"),
 31: ("partial", ["supply_chain/provider_catalog.json", "pyproject.toml", "lock/constraints.txt"], [T+"integration/test_registry_negotiation.py::test_untrusted_or_revoked_artifact_refused"], ["M20", "M36", "M02"], "pk_core cannot be pinned: no source/digest available"),
 32: ("verified-local", ["state/store.py", "supply_chain/trust.py"], [T+"fault/test_state_recovery.py::test_snapshot_checksum_and_compaction"], ["M05"]),
 33: ("verified-local", ["host/bootstrap.py", "docs/configuration.md"], [T+"security/test_key_rotation.py::TransportPolicy"], ["M10"]),
 34: ("verified-local", ["provider.py", "config/model.py"], [T+"security/test_secret_handling.py::test_bad_refs_and_inline_secrets_rejected"], ["M10"]),
 35: ("verified-local", ["host/bootstrap.py", "residency/engine.py"], [T+"test_runtime_units.py::Residency"], ["M40"]),
 36: ("verified-local", ["config/model.py"], [T+"test_runtime_units.py::ConfigTransactions"], ["M10"]),
 37: ("verified-local", ["config/model.py"], [T+"test_runtime_units.py::ConfigTransactions"], ["M10"]),
 38: ("verified-local", ["config/model.py", "rollout/controller.py"], [T+"integration/test_rollout.py::test_auto_rollback_on_canary_errors"], ["M10", "M33"]),
 39: ("verified-local", ["secret_refs/resolver.py", "observability/telemetry.py"], [T+"security/test_secret_handling.py::test_secret_resolved_in_scope_and_never_persisted_or_logged"], ["M09"]),
 40: ("partial", ["host/server.py", "host/bootstrap.py", "docs/runbooks/day0-day1-day2.md"], [T+"integration/test_host_http.py::test_probes_and_metrics"], ["M04", "M02"], "bootstrap of pk_core conformance path needs pk_core"),
 41: ("documented", ["docs/threat-model.md"], [], ["M32"]),
 42: ("verified-local", ["authz/decision.py"], [T+"security/test_authorization_enforcement.py::test_wrong_subject_scope"], ["M08"]),
 43: ("partial", ["provider.py", "docs/threat-model.md"], [T+"security/test_adversarial.py::test_exhaustion_bounds"], [], "process sandboxing (seccomp/wasm) belongs to INV-60 host"),
 44: ("verified-local", ["authn/authenticator.py", "registry/model.py"], [T+"security/test_authentication.py::test_bad_signature_and_tamper"], ["M07", "M20"]),
 45: ("partial", ["supply_chain/trust.py"], [T+"test_runtime_units.py::SupplyChain"], ["M20"], "digest pinning enforced; signature verification of release artifacts is an owner-held key step"),
 46: ("verified-local", ["service.py", "identity/context.py"], [T+"security/test_identity_binding.py::test_two_tenants_same_link_name_are_isolated"], ["M06"]),
 47: ("partial", ["crypto/at_rest.py", "crypto/transport.py", "docs/key-management.md"], [T+"security/test_key_rotation.py::KeyRotation"], ["M19"], "KMS integration and mTLS certificate issuance external"),
 48: ("verified-local", ["secret_refs/resolver.py", "crypto/at_rest.py"], [T+"security/test_secret_handling.py::test_backend_outage_fails_closed", T+"security/test_key_rotation.py::KeyRotation"], ["M09", "M19"]),
 49: ("verified-local", ["audit/emitter.py", "audit/verification.py"], [T+"security/test_audit_chain.py::test_every_sensitive_action_audited_and_chain_verifies"], ["M18"]),
 50: ("verified-local", ["fuzz/harness.py"], [T+"security/test_adversarial.py::test_token_malleability_regression"], ["M25"]),
 51: ("documented", ["docs/failure-mode-matrix.md", "tests/fault/fault_matrix.json"], [], ["M26"]),
 52: ("verified-local", ["health/model.py"], [T+"test_runtime_units.py::Health"], ["M16"]),
 53: ("verified-local", ["runtime/call_control.py"], [T+"fault/test_fault_scenarios.py::test_transient_failure_retry_rules"], ["M14"]),
 54: ("verified-local", ["runtime/admission.py", "runtime/circuit_breaker.py"], [T+"fault/test_fault_scenarios.py::test_backend_outage_opens_breaker_then_recovers"], ["M15"]),
 55: ("verified-local", ["resilience/failover.py"], [T+"fault/test_failover_splitbrain.py::test_failover_target_respects_residency_and_health"], ["M17", "M40"]),
 56: ("verified-local", ["service.py", "resilience/failover.py"], [T+"fault/test_failover_splitbrain.py::test_degraded_mode_serves_reads_only_and_refuses_link_changes"], ["M17"]),
 57: ("verified-local", ["state/store.py"], [T+"fault/test_state_recovery.py::test_torn_tail_discarded_mid_record_corruption_fails_closed"], ["M05"]),
 58: ("verified-local", ["resilience/fencing.py", "registry/model.py"], [T+"fault/test_failover_splitbrain.py::test_stale_owner_is_fenced_after_takeover"], ["M17"]),
 59: ("verified-local", ["rollout/controller.py", "service.py"], [T+"integration/test_rollout.py::test_emergency_disable_two_person_rule"], ["M33"]),
 60: ("verified-local", ["tests/fault/fault_matrix.json"], [T+"fault/test_fault_scenarios.py::test_fault_matrix_references_existing_tests"], ["M26"]),
 61: ("partial", ["benchmarks/harness.py", "benchmarks/baselines/local.json"], [T+"test_release_tooling.py::test_benchmark_gate_logic"], ["M27"], "single-host baseline only"),
 62: ("verified-local", ["slo/SLO.json", "benchmarks/baselines/local.json"], [T+"test_release_tooling.py::test_benchmark_gate_logic"], ["M27", "M39"]),
 63: ("partial", ["benchmarks/harness.py"], [], ["M27"], "scale-out/scale-in not measurable without a fleet"),
 64: ("partial", ["benchmarks/harness.py"], [], ["M27"], "per-tenant overhead measured only as admission fairness"),
 65: ("verified-local", ["docs/performance-notes.md"], [T+"test_release_tooling.py::test_benchmark_gate_logic"], ["M27"]),
 66: ("documented", ["docs/performance-notes.md"], [], []),
 67: ("verified-local", ["runtime/call_control.py", "runtime/idempotency.py", "observability/telemetry.py"], [T+"test_runtime_units.py::CallControl::test_backpressure_sheds_when_queue_full"], ["M15"]),
 68: ("blocked", [], [], ["M27"], "no constrained edge hardware available"),
 69: ("partial", ["docs/capacity-model.md"], [], ["M15", "M22"], "saturation signals exported; capacity model unvalidated at fleet scale"),
 70: ("verified-local", ["benchmarks/harness.py", "tools/release_gate.py"], [T+"test_release_tooling.py::test_benchmark_gate_logic"], ["M27", "M29"]),
 71: ("verified-local", ["health/model.py", "transport/http_adapter.py"], [T+"integration/test_host_http.py::test_probes_and_metrics"], ["M16"]),
 72: ("verified-local", ["observability/telemetry.py"], [T+"test_runtime_units.py::Telemetry::test_service_emits_metrics_traces_and_explanations"], ["M21"]),
 73: ("verified-local", ["observability/telemetry.py"], [T+"test_runtime_units.py::Telemetry::test_redaction"], ["M21"]),
 74: ("partial", ["observability/telemetry.py"], [T+"test_runtime_units.py::Telemetry::test_traceparent"], ["M21"], "no exporter to a tracing backend"),
 75: ("verified-local", ["observability/telemetry.py"], [T+"test_runtime_units.py::Telemetry::test_cardinality_guard_and_label_allowlist"], ["M21"]),
 76: ("verified-local", ["service.py", "audit/emitter.py"], [T+"security/test_audit_chain.py::test_every_sensitive_action_audited_and_chain_verifies"], ["M18", "M21"]),
 77: ("partial", ["observability/telemetry.py"], [T+"test_runtime_units.py::Telemetry::test_service_emits_metrics_traces_and_explanations"], ["M21"], "explain records exist; no operator UI"),
 78: ("blocked", [], [], ["M21"], "release lineage / live infrastructure graph live outside this archive"),
 79: ("documented", ["docs/telemetry-policy.md"], [], ["M21"]),
 80: ("partial", ["dashboards/provider-overview.json", "alerts/provider-rules.json"], [T+"monitoring/test_alert_rules.py::test_every_alert_references_emitted_metric"], ["M22"], "not loaded into a real monitoring stack"),
 81: ("verified-local", [T], [T+"test_runtime_units.py::Lifecycle"], []),
 82: ("verified-local", ["conformance/"], [T+"contract/test_golden_vectors.py::test_invalid_fixtures_fail"], ["M24"]),
 83: ("blocked", [T+"integration/"], [T+"integration/test_adjacent_layers.py::test_inv64_manifest_applied_via_inv60"], ["M23"], "real adjacent layers absent"),
 84: ("partial", ["compatibility/matrix.json"], [], ["M28"], "only CPython 3.11/x86_64/linux exercised here"),
 85: ("verified-local", ["fuzz/harness.py"], [T+"security/test_adversarial.py::test_fuzz_smoke_no_crashes"], ["M25"]),
 86: ("verified-local", ["provider.py", "runtime/admission.py"], [T+"test_component.py::ProviderReferenceModelTest::test_parallel_link_updates_do_not_corrupt_state"], []),
 87: ("verified-local", ["docs/threat-model.md"], [T+"security/test_adversarial.py::test_link_confusion_via_separator_injection"], ["M25"]),
 88: ("partial", ["benchmarks/harness.py"], [], ["M27"], "fleet-scale not run"),
 89: ("partial", ["tests/fault/"], [T+"fault/test_failover_splitbrain.py::test_stale_owner_is_fenced_after_takeover"], ["M26"], "partitions simulated via lease clock, not real network"),
 90: ("blocked", ["tools/release_gate.py", "evidence/"], [T+"test_release_tooling.py::test_evidence_chain_verifies"], ["M30"], "100-item pk_core conformance not executable; independent reviewer absent"),
 91: ("partial", ["slo/"], [T+"test_runtime_units.py::Slo"], ["M39"], "support commitments need owner"),
 92: ("verified-local", ["rollout/", "docs/runbooks/rollout-rollback.md"], [T+"integration/test_rollout.py::test_stages_advance_and_complete"], ["M33"]),
 93: ("partial", ["compatibility/matrix.json"], [], ["M28", "M02"], "pk_core version unknown"),
 94: ("documented", ["governance/VULNERABILITY_POLICY.md", "governance/EOL_POLICY.md"], [], ["M34"]),
 95: ("verified-local", ["tools/backup_state.py", "state/migrations.py", "docs/runbooks/backup-restore.md"], [T+"fault/test_state_recovery.py::test_backup_restore_never_resurrects_revoked"], ["M35"]),
 96: ("documented", ["docs/runbooks/day0-day1-day2.md"], [], ["M32"]),
 97: ("documented", ["docs/runbooks/incident-response.md"], [], ["M32"]),
 98: ("partial", ["governance/review-calendar.md"], [], ["M34"], "reviews must actually be held by people"),
 99: ("verified-local", ["governance/waivers.json"], [T+"test_release_tooling.py::test_waivers_have_owner_and_expiry"], ["M34"]),
 100: ("blocked", ["tools/release_gate.py"], [T+"test_release_tooling.py::test_gate_is_not_go"], ["M30"], "production gate cannot be GO: P0 blockers M02/M23 open"),
}


def build() -> dict:
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    rows = []
    for it in items:
        e = R[it["ordinal"]]
        status, impl, tests, mids = e[:4]
        rows.append({"check_id": it["check_id"], "dimension": it["dimension"], "requirement": it["requirement"],
                     "status": status, "implementation": impl, "tests": tests, "missing_components": mids,
                     "blocker": e[4] if len(e) > 4 else None, "owner": "UNASSIGNED", "reviewer": "UNASSIGNED",
                     "waiver": None})
    return {"schema": "PK_RTM/1", "element": "INV-65", "version": (PKG / "VERSION").read_text().strip(), "rows": rows}


if __name__ == "__main__":
    out = PKG / "traceability" / "INV65_RTM.json"
    out.write_text(json.dumps(build(), indent=1) + "\n")
    print(out, file=sys.stderr)
