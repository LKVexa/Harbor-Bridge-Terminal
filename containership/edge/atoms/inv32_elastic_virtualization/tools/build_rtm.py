"""Build RTM.json + CHECKLIST_EXECUTION.md from the INV-32 v4.2.0 missing-components checklist.

Every checklist bullet becomes one RTM row (CL-<ws>-<nnn>) with an honest status:

  IMPLEMENTED  code + automated test in this repository (hosted-CI immutable result still pending, see CL-00-004)
  DOCUMENTED   a definition/specification/procedure artifact exists; nothing executable is required by the item
  PARTIAL      part of the item is implemented and tested; the remainder is named in `note`/`blocker`
  BLOCKED      requires an input this repository cannot supply (named in `blocker`)

Per the checklist's completion rule none of these is "complete": completion additionally needs an immutable
CI result, operational evidence and owner approval (see the Final Definition of Done rows).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "inv32_elastic_virtualization"
CHECKLIST = Path(sys.argv[1])

T = {  # short alias -> test file
    "adp": "test_adapter_contract", "sec": "test_security", "dur": "test_durability", "ctl": "test_controls",
    "rel": "test_release", "mod": "test_model", "pkc": "test_pk_core_compat", "cmp": "test_component",
}


def t(*names: str) -> list[str]:
    out = []
    for n in names:
        a, _, fn = n.partition(":")
        out.append(f"{T[a]}::{fn}")
    return out


B_HYPERFLUX = "HyperFlux specification/version/transport not supplied (ADR-0001); production adapter fails closed"
B_OWNER = "Accountable owners/approvers must be named by the organisation (governance.json owners = null)"
B_CI = "Hosted CI runner + immutable result store not available to this execution (workflow file provided)"
B_HW = "Real hardware classes / disposable test VMs / real hypervisor not available"
B_PKI = "Platform PKI / identity provider / KMS not selected (ADR-0004)"
B_PKCORE = "No released, hash-pinnable pk_core artifact supplied (ADR-0002)"
B_CONSENSUS = "Consensus lease store (etcd/ZooKeeper/Consul) not selected (ADR-0003)"
B_DEPLOY = "Deployment environment (encrypted volume, central audit sink, dashboards backend) not available"
B_GAMEDAY = "Runbooks not yet exercised in a game day (needs a real environment)"
B_LICENSE = "License choice is an owner decision"
B_ADJ = "Adjacent-layer contracts (PLN-05, GAP-10, INV-24) not supplied"

# (ws, subsection) -> spec.  "s": one status letter per bullet (I/D/P/B).
S: dict[tuple, dict] = {}


def sec(ws, sub, s, impl=(), tests=(), docs=(), notes=None, blockers=None):
    S[(ws, sub)] = {"s": s, "impl": list(impl), "tests": list(tests), "docs": list(docs),
                    "notes": notes or {}, "blockers": blockers or {}}


# ---- Engineering evidence convention (meta; applies to every row)
sec("E", None, "IIIBIDPIIB", impl=["RTM.json", "schemas/", "ops/site.example.json", "bench.py"],
    tests=t("rel:test_rtm_is_complete_and_consistent", "ctl:test_check_is_non_mutating_and_machine_readable"),
    docs=["docs/RUNBOOKS.md", "docs/THREAT_MODEL.md", "CHANGELOG.md"],
    notes={6: "threat-model entries exist per control; human security review not performed"},
    blockers={3: B_CI, 6: B_OWNER, 9: B_OWNER})

# ---- WS1
A = ["adapters/base.py", "adapters/fake.py", "adapters/hyperflux.py", "controller.py"]
sec(1, "Architecture and boundary definition", "IIBBPIIIPP", impl=A,
    tests=t("adp:test_capability_negotiation_fails_before_mutation", "adp:test_partial_vcpu_is_compensated",
            "adp:test_cancellation_before_mutation", "adp:test_block_alignment", "adp:test_non_balloonable_and_boot_vcpu_constraints"),
    docs=["docs/ARCHITECTURE.md", "docs/adr/ADR-0001-hyperflux-provider.md"],
    notes={4: "identity mapping defined; provider identifier mapping pending spec",
           8: "NUMA preservation is a provider capability flag only",
           9: "block alignment + non-balloonable + boot vCPU enforced; huge pages/NUMA affinity pending provider"},
    blockers={2: B_HYPERFLUX, 3: B_HYPERFLUX, 4: B_HYPERFLUX, 8: B_HYPERFLUX, 9: B_HYPERFLUX})
sec(1, "Implementation", "PIIIIIIIIIIIIII", impl=A + ["errors.py"],
    tests=t("adp:test_grow_reclaim_uses_hypervisor_confirmed_values", "adp:test_stale_expected_state_rejected",
            "adp:test_concurrent_external_change_between_read_and_write", "adp:test_guest_refusal_is_first_class",
            "adp:test_partial_balloon_records_actual", "adp:test_partial_vcpu_is_compensated",
            "adp:test_provider_invariant_violation_quarantines", "adp:test_raw_provider_error_text_never_exposed",
            "adp:test_capability_change_invalidates_cache_and_is_audited", "adp:test_drain_blocks_new_mutations",
            "adp:test_vcpu_add_remove_and_revert", "adp:test_hyperflux_shell_fails_closed_without_pinned_spec"),
    notes={0: "adapters/hyperflux.py is a fail-closed shell; FakeHypervisor is the deterministic reference adapter"},
    blockers={0: B_HYPERFLUX})
sec(1, "Isolation and safety", "IIIIIIIII", impl=["controller.py", "adapters/base.py"],
    tests=t("adp:test_identifier_reuse_detected", "adp:test_tenant_ownership_checked_against_provider",
            "adp:test_reserve_boundary_uses_confirmed_capacity_including_overhead", "adp:test_untrusted_capacity_fails_closed",
            "adp:test_lifecycle_blocks_mutation", "adp:test_non_balloonable_and_boot_vcpu_constraints",
            "adp:test_grow_reclaim_uses_hypervisor_confirmed_values"))
sec(1, "Verification and acceptance", "IBIIPIIIIPPP", impl=["adapters/fake.py", "bench.py", "compat_matrix.json"],
    tests=t("adp:test_floor_ceiling_boundaries", "adp:test_reserve_boundary_uses_confirmed_capacity_including_overhead",
            "adp:test_block_alignment", "adp:test_guest_refusal_is_first_class", "adp:test_provider_restart_mid_request",
            "adp:test_transient_rpc_failure_is_retried_once_mutated_once", "adp:test_cancellation_before_mutation",
            "adp:test_lifecycle_blocks_mutation", "adp:test_stale_expected_state_rejected", "dur:test_crash_at_every_phase",
            "sec:test_revert_requires_elevation", "dur:test_rollback_records_do_not_cross_epochs",
            "adp:test_capability_change_invalidates_cache_and_is_audited", "rel:test_small_run_emits_reproducible_schema",
            "ctl:test_controller_overload_bounded_no_duplicate_mutations", "rel:test_compat_matrix_and_governance_shape"),
    notes={4: "all lifecycle states tested; topology configurations need a real provider",
           9: "controller-side provider latency measured against the fake only",
           10: "zero reserve/floor violations under concurrent stress on the fake",
           11: "matrix exists; production rows unsupported until provider spec"},
    blockers={1: B_HW, 4: B_HYPERFLUX, 9: B_HYPERFLUX, 10: B_HW, 11: B_HYPERFLUX})

# ---- WS2
sec(2, "Dependency contract", "DDBDPI", impl=["__init__.py", "bootstrap.py"],
    tests=t("pkc:test_symbols", "pkc:test_missing_pk_core_fails_at_activation_with_clear_error", "ctl:test_exit_codes"),
    docs=["docs/adr/ADR-0002-to-0006.md"],
    notes={4: "compat test present; skips until pk_core is installable"}, blockers={2: B_PKCORE, 4: B_PKCORE})
sec(2, "Packaging", "IIPPPIIID", impl=["../pyproject.toml", "__init__.py", "../requirements.lock"],
    tests=t("rel:test_version_single_source", "cmp:test_version_files_are_consistent", "pkc:test_control_plane_imports_without_pk_core"),
    docs=["../RELEASE.md"],
    notes={2: "runtime has zero dependencies; lock pins build backend", 3: "build-backend hashes recorded in lock",
           4: "wheel+sdist built and installed into an empty venv locally (evidence/clean_install.log)"},
    blockers={2: B_CI, 3: B_CI, 4: B_CI})
sec(2, "Deterministic bootstrap", "IIIIID", impl=["bootstrap.py", "release.py"],
    tests=t("ctl:test_check_is_non_mutating_and_machine_readable", "ctl:test_exit_codes", "ctl:test_cli_emits_json"),
    docs=["docs/RUNBOOKS.md"])
sec(2, "Acceptance", "PIII", impl=["../.github/workflows/ci.yml", "release.py"],
    tests=t("pkc:test_control_plane_imports_without_pk_core", "rel:test_sast_and_sbom"),
    notes={0: "executed locally in a fresh venv from the built wheel; hosted CI pending"}, blockers={0: B_CI})

# ---- WS3
V = ["validation.py", "schemas/", "errors.py", "conformance/", "conformance_check.py"]
sec(3, "Schema design", "DIIIIIIIII", impl=V, docs=["docs/adr/ADR-0002-to-0006.md", "docs/INTERFACES.md"],
    tests=t("sec:test_published_vectors_pass", "sec:test_every_error_code_has_retry_class_and_envelope_validates",
            "sec:test_audit_and_host_schemas_validate_live_output", "sec:test_resource_exhaustion_bounded"))
sec(3, "Compatibility", "DIIIDIIP", impl=V, docs=["docs/INTERFACES.md"],
    tests=t("sec:test_published_vectors_pass", "mod:test_legacy_record_cannot_escape_current_bounds"),
    notes={7: "v1 legacy revert + v2 fixtures only; no adjacent v2/v3 pair exists yet"}, blockers={7: "no second supported major exists"})
sec(3, "Interface semantics", "IIIIIDII", impl=["controller.py", "resilience.py", "store.py"], docs=["docs/INTERFACES.md"],
    tests=t("adp:test_cancellation_before_mutation", "dur:test_idempotency_retention_pruning", "ctl:test_tenant_rate_limit",
            "ctl:test_admission_bounds_and_safety_reserve", "dur:test_at_most_one_writer_per_state_version",
            "sec:test_every_error_code_has_retry_class_and_envelope_validates"))
sec(3, "Conformance and fuzzing", "IIIIIBI", impl=V + ["controller.py"],
    tests=t("sec:test_published_vectors_pass", "sec:test_fuzz_decoder", "sec:test_fuzz_controller_never_crashes_or_mutates_on_garbage",
            "sec:test_audit_and_host_schemas_validate_live_output"),
    blockers={5: "only one language implementation exists"})

# ---- WS4
Z = ["authz.py", "controller.py"]
sec(4, "Identity model", "IIPBBII", impl=Z, docs=["docs/adr/ADR-0002-to-0006.md", "docs/THREAT_MODEL.md"],
    tests=t("sec:test_audience_issuer_mismatch_and_forgery", "sec:test_revoked_token_and_principal", "sec:test_revert_requires_elevation",
            "sec:test_expired_credential_with_skew"),
    notes={2: "signed audience-bound credentials implemented; mTLS transport pending"},
    blockers={2: B_PKI, 3: B_PKI, 4: B_HYPERFLUX})
sec(4, "Authorization model", "IPIIIIII", impl=Z,
    tests=t("sec:test_deny_by_default_policy_mutation", "sec:test_wrong_tenant_and_no_existence_leak", "sec:test_wrong_host",
            "sec:test_revert_requires_elevation", "sec:test_break_glass", "sec:test_reason_and_ids_cannot_escalate",
            "ctl:test_manual_quarantine_requires_authz_and_fields"),
    notes={1: "tenant + host scopes enforced; site/environment scopes not modelled"}, blockers={1: "site/environment identity model not supplied"})
sec(4, "Policy enforcement", "IIPIIII", impl=Z,
    tests=t("sec:test_wrong_tenant_and_no_existence_leak", "sec:test_decisions_are_audited", "sec:test_policy_unavailable_fails_closed",
            "sec:test_expired_credential_with_skew", "sec:test_revoked_token_and_principal"),
    notes={1: "no request queue exists; authz, lease and live state are checked immediately before the provider call",
           2: "decision id + request fingerprint + expected version recorded together; not cryptographically bound"},
    blockers={2: B_PKI})
sec(4, "Security verification", "IIIIIID", impl=Z, docs=["../CONTRIBUTING.md"],
    tests=t("sec:test_allow", "sec:test_missing_credential", "sec:test_expired_credential_with_skew", "sec:test_wrong_host",
            "sec:test_revoked_token_and_principal", "sec:test_confused_deputy_controller_chain",
            "sec:test_audience_issuer_mismatch_and_forgery", "sec:test_wrong_tenant_and_no_existence_leak",
            "sec:test_break_glass", "sec:test_deny_by_default_policy_mutation"))

# ---- WS5
C = ["config.py", "controller.py", "bootstrap.py"]
CT = t("ctl:test_every_setting_has_bounds", "ctl:test_rejections", "ctl:test_layer_precedence_conflict_and_emergency_scope",
       "ctl:test_cross_field_invariants", "ctl:test_atomic_activation_rollback_and_audit", "ctl:test_readers_never_see_mixed_config",
       "ctl:test_inspect_hides_secret_values", "dur:test_config_cannot_make_live_state_illegal")
sec(5, "Configuration schema", "IIIIIII", impl=C, tests=CT)
sec(5, "Layering and provenance", "IIIIII", impl=C, tests=CT + t("sec:test_decisions_are_audited"))
sec(5, "Validation and activation", "IIIIIIIIII", impl=C, tests=CT + t("ctl:test_emergency_disable_without_restart"))
sec(5, "Secrets separation", "IPIII", impl=["config.py", "authz.py", "telemetry.py"], tests=CT + t("ctl:test_redaction"),
    notes={1: "SecretResolver resolves secret:// refs at point of use; real secret backend pending"}, blockers={1: B_PKI})
sec(5, "Bootstrap acceptance", "PIII", impl=C, tests=t("ctl:test_check_is_non_mutating_and_machine_readable", "ctl:test_exit_codes",
                                                       "ctl:test_atomic_activation_rollback_and_audit"),
    notes={0: "bootstrap + controller start on an empty directory in tests; real node pending"}, blockers={0: B_HW})

# ---- WS6
ST = ["store.py", "controller.py"]
sec(6, "State inventory", "IIII", impl=["store.py"], tests=t("dur:test_restart_restores_ops_audit_quarantine_state"))
sec(6, "Persistence design", "PIIIIIIBI", impl=ST, docs=["docs/adr/ADR-0002-to-0006.md"],
    tests=t("dur:test_restart_restores_ops_audit_quarantine_state", "dur:test_torn_tail_is_quarantined_not_trusted",
            "dur:test_mid_file_corruption_blocks", "dur:test_state_store_write_failure_never_acknowledges", "dur:test_crash_at_every_phase"),
    notes={0: "single-node store selected; distributed store pending ADR-0003"}, blockers={0: B_CONSENSUS, 7: B_DEPLOY})
sec(6, "Audit hardening", "PPIIIPBPI", impl=ST, docs=["store.py"],
    tests=t("sec:test_decisions_are_audited", "dur:test_audit_rotation_signed_heads_and_linkage", "dur:test_external_anchor_detects_whole_chain_rewrite",
            "dur:test_missing_audit_segment_detected", "dur:test_restart_restores_ops_audit_quarantine_state"),
    notes={0: "authn/authz/policy rejections audited; pre-authentication decode failures are logged+counted, not audited (flood resistance)",
           1: "wall + monotonic time recorded; trusted time source pending", 5: "anchor sink hook implemented; real external sink pending",
           7: "retention defined; legal/privacy constraints pending owner"},
    blockers={0: "design decision pending owner review", 1: B_DEPLOY, 5: B_DEPLOY, 6: B_DEPLOY, 7: B_OWNER})
sec(6, "Crash/restart semantics", "IIIIII", impl=ST,
    tests=t("dur:test_crash_at_every_phase", "dur:test_unknown_outcome_blocks_blind_retry_until_reconciled",
            "dur:test_ambiguous_reconciliation_quarantines", "sec:test_audit_tamper_blocks_mutation"))
sec(6, "Backup, restore, and reconstruction", "DDIIPID", impl=["store.py"], docs=["docs/RUNBOOKS.md", "store.py"],
    tests=t("dur:test_backup_restore_clean_env_and_partial_restore", "dur:test_stale_backup_is_reconciled_before_writes",
            "dur:test_missing_audit_segment_detected", "dur:test_mid_file_corruption_blocks"),
    notes={4: "PITR = restore last backup + re-read live state; journal replay to arbitrary time not supported"},
    blockers={4: "PITR requires a store with point-in-time capability (ADR-0005)"})

# ---- WS7
F = ["fencing.py", "controller.py", "adapters/fake.py"]
FT = t("dur:test_duplicate_controller_startup", "dur:test_stale_controller_cannot_commit_after_takeover",
       "dur:test_delayed_packet_from_stale_epoch_rejected_by_provider", "dur:test_partition_from_lease_store_freezes_writes",
       "dur:test_at_most_one_writer_per_state_version", "dur:test_rollback_records_do_not_cross_epochs", "dur:test_ownership_events_audited",
       "dur:test_crash_at_every_phase")
sec(7, "Ownership model", "IIIIIPI", impl=F, tests=FT, docs=["docs/FAILURE_MODEL.md"],
    notes={5: "planned drain + expiry takeover implemented; forced takeover is a documented operator procedure"},
    blockers={5: B_CONSENSUS})
sec(7, "Mutation safety", "IIIIIII", impl=F, tests=FT)
sec(7, "Partition and failover behavior", "IIDII", impl=F, tests=FT, docs=["docs/FAILURE_MODEL.md"])
sec(7, "Verification", "IIIIII", impl=F, tests=FT)

# ---- WS8
H = ["health.py", "controller.py"]
HT = t("ctl:test_scopes", "ctl:test_global_emergency_keeps_reads_and_audit", "ctl:test_manual_quarantine_requires_authz_and_fields",
       "ctl:test_ttl_expiry_only_when_declared_safe", "ctl:test_watchdog_flags_stall_once", "ctl:test_readiness_false_on_integrity_or_ownership",
       "ctl:test_emergency_disable_without_restart", "dur:test_partition_from_lease_store_freezes_writes")
sec(8, "Health model", "IIIPPP", impl=H + ["config.py"], tests=HT,
    notes={3: "lease renewal is the heartbeat; no separate heartbeat monitor", 4: "threshold configured; guest-agent reporting pending provider",
           5: "admission rejects at saturation; readiness does not flip"},
    blockers={3: B_CONSENSUS, 4: B_HYPERFLUX, 5: "owner decision: should saturation flip readiness"})
sec(8, "Watchdogs and stall handling", "IIIII", impl=H, tests=HT + t("adp:test_provider_invariant_violation_quarantines"))
sec(8, "Quarantine / freeze controls", "IIIIIIIII", impl=H + ["store.py"], tests=HT)
sec(8, "Acceptance", "IIIBD", impl=H, tests=HT, docs=["ops/alerts.json", "docs/RUNBOOKS.md"], blockers={3: B_GAMEDAY})

# ---- WS9
R = ["resilience.py", "controller.py", "errors.py"]
RT = t("ctl:test_retry_bounded_and_respects_deadline_and_classification", "ctl:test_retry_budget_prevents_storm",
       "ctl:test_circuit_breaker_open_half_open_jitter", "ctl:test_admission_bounds_and_safety_reserve", "ctl:test_tenant_rate_limit",
       "ctl:test_controller_overload_bounded_no_duplicate_mutations", "adp:test_transient_rpc_failure_is_retried_once_mutated_once")
sec(9, "Retry taxonomy", "IIIIII", impl=R, tests=RT)
sec(9, "Backpressure and admission", "IIIIIIII", impl=R + ["config.py"], tests=RT)
sec(9, "Circuit breaking", "IIIIP", impl=R, tests=RT, notes={4: "state observable via inventory/metrics/logs; transitions not written to audit"},
    blockers={4: "owner decision: audit circuit transitions"})
sec(9, "Verification", "IIIIII", impl=R, tests=RT)

# ---- WS10
FM = ["docs/FAILURE_MODEL.md"]
sec(10, "Outcome taxonomy", "IIII", impl=["errors.py", "controller.py"], tests=t("sec:test_every_error_code_has_retry_class_and_envelope_validates",
                                                                              "adp:test_partial_balloon_records_actual", "adp:test_partial_vcpu_is_compensated"))
sec(10, "Failure catalog", "DDDD", docs=FM)
sec(10, "Degraded modes", "IIPDPDD", impl=["health.py", "controller.py", "config.py"], docs=FM,
    tests=t("ctl:test_global_emergency_keeps_reads_and_audit", "dur:test_partition_from_lease_store_freezes_writes"),
    notes={2: "LOCAL_SAFE defined; no separate local agent API", 4: "anchors retained locally when sink fails; no EXPORT_DOWN health flag"},
    blockers={2: B_ADJ, 4: B_DEPLOY})
sec(10, "Failover and recovery", "DIIDP", impl=["controller.py", "fencing.py"], docs=FM,
    tests=t("dur:test_stale_controller_cannot_commit_after_takeover", "dur:test_crash_at_every_phase"),
    notes={4: "ownership_acquired + reconciled events recorded; no single 'failover' event with old owner"},
    blockers={4: B_CONSENSUS})
sec(10, "Fault-injection acceptance", "PPIIII", impl=["adapters/fake.py", "release.py"],
    tests=t("dur:test_crash_at_every_phase", "adp:test_provider_restart_mid_request", "dur:test_unknown_outcome_blocks_blind_retry_until_reconciled",
            "dur:test_stale_controller_cannot_commit_after_takeover", "rel:test_evidence_sign_verify_and_gate_fails_closed"),
    notes={0: "11 of 20 catalog failures injected", 1: "invariant asserted for injected cases"}, blockers={0: B_HW, 1: B_HW})

# ---- WS11
BT = t("rel:test_small_run_emits_reproducible_schema", "rel:test_gate_regression_and_waiver_expiry")
sec(11, "Benchmark specification", "BPPPPI", impl=["bench.py"], tests=BT, docs=["docs/PERFORMANCE.md"],
    notes={1: "Python/platform/package recorded", 2: "decision/provider/e2e separated", 3: "cold start recorded", 4: "guest count parameter"},
    blockers={0: B_HW, 1: B_HYPERFLUX, 2: B_HYPERFLUX, 3: B_HW, 4: B_HW})
sec(11, "Latency/throughput objectives", "IIPPII", impl=["bench.py"], tests=BT, docs=["docs/PERFORMANCE.md", "docs/adr/ADR-0001-hyperflux-provider.md"],
    notes={2: "cold start measured; target not approved", 3: "max RSS measured; CPU target not approved"}, blockers={2: B_OWNER, 3: B_OWNER})
sec(11, "Load scenarios", "PIIPIIPPP", impl=["bench.py", "controller.py"], docs=["docs/PERFORMANCE.md"],
    tests=BT + t("ctl:test_controller_overload_bounded_no_duplicate_mutations", "dur:test_at_most_one_writer_per_state_version",
                 "ctl:test_property_caps_floors_reserve", "dur:test_crash_at_every_phase"),
    notes={0: "single load level", 3: "guest creation in fixtures only", 6: "crash recovery only", 7: "rotation in unit tests only",
           8: "reload tested for atomicity without traffic"},
    blockers={0: B_CI, 3: B_CI, 6: B_HW, 7: B_CI, 8: B_CI})
sec(11, "Efficiency analysis", "IPBDIDDI", impl=["store.py", "controller.py", "bench.py"], docs=["docs/PERFORMANCE.md"], tests=BT,
    notes={1: "allocation findings via profiling only"}, blockers={1: B_HW, 2: B_HW})
sec(11, "Capacity model", "DDIDB", impl=["resilience.py"], docs=["docs/PERFORMANCE.md"], tests=t("ctl:test_admission_bounds_and_safety_reserve"),
    blockers={4: B_CI})
sec(11, "Power and thermal", "BBBB", blockers={0: B_HW, 1: B_HW, 2: B_HW, 3: B_ADJ})
sec(11, "CI release gates", "IIII", impl=["bench.py", "../evidence/bench-baseline.json"], tests=BT)

# ---- WS12
TT = t("ctl:test_metric_labels_bounded", "ctl:test_redaction", "ctl:test_logs_structured_and_pseudonymous",
       "ctl:test_traceparent_parse_and_spans", "ctl:test_explain", "ctl:test_inventory")
sec(12, "Health and inventory surfaces", "III", impl=["controller.py", "health.py"], tests=TT + t("ctl:test_readiness_false_on_integrity_or_ownership"))
sec(12, "Metrics", "IIIIII", impl=["telemetry.py", "controller.py"], tests=TT)
sec(12, "Structured logging", "IIIIII", impl=["telemetry.py", "controller.py"], tests=TT)
sec(12, "Distributed tracing", "IPIIII", impl=["telemetry.py", "controller.py"], tests=TT,
    notes={1: "propagated through controller spans; provider hop pending"}, blockers={1: B_HYPERFLUX})
sec(12, "Explainability", "IIIIII", impl=["controller.py", "telemetry.py"], tests=TT)
sec(12, "Retention/privacy/export", "DDDPD", impl=["telemetry.py"], tests=TT, docs=["telemetry.py", "docs/OBSERVABILITY.md"],
    notes={3: "policy defined; export destination not deployed"}, blockers={3: B_DEPLOY})
sec(12, "Dashboards and alerts", "PPPPPDD", impl=["ops/dashboards.json", "ops/alerts.json"], tests=TT, docs=["ops/alerts.json"],
    notes={i: "definition authored; not deployed to a dashboard backend" for i in range(5)}, blockers={i: B_DEPLOY for i in range(5)})

# ---- WS13
sec(13, "Threat model", "DDDDDP", impl=["docs/THREAT_MODEL.md"], docs=["docs/THREAT_MODEL.md"], tests=t("sec:test_decisions_are_audited"),
    notes={5: "residual risk + review date assigned; owner unassigned"}, blockers={5: B_OWNER})
sec(13, "Least privilege and ambient authority removal", "DDDDIII", impl=["release.py", "config.py"], docs=["ops/inv32.service", "docs/THREAT_MODEL.md"],
    tests=t("rel:test_sast_and_sbom", "ctl:test_rejections"))
sec(13, "Artifact and supply-chain trust", "IPPIPPB", impl=["bootstrap.py", "release.py", "adapters/hyperflux.py"],
    tests=t("rel:test_sast_and_sbom", "rel:test_evidence_sign_verify_and_gate_fails_closed", "ctl:test_exit_codes"),
    notes={1: "HMAC-signed manifest; policy/config bundles unsigned", 2: "provider allowlist empty until spec", 4: "no runtime deps; license undecided",
           5: "builder identity env + git commit captured when available"},
    blockers={1: B_PKI, 2: B_HYPERFLUX, 4: B_LICENSE, 5: B_CI, 6: B_CI})
sec(13, "Isolation", "IBIIIIP", impl=["controller.py", "quota.py", "adapters/fake.py"],
    tests=t("sec:test_wrong_tenant_and_no_existence_leak", "ctl:test_property_caps_floors_reserve", "mod:test_free_page_reports_are_bounded",
            "adp:test_identifier_reuse_detected", "adp:test_provider_invariant_violation_quarantines"),
    notes={6: "fake adapter scoped to its guests; real adapter pending"}, blockers={1: B_HYPERFLUX, 6: B_HYPERFLUX})
sec(13, "Encryption and key management", "BBPDPI", impl=["authz.py", "telemetry.py"], docs=["docs/THREAT_MODEL.md", "ops/alerts.json"],
    tests=t("ctl:test_redaction", "sec:test_audience_issuer_mismatch_and_forgery"),
    notes={2: "kid rotation/retire implemented; managed KMS pending", 4: "alert defined; cert exporter pending"},
    blockers={0: B_PKI, 1: B_DEPLOY, 2: B_PKI, 4: B_PKI})
sec(13, "Adversarial testing", "IIIIPBPPII", impl=["authz.py", "validation.py", "store.py"],
    tests=t("sec:test_revert_requires_elevation", "sec:test_wrong_tenant_and_no_existence_leak", "sec:test_fuzz_decoder",
            "sec:test_revoked_token_and_principal", "sec:test_audience_issuer_mismatch_and_forgery", "sec:test_resource_exhaustion_bounded",
            "dur:test_external_anchor_detects_whole_chain_rewrite", "dur:test_fuzz_audit_and_journal_import"),
    notes={4: "controller/credential spoofing tested; node/provider spoofing pending", 6: "IDs/size/queue/tenant table bounded; connection/CPU not",
           7: "identical errors for missing vs foreign guest; timing not measured"},
    blockers={4: B_PKI, 5: B_HYPERFLUX, 6: B_HW, 7: B_HW})

# ---- WS14
sec(14, "Test architecture", "DPID", impl=["tests/_support.py"], docs=["docs/TESTING.md"], tests=t("sec:test_fuzz_decoder"),
    notes={1: "unit/contract/fault/security/fuzz/bench tiers runnable; integration tiers need infra"}, blockers={1: B_HW})
sec(14, "Adjacent-layer integration", "PBBBPP", impl=["controller.py", "adapters/fake.py"],
    tests=t("adp:test_grow_reclaim_uses_hypervisor_confirmed_values", "sec:test_every_error_code_has_retry_class_and_envelope_validates"),
    notes={0: "request flow simulated in-process", 4: "fake dependencies only", 5: "schema major negotiation + error envelope"},
    blockers={0: B_ADJ, 1: B_ADJ, 2: B_ADJ, 3: B_ADJ, 4: B_DEPLOY, 5: B_ADJ})
sec(14, "Compatibility matrix", "BBBPIPBP", impl=["../.github/workflows/ci.yml", "validation.py", "bootstrap.py", "adapters/hyperflux.py"],
    tests=t("sec:test_published_vectors_pass", "adp:test_hyperflux_shell_fails_closed_without_pinned_spec", "ctl:test_exit_codes"),
    notes={3: "CI matrix 3.10-3.13 declared; executed locally on 3.11", 5: "single store format version", 7: "unsupported provider + old Python rejected"},
    blockers={0: B_HW, 1: B_HYPERFLUX, 2: B_HYPERFLUX, 3: B_CI, 5: "only one store version exists", 6: B_CI, 7: B_HYPERFLUX})
sec(14, "Fuzz testing", "IIIIIPP", impl=["validation.py", "store.py"],
    tests=t("sec:test_fuzz_decoder", "sec:test_fuzz_controller_never_crashes_or_mutates_on_garbage", "dur:test_fuzz_audit_and_journal_import"),
    notes={5: "deterministic seeds make every case reproducible; no crash found to minimise", 6: "concurrency test finding (reserve race) converted to regression"},
    blockers={5: "no fuzz crash found yet", 6: "no fuzz crash found yet"})
sec(14, "Fault/disaster testing", "IIIIIIPPBI", impl=["adapters/fake.py", "fencing.py", "store.py"],
    tests=t("dur:test_crash_at_every_phase", "adp:test_provider_restart_mid_request", "dur:test_state_store_write_failure_never_acknowledges",
            "adp:test_raw_provider_error_text_never_exposed", "dur:test_partition_from_lease_store_freezes_writes", "dur:test_fuzz_audit_and_journal_import",
            "sec:test_expired_credential_with_skew", "dur:test_unknown_outcome_blocks_blind_retry_until_reconciled"),
    notes={6: "revocation between requests tested; mid-operation revocation not", 7: "skew window tested; time-service outage not"},
    blockers={6: B_PKI, 7: B_DEPLOY, 8: B_CONSENSUS})
sec(14, "Soak and fleet scale", "BPBPB", impl=["resilience.py", "store.py"],
    tests=t("ctl:test_controller_overload_bounded_no_duplicate_mutations", "dur:test_idempotency_retention_pruning", "ctl:test_property_caps_floors_reserve"),
    notes={1: "bounded structures by construction + pruning", 3: "400-op randomised two-tenant property test"},
    blockers={0: B_CI, 1: B_CI, 2: B_CI, 3: B_CI, 4: B_CI})
sec(14, "Certification evidence", "PPI", impl=["release.py"], tests=t("rel:test_evidence_sign_verify_and_gate_fails_closed"),
    notes={0: "unittest summary JSON per run", 1: "commit/lock/env captured when available"}, blockers={0: B_CI, 1: B_CI})

# ---- WS15
sec(15, "Requirement specification", "D" * 12, docs=["docs/REQUIREMENTS.md"])
sec(15, "Traceability matrix", "IIIIIII", impl=["RTM.json", "release.py", "../tools/build_rtm.py"],
    tests=t("rel:test_rtm_is_complete_and_consistent", "rel:test_rtm_check_catches_defects"))
sec(15, "Acceptance evidence manifest", "IPPPB", impl=["release.py"], tests=t("rel:test_evidence_sign_verify_and_gate_fails_closed"),
    notes={1: "all fields emitted; approvals/provenance empty", 2: "HMAC reference signature", 3: "stored beside local build"},
    blockers={1: B_OWNER, 2: B_PKI, 3: B_CI, 4: B_DEPLOY})
sec(15, "Production exit gate", "I" * 11, impl=["release.py"], tests=t("rel:test_evidence_sign_verify_and_gate_fails_closed"),
    notes={i: "gate check implemented; current result FAIL (see evidence/exit_gate.json)" for i in range(11)})

# ---- WS16
G = ["governance.json", "docs/GOVERNANCE_AND_COMPATIBILITY.md"]
sec(16, "Ownership", "BBDDP", docs=G, notes={4: "cadence defined; deputy unnamed"}, blockers={0: B_OWNER, 1: B_OWNER, 4: B_OWNER},
    impl=["governance.json"], tests=t("rel:test_compat_matrix_and_governance_shape"))
sec(16, "Architecture decision record", "DDDDDDD", docs=["docs/adr/ADR-0001-hyperflux-provider.md", "docs/adr/ADR-0002-to-0006.md"])
sec(16, "Incident management", "DDDDPDDD", docs=G + ["docs/RUNBOOKS.md"], impl=["governance.json"],
    tests=t("rel:test_compat_matrix_and_governance_shape"), notes={4: "owner role assigned; person unnamed"}, blockers={4: B_OWNER})
sec(16, "Recurring governance", "PPPPPPP", impl=["governance.json"], tests=t("rel:test_compat_matrix_and_governance_shape"), docs=G,
    notes={i: "cadence defined; not scheduled in a calendar/ticket system" for i in range(7)}, blockers={i: B_OWNER for i in range(7)})
sec(16, "Exceptions, waivers, and technical debt", "IIDDI", impl=["waivers.json", "tech_debt.json", "release.py", "bench.py"],
    tests=t("rel:test_gate_regression_and_waiver_expiry", "rel:test_evidence_sign_verify_and_gate_fails_closed"), docs=G + ["tech_debt.json"])

# ---- WS17
sec(17, "Version policy", "DDDDD", docs=G)
sec(17, "Matrix", "IIIII", impl=["compat_matrix.json", "release.py"], tests=t("rel:test_compat_matrix_and_governance_shape"))
sec(17, "Mixed-version behavior", "DDDDPI", impl=["adapters/hyperflux.py", "validation.py"], docs=["compat_matrix.json"],
    tests=t("adp:test_hyperflux_shell_fails_closed_without_pinned_spec", "sec:test_published_vectors_pass"),
    notes={4: "provider version allowlist gate; peer versions not negotiated"}, blockers={4: B_HYPERFLUX})
sec(17, "Patching and EOL", "DDDDPD", impl=["bootstrap.py"], docs=G, tests=t("ctl:test_exit_codes"),
    notes={4: "Python floor enforced; matrix-driven EOL check not wired"}, blockers={4: B_OWNER})

# ---- WS18
Q = ["quota.py", "controller.py", "resilience.py"]
QT = t("ctl:test_property_caps_floors_reserve", "ctl:test_borrow_cannot_break_other_guarantee_and_reclaim_order", "ctl:test_tenant_rate_limit",
       "ctl:test_admission_bounds_and_safety_reserve")
sec(18, "Resource model", "PPIIII", impl=Q, tests=QT, notes={0: "guarantee + hard cap; soft target/burst not modelled", 1: "vCPU cap; no vCPU guarantee"},
    blockers={0: "tenant SLA model not supplied", 1: "tenant SLA model not supplied"})
sec(18, "Fairness algorithm", "IIIIIP", impl=Q, tests=QT, docs=["quota.py"], notes={5: "no queue: eligible requests are admitted or rejected immediately"},
    blockers={5: "owner decision: bounded waiting vs reject"})
sec(18, "Control-plane quotas", "IIIPPD", impl=Q + ["model.py"], tests=QT + t("mod:test_free_page_reports_are_bounded"), docs=["docs/INTERFACES.md"],
    notes={3: "payload bounded; report frequency not rate-limited", 4: "explain store bounded; audit query API not exposed"},
    blockers={3: B_HYPERFLUX, 4: "audit query API not in scope"})
sec(18, "Capacity and observability", "PPPBP", impl=Q, tests=QT,
    notes={0: "aggregate refusal metrics only", 1: "guarantee check in quota.py", 2: "unsatisfiable_guarantees() exists; no alert wired",
           4: "randomised many-op test; long-running not"},
    blockers={0: B_DEPLOY, 1: B_OWNER, 2: B_DEPLOY, 3: B_HW, 4: B_CI})
sec(18, "Acceptance", "IIPP", impl=Q, tests=QT, notes={2: "sequential property test", 3: "reject-based admission bounds wait to zero"},
    blockers={2: B_CI, 3: "owner decision"})

# ---- WS19
RB = ["docs/RUNBOOKS.md"]
sec(19, "Day-0 bootstrap runbook", "D" * 11, docs=RB)
sec(19, "Day-1 deployment/rollout runbook", "D" * 9, docs=RB)
sec(19, "Day-2 operations runbook", "D" * 10, docs=RB)
sec(19, "Incident runbooks", "D" * 12, docs=RB)
sec(19, "Runbook quality gate", "DDDDB", docs=RB, blockers={4: B_GAMEDAY})

# ---- WS20
sec(20, "Repository metadata", "BDIDDDI", impl=["../pyproject.toml", "../.gitignore"], tests=t("rel:test_version_single_source"),
    docs=["../CONTRIBUTING.md", "../SECURITY.md", "../RELEASE.md", "../NOTICE"], blockers={0: B_LICENSE})
sec(20, "Code quality gates", "IIPPIPIP", impl=["../pyproject.toml", "release.py", "../.github/workflows/ci.yml"], tests=t("rel:test_sast_and_sbom"),
    notes={2: "ruff import rules; no layered boundary contract", 3: "ruff F-codes only", 5: "no runtime deps; pip-audit step in CI",
           7: "coverage threshold configured (85%); measured locally"},
    blockers={2: "owner decision", 3: "owner decision", 5: B_CI, 7: B_CI})
sec(20, "CI pipeline", "IIPIIIIIIIBI", impl=["../.github/workflows/ci.yml", "release.py", "bench.py"],
    tests=t("rel:test_version_single_source", "sec:test_published_vectors_pass", "rel:test_sast_and_sbom"),
    notes={2: "lock hash checked in CI step", **{i: "step defined in workflow and executed locally" for i in (0, 1, 3, 4, 5, 6, 7, 8, 9, 11)}},
    blockers={2: B_CI, 10: B_HW})
sec(20, "SBOM and provenance", "IIPPPI", impl=["release.py"], tests=t("rel:test_sast_and_sbom", "rel:test_evidence_sign_verify_and_gate_fails_closed"),
    notes={2: "HMAC reference", 3: "HMAC reference", 4: "verify-evidence command"}, blockers={2: B_PKI, 3: B_PKI, 4: B_DEPLOY})
sec(20, "Release regression gates", "IIPIIIII", impl=["release.py", "bench.py"],
    tests=t("rel:test_evidence_sign_verify_and_gate_fails_closed", "rel:test_gate_regression_and_waiver_expiry"),
    notes={2: "SAST gate; no vulnerability feed"}, blockers={2: B_CI})


def parse(md: str):
    ws, sub, prio, controls = None, None, "P0", []
    rows = []
    counters: dict[tuple, int] = {}
    for line in md.splitlines():
        m = re.match(r"^## (\d+)\. (.*)", line)
        if m:
            ws, sub = int(m.group(1)), None
            continue
        if line.startswith("## Engineering evidence"):
            ws, sub = "E", None
            continue
        if line.startswith("## Final Definition of Done"):
            ws, sub = "DOD", None
            continue
        if line.startswith("## "):
            ws = None
            continue
        m = re.match(r"^\*\*Priority:\*\* (\S+)", line)
        if m:
            prio = m.group(1).split("/")[0]
        m = re.match(r"^\*\*Primary audit coverage:\*\* (.*)", line)
        if m:
            ids = re.findall(r"C(\d{3})(?:`?–`?C?(\d{3}))?", m.group(1))
            controls = []
            for a, b in ids:
                rng = range(int(a), int(b) + 1) if b else [int(a)]
                controls += [f"INV-32-C{n:03d}" for n in rng]
        m = re.match(r"^### (.*)", line)
        if m:
            sub = m.group(1)
            continue
        m = re.match(r"^- \[ \] (.*)", line)
        if m and ws is not None:
            key = (ws, sub)
            idx = counters.get(key, 0)
            counters[key] = idx + 1
            rows.append((ws, sub, idx, m.group(1), prio if isinstance(ws, int) else "P0", list(controls) if isinstance(ws, int) else []))
    return rows


def main() -> None:
    md = CHECKLIST.read_text(encoding="utf-8")
    items = parse(md)
    appendix_a = dict(re.findall(r"\| `(INV-32-C\d{3})` \| .*? \| (\d+) \|", md))
    rtm_rows = []
    letters = {"I": "IMPLEMENTED", "D": "DOCUMENTED", "P": "PARTIAL", "B": "BLOCKED"}
    dod_gate = []
    for ws, sub, idx, text, prio, controls in items:
        if ws == "DOD":
            dod_gate.append(text)
            continue
        spec = S[(ws, sub)] if (ws, sub) in S else None
        if spec is None:
            raise SystemExit(f"no spec for {(ws, sub)}")
        if len(spec["s"]) != sum(1 for i in items if i[0] == ws and i[1] == sub):
            raise SystemExit(f"status string length mismatch for {(ws, sub)}")
        st = letters[spec["s"][idx]]
        wsn = 0 if ws == "E" else ws
        rid = f"CL-{wsn:02d}-{sub_slug(sub)}-{idx + 1:02d}"
        row = {"id": rid, "workstream": wsn, "section": sub or "Engineering evidence convention", "text": text,
               "priority": prio, "controls": controls, "status": st}
        if st in ("IMPLEMENTED", "PARTIAL"):
            row["implementation"] = spec["impl"]
            row["tests"] = spec["tests"]
        if spec["docs"] and st in ("DOCUMENTED", "PARTIAL", "IMPLEMENTED"):
            row["docs"] = spec["docs"]
        if idx in spec["notes"]:
            row["note"] = spec["notes"][idx]
        if st in ("BLOCKED", "PARTIAL"):
            row["blocker"] = spec["blockers"].get(idx) or "see note"
        rtm_rows.append(row)
    # requirement rows (REQ-*) from REQUIREMENTS.md
    req_md = (PKG / "docs" / "REQUIREMENTS.md").read_text()
    req_map = {
        "REQ-MEM": (["controller.py"], t("adp:test_floor_ceiling_boundaries", "adp:test_block_alignment", "adp:test_partial_balloon_records_actual")),
        "REQ-CPU": (["controller.py"], t("adp:test_vcpu_add_remove_and_revert", "adp:test_partial_vcpu_is_compensated")),
        "REQ-RBK": (["controller.py", "store.py"], t("dur:test_rollback_records_do_not_cross_epochs", "dur:test_crash_at_every_phase")),
        "REQ-INV": (["controller.py"], t("ctl:test_controller_overload_bounded_no_duplicate_mutations", "ctl:test_property_caps_floors_reserve")),
        "REQ-CTX": (["fencing.py"], t("dur:test_partition_from_lease_store_freezes_writes")),
        "REQ-NFR": (["controller.py", "store.py", "bench.py"], t("rel:test_small_run_emits_reproducible_schema", "dur:test_state_store_write_failure_never_acknowledges")),
        "REQ-OUT": (["errors.py"], t("sec:test_every_error_code_has_retry_class_and_envelope_validates")),
        "REQ-LCY": (["store.py", "controller.py"], t("dur:test_crash_at_every_phase", "adp:test_lifecycle_blocks_mutation")),
        "REQ-QTA": (["quota.py", "resilience.py"], t("ctl:test_property_caps_floors_reserve", "ctl:test_tenant_rate_limit")),
        "REQ-NET": (["fencing.py", "resilience.py"], t("dur:test_partition_from_lease_store_freezes_writes", "ctl:test_circuit_breaker_open_half_open_jitter")),
        "REQ-PRC": (["controller.py"], t("ctl:test_global_emergency_keeps_reads_and_audit")),
    }
    req_controls = {"REQ-MEM": ["INV-32-C011", "INV-32-C012"], "REQ-CPU": ["INV-32-C011"], "REQ-RBK": ["INV-32-C057"],
                    "REQ-INV": ["INV-32-C017"], "REQ-CTX": ["INV-32-C012"], "REQ-NFR": ["INV-32-C013"],
                    "REQ-OUT": ["INV-32-C014"], "REQ-LCY": ["INV-32-C015"], "REQ-QTA": ["INV-32-C017"],
                    "REQ-NET": ["INV-32-C018"], "REQ-PRC": ["INV-32-C019"]}
    for m in re.finditer(r"\*\*(REQ-[A-Z]+-[A-Z0-9]+)\*\* (.*)", req_md):
        rid, text = m.groups()
        fam = rid.rsplit("-", 1)[0]
        impl, tests = req_map[fam]
        blocked = "BLOCKED ADR-0003" in text
        row = {"id": rid, "workstream": 15, "section": "SHALL requirement", "text": text, "priority": "P0",
               "controls": req_controls[fam], "status": "PARTIAL" if blocked else "IMPLEMENTED",
               "implementation": impl, "tests": tests, "docs": ["docs/REQUIREMENTS.md"]}
        if blocked:
            row["blocker"] = B_CONSENSUS
        rtm_rows.append(row)
    # control linkage (Appendix A + B)
    for ctl, wsn in appendix_a.items():
        if not any(ctl in r["controls"] for r in rtm_rows):
            for r in rtm_rows:
                if r["workstream"] == int(wsn):
                    r["controls"] = sorted(set(r["controls"] + [ctl]))
    for ctl in re.findall(r"\| `(INV-32-C\d{3})` \| (?!Audit requirement)", md.split("## Appendix B")[1]):
        if not any(ctl in r["controls"] for r in rtm_rows):
            rtm_rows[-1]["controls"].append(ctl)
    doc = {"schema": "PK_INV32_RTM/1", "source_checklist": CHECKLIST.name, "generated_by": "tools/build_rtm.py",
           "status_legend": {v: k for k, v in letters.items()}, "rows": rtm_rows,
           "definition_of_done": [{"text": d, "status": "NOT MET", "evidence": "evidence/exit_gate.json"} for d in dod_gate]}
    (PKG / "RTM.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False))
    write_report(doc)


def sub_slug(sub: str | None) -> str:
    if not sub:
        return "EVID"
    words = re.findall(r"[A-Za-z0-9]+", sub)
    return "".join(w[0] for w in words).upper()[:5]


def write_report(doc: dict) -> None:
    rows = [r for r in doc["rows"] if r["id"].startswith("CL-")]
    from collections import Counter, defaultdict
    total = Counter(r["status"] for r in rows)
    by_ws: dict[int, Counter] = defaultdict(Counter)
    for r in rows:
        by_ws[r["workstream"]][r["status"]] += 1
    titles = {0: "Engineering evidence convention", 1: "HyperFlux / hypervisor adapter", 2: "pk_core packaging & bootstrap",
              3: "Formal schemas & protocol", 4: "AuthN / AuthZ / capabilities", 5: "Declarative configuration", 6: "Durable state & audit",
              7: "Controller fencing & ownership", 8: "Health, stall, quarantine", 9: "Retry, backpressure, admission", 10: "Failure & failover model",
              11: "Performance & capacity", 12: "Observability", 13: "Security program", 14: "Test program", 15: "Requirements & evidence",
              16: "Ownership & governance", 17: "Version compatibility", 18: "Tenant quota & fairness", 19: "Runbooks", 20: "Release hygiene & CI"}
    out = ["# INV-32 v4.2.0 → v4.3.0 — Checklist execution report", "",
           "Generated from `RTM.json` by `tools/build_rtm.py`. One row per checklist bullet; statuses are deliberately conservative.",
           "Per the checklist's completion rule no bullet is *complete* until an immutable CI result, operational evidence and",
           "owner approval exist; the production exit gate therefore returns **FAIL** (see `evidence/exit_gate.json`).", "",
           f"**Totals ({len(rows)} bullets):** " + ", ".join(f"{k} {total.get(k, 0)}" for k in ("IMPLEMENTED", "DOCUMENTED", "PARTIAL", "BLOCKED")), "",
           "| WS | Workstream | Implemented | Documented | Partial | Blocked |", "|---:|---|---:|---:|---:|---:|"]
    for ws in sorted(by_ws):
        c = by_ws[ws]
        out.append(f"| {ws} | {titles[ws]} | {c['IMPLEMENTED']} | {c['DOCUMENTED']} | {c['PARTIAL']} | {c['BLOCKED']} |")
    blockers = Counter(r["blocker"] for r in rows if r["status"] in ("BLOCKED", "PARTIAL"))
    out += ["", "## What is blocking the remainder", "", "| Blocker | Rows |", "|---|---:|"]
    for b, n in blockers.most_common():
        out.append(f"| {b} | {n} |")
    out += ["", "## Row detail", ""]
    cur = None
    for r in rows:
        key = (r["workstream"], r["section"])
        if key != cur:
            cur = key
            out += ["", f"### WS{r['workstream']} — {r['section']}", ""]
        mark = {"IMPLEMENTED": "✅", "DOCUMENTED": "📄", "PARTIAL": "◐", "BLOCKED": "⛔"}[r["status"]]
        extra = []
        if r.get("note"):
            extra.append(r["note"])
        if r["status"] in ("BLOCKED", "PARTIAL") and r.get("blocker") and r["blocker"] != "see note":
            extra.append("blocked on: " + r["blocker"])
        out.append(f"- {mark} `{r['id']}` {r['text']}" + (f" — _{'; '.join(extra)}_" if extra else ""))
    out += ["", "## Final Definition of Done", ""]
    for d in doc["definition_of_done"]:
        out.append(f"- ⛔ NOT MET — {d['text']}")
    (PKG / "CHECKLIST_EXECUTION.md").write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
