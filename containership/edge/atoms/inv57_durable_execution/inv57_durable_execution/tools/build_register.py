"""Build STATUS_REGISTER.json (all 82 remediation components) and refresh TRACEABILITY.json.

Status vocabulary (never upgraded by prose):
  CLOSED             every checklist box satisfied, incl. production evidence and approvals. (none yet)
  IMPLEMENTED_LOCAL  code + passing tests in this repository cover the component's in-repo scope;
                     production/integration evidence or approvals are still outstanding.
  PARTIAL            some of the component is implemented and tested; named parts are not.
  BLOCKED            cannot progress without an external input (named in ``blockers``).
  OPEN               no external blocker; simply not done in this pass.

C-item rule: a C-item moves missing→partial only when a mapped component is IMPLEMENTED_LOCAL or
PARTIAL *with* resolving evidence and cited tests.  No C-item is promoted to ``present`` here,
because the checklist's exit gate requires the production acceptance gate and approvals.
"""
from __future__ import annotations

import json
import os
import re

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

T = {  # test id shorthands
    "store": "tests.test_store::StoreTests.",
    "life": "tests.test_store::LifecycleTests.",
    "bk": "tests.test_store::BackupRestoreAndFixtureTests.",
    "crash": "tests.test_crash_boundaries::CrashBoundaryTests.",
    "eff": "tests.test_components::EffectTests.",
    "id": "tests.test_components::IdentityTests.",
    "err": "tests.test_components::ErrorModelTests.",
    "cfg": "tests.test_components::ConfigTests.",
    "res": "tests.test_components::ResilienceTests.",
    "tel": "tests.test_components::TelemetryStatusTests.",
    "gate": "tests.test_components::GateTests.",
    "con": "tests.test_contracts::ContractTests.",
    "prop": "tests.test_property::PropertyTests.",
    "conc": "tests.test_property::ConcurrencyTests.",
    "perf": "tests.test_performance::PerformanceGate.",
    "dur": "tests.test_durable::DurableReplayTest.",
    "r1": "tests.test_review_findings::R1EffectScoping.",
    "r2": "tests.test_review_findings::R2FrozenPayload.",
    "r3": "tests.test_review_findings::R3GateHardening.",
    "r4": "tests.test_review_findings::R4DecoderEscapes.",
    "r5": "tests.test_review_findings::R5EffectCrashBoundaries.",
}


def t(*names):
    out = []
    for n in names:
        k, m = n.split(".", 1)
        out.append(T[k] + m)
    return out


NO_OWNER = "accountable owner/approver not named (OWNERS.yaml unresolved)"
NO_INV50 = "INV-50 state abstraction not supplied"
NO_INV53 = "INV-53 reliable messaging not supplied"
NO_ENV = "target deployment environment (Kubernetes/Dapr/site) not specified or reachable"
NO_KEYS = "no release signing key / trust policy / KMS supplied"
NO_HW = "no edge/target hardware available for measurement"
NO_PK = "pk_core source, version and licence unknown"

C = {}


def comp(cid, status, *, evidence=(), tests=(), done="", remaining="", blockers=()):
    C[cid] = {"status": status, "evidence": list(evidence), "tests": list(tests),
              "done": done, "remaining": remaining, "blockers": list(blockers)}


# ---- Architecture, requirements, semantics --------------------------------------------------
comp("MC-01", "BLOCKED", evidence=["OWNERS.yaml", "acceptance.py::unresolved_owners"],
     done="Ownership schema with roles, L1-L4 escalation, change-approval authorities; gate fails on every empty role.",
     remaining="Fill roles with group identifiers; CODEOWNERS; RACI; service-catalog binding.", blockers=[NO_OWNER])
comp("MC-02", "PARTIAL", evidence=["docs/ARCHITECTURE.md"],
     done="ADR-001 drafted (decision, alternatives, consequences).", remaining="Approval record.", blockers=[NO_OWNER])
comp("MC-03", "PARTIAL", evidence=["docs/ARCHITECTURE.md"], tests=t("store.test_stale_owner_cannot_commit_after_takeover", "crash.test_every_boundary"),
     done="R-01..R-10 SHALL requirements each bound to a test; deployment-context matrix enforced in config.validate.",
     remaining="Stakeholder review/approval.", blockers=[NO_OWNER])
comp("MC-04", "PARTIAL", evidence=["docs/ARCHITECTURE.md", "evidence/benchmark/summary.json"], tests=t("perf.test_1000_event_replay_under_slo"),
     done="NFR table with measured replay/append values on the build machine.",
     remaining="Targets for append latency, availability, RPO/RTO; measurement on target hardware.", blockers=[NO_HW])
comp("MC-05", "IMPLEMENTED_LOCAL", evidence=["lifecycle.py", "sqlite_store.py::SQLiteBackend.control"],
     tests=t("life.test_happy_path_and_log", "life.test_terminal_refuses_and_idempotent_repeat", "life.test_cas_version",
             "life.test_every_table_row_is_reachable_and_unknown_control_refused"),
     done="Closed 11-state machine, idempotent controls, CAS versioning, durable transition log.",
     remaining="Wire lifecycle into Worker.run automatically (currently driven by caller).")
comp("MC-06", "PARTIAL", evidence=["docs/ARCHITECTURE.md"], tests=t("store.test_newer_backend_schema_refused", "bk.test_golden_fixture_replays"),
     done="Versioning policy; backend refuses newer schema; golden history fixture is byte-stable.",
     remaining="Migration tooling N-1→N; policy approval.", blockers=[NO_OWNER])
comp("MC-07", "PARTIAL", evidence=["resilience.py::AdmissionController"], tests=t("res.test_admission_fairness"),
     done="Global and per-tenant in-flight quotas with shedding.", remaining="Capacity model, storage quotas, fairness under load.")
comp("MC-08", "OPEN", remaining="Disconnected/intermittent network semantics not designed; depends on INV-53 wire protocol.",
     blockers=[NO_INV53])
comp("MC-09", "PARTIAL", evidence=["docs/ARCHITECTURE.md"], done="Precedence order drafted with examples.",
     remaining="Approval.", blockers=[NO_OWNER])
# ---- Interfaces -----------------------------------------------------------------------------
comp("MC-10", "IMPLEMENTED_LOCAL", evidence=["schemas/identity.schema.json", "schemas/history_event.schema.json",
     "schemas/error.schema.json", "schemas/status.schema.json", "schemas/config.schema.json", "tools/gen_schemas.py"],
     tests=t("con.test_no_schema_drift", "con.test_documents_conform", "con.test_validator_rejects_bad_documents"),
     done="Boundary inventory + five versioned JSON Schemas generated from code with a drift check.",
     remaining="Schemas for INV-50/INV-53 adapter boundaries (blocked with those layers).")
comp("MC-11", "BLOCKED", evidence=["identity.py::bind_to_principal"], tests=t("id.test_spoofing_rejected"),
     done="Identity binding to an authenticated principal.", remaining="Actual authentication (mTLS/tokens).",
     blockers=["platform identity provider not specified"])
comp("MC-12", "PARTIAL", evidence=["sqlite_store.py::SQLiteBackend.control", "sqlite_store.py::SQLiteBackend.release_quarantine"],
     tests=t("life.test_operator_only_controls", "store.test_tampered_row_quarantines"),
     done="Capability checks (workflow:control, operator) on lifecycle and quarantine release.",
     remaining="Capability issuance/policy engine; per-tenant scoping of capabilities.")
comp("MC-13", "PARTIAL", evidence=["resilience.py", "effects.py", "sqlite_store.py"],
     tests=t("res.test_retry_only_after_backoff_class", "eff.test_crash_after_provider_commit_reconciled_without_duplicate"),
     done="Retry restricted to after_backoff; idempotency via effect ids; backpressure via admission; lease timeouts.",
     remaining="Activity-level timeout enforcement and cooperative cancellation propagation.")
comp("MC-14", "IMPLEMENTED_LOCAL", evidence=["errors.py", "schemas/error.schema.json"],
     tests=t("err.test_codes_unique_and_unsafe_detail_hidden", "con.test_documents_conform"),
     done="21 stable codes, category, retryability, safe-detail flag, HTTP mapping, JSON schema.")
comp("MC-15", "OPEN", remaining="No peer wire protocol yet; cross-version peer behaviour undefined.", blockers=[NO_INV53])
comp("MC-16", "PARTIAL", evidence=["identity.py", "config.py", "durable.py"], tests=t("id.test_rejects_bad_fields", "dur.test_capacity_is_checked_before_user_code_runs"),
     done="Identity field length/charset, history bound, config ranges, log field truncation.",
     remaining="Payload size limits per event and per workflow byte budget.")
comp("MC-17", "PARTIAL", evidence=["fixtures/history_v2_golden.json"], tests=t("bk.test_golden_fixture_replays"),
     done="Versioned golden history fixture replayed byte-stably.", remaining="Fixtures for adapter protocols; published conformance kit.")
comp("MC-18", "BLOCKED", remaining="Adjacent-layer harness (INV-50/53/56/69).", blockers=[NO_INV50, NO_INV53])
# ---- Implementation & configuration ---------------------------------------------------------
comp("MC-19", "PARTIAL", evidence=["pyproject.toml", "VERSION"], tests=t("store.test_history_survives_process_restart_and_replays"),
     done="Pinned package version with single version source; reference persistent backend.", remaining="Pinned production backend.", blockers=[NO_INV50])
comp("MC-20", "PARTIAL", evidence=["config.py", "docs/OPERATIONS.md"], done="Artifact (wheel) / config (ledger dir) / state (state_path DB) are separate paths.",
     remaining="Deployment-level enforcement (read-only artifact FS).", blockers=[NO_ENV])
comp("MC-21", "IMPLEMENTED_LOCAL", evidence=["config.py::validate", "schemas/config.schema.json"],
     tests=t("cfg.test_defaults_valid_and_secure", "cfg.test_rejections"),
     done="Typed schema, unknown-key rejection, ranges, cross-field rules, secure defaults, prod rules.")
comp("MC-22", "IMPLEMENTED_LOCAL", evidence=["config.py::merge_overlays"], tests=t("cfg.test_overlays"),
     done="Ordered overlays validated as a whole.")
comp("MC-23", "IMPLEMENTED_LOCAL", evidence=["config.py::ConfigManager"], tests=t("cfg.test_activation_ledger_and_rollback"),
     done="Hash-chained, fsynced provenance ledger; tamper detected on load.")
comp("MC-24", "IMPLEMENTED_LOCAL", evidence=["config.py::ConfigManager.activate"], tests=t("cfg.test_activation_ledger_and_rollback"),
     done="Validate-before-write, fsync + os.replace atomic swap; rejected config never becomes active.")
comp("MC-25", "PARTIAL", evidence=["config.py::ConfigManager.rollback"], tests=t("cfg.test_activation_ledger_and_rollback"),
     done="Configuration rollback by digest, recorded in ledger.", remaining="Deployment rollback.", blockers=[NO_ENV])
comp("MC-26", "PARTIAL", evidence=["config.py::validate"], tests=t("cfg.test_rejections"),
     done="Inline secrets rejected; secretref:// indirection required in prod.", remaining="Secret provider integration.",
     blockers=["secret provider not specified"])
comp("MC-27", "BLOCKED", evidence=["ci.sh"], done="Deterministic local build/install path.", remaining="Deployment bootstrap.", blockers=[NO_ENV])
# ---- Security -----------------------------------------------------------------------------
comp("MC-28", "PARTIAL", evidence=["docs/ARCHITECTURE.md"], done="Threat table with controls and residual risk.",
     remaining="Formal STRIDE review, sign-off.", blockers=[NO_OWNER])
comp("MC-29", "OPEN", remaining="Least-privilege runtime identity; depends on deployment.", blockers=[NO_ENV])
comp("MC-30", "BLOCKED", remaining="Trust bootstrap for nodes/peers/artifacts.", blockers=[NO_KEYS, NO_ENV])
comp("MC-31", "BLOCKED", remaining="Artifact signature/provenance verification.", blockers=[NO_KEYS])
comp("MC-32", "PARTIAL", evidence=["identity.py", "sqlite_store.py"], tests=t("store.test_tenants_isolated_by_key", "id.test_spoofing_rejected", "id.test_key_injective_and_roundtrip"),
     done="Injective per-tenant keys; principal binding.", remaining="Storage-level isolation / per-tenant encryption.")
comp("MC-33", "BLOCKED", remaining="Encryption at rest and key rotation.", blockers=[NO_KEYS])
comp("MC-34", "PARTIAL", evidence=["status.py"], tests=t("tel.test_status_transitions_and_probe_cache"),
     done="Failed time/dependency probes drop readiness with reason codes.", remaining="Key-service failure behaviour.", blockers=[NO_KEYS])
comp("MC-35", "PARTIAL", evidence=["sqlite_store.py::SQLiteBackend.lifecycle_log", "config.py::ConfigManager"],
     tests=t("life.test_happy_path_and_log", "cfg.test_activation_ledger_and_rollback"),
     done="Durable audit trails for lifecycle controls and config changes.", remaining="Central tamper-evident audit sink.")
comp("MC-36", "PARTIAL", evidence=["tests/test_store.py", "tests/test_property.py"],
     tests=t("store.test_tampered_row_quarantines", "store.test_stale_owner_cannot_commit_after_takeover", "id.test_spoofing_rejected",
             "prop.test_any_single_byte_mutation_of_history_is_detected_or_harmless", "r1.test_foreign_lease_cannot_mark_or_alias_effect",
             "r2.test_payload_cannot_be_mutated_through_events", "r3.test_symlinked_evidence_rejected"),
     done="Tamper, stale-owner, spoofing, mutation-fuzz, cross-workflow effect, in-memory payload mutation, symlink-evidence tests.", remaining="Tests for authn/authz once MC-11 exists.")
# ---- Resilience -----------------------------------------------------------------------------
comp("MC-37", "PARTIAL", evidence=["errors.py", "status.py"], tests=t("err.test_codes_unique_and_unsafe_detail_hidden"),
     done="Failure taxonomy = error registry.", remaining="Stalled-workflow detection.")
comp("MC-38", "IMPLEMENTED_LOCAL", evidence=["resilience.py"],
     tests=t("res.test_retry_only_after_backoff_class", "res.test_retry_bounded", "res.test_circuit", "res.test_admission_fairness"),
     done="Bounded full-jitter retry, circuit breaker with half-open, admission/shedding.")
comp("MC-39", "OPEN", remaining="Failover/degraded-operation model across sites.")
comp("MC-40", "PARTIAL", evidence=["sqlite_store.py"],
     tests=t("store.test_stale_owner_cannot_commit_after_takeover", "store.test_expired_lease_rejects_append_even_without_takeover",
             "store.test_concurrent_acquire_exactly_one_wins", "conc.test_competing_workers_single_owner_no_lost_or_duplicate_appends"),
     done="Lease + epoch fencing inside the append transaction on the reference store.",
     remaining="Fencing in the production store and messaging adapters; multi-host clock skew.", blockers=[NO_INV50, NO_INV53])
comp("MC-41", "PARTIAL", evidence=["sqlite_store.py::SQLiteBackend.quarantine", "status.py"],
     tests=t("store.test_tampered_row_quarantines", "tel.test_status_transitions_and_probe_cache", "crash.test_every_boundary"),
     done="Quarantine with operator release; freeze mode; crash-point fault injection.", remaining="Tenant-wide disable switch.")
# ---- Performance ----------------------------------------------------------------------------
comp("MC-42", "PARTIAL", evidence=["tools/benchmark.py", "evidence/benchmark/summary.json"], tests=t("perf.test_1000_event_replay_under_slo"),
     done="Replay/append baseline with percentiles on the build machine.", remaining="Load matrix, tenant overhead, target hardware.", blockers=[NO_HW])
comp("MC-43", "PARTIAL", evidence=["durable.py::InMemoryHistoryStore.validate"], tests=t("perf.test_replay_scales_linearly"),
     done="Profiled and removed O(n^2) replay (3.7 s → 5 ms p99 at 1000 events).", remaining="Memory bounds per workflow.")
comp("MC-44", "BLOCKED", remaining="Edge power/thermal measurement.", blockers=[NO_HW])
comp("MC-45", "OPEN", remaining="Capacity model and saturation signals.")
comp("MC-46", "IMPLEMENTED_LOCAL", evidence=["tools/benchmark.py", "tests/test_performance.py"],
     tests=t("perf.test_replay_scales_linearly", "perf.test_1000_event_replay_under_slo"),
     done="Regression gate in the test suite plus --baseline comparison in the benchmark.")
# ---- Observability --------------------------------------------------------------------------
comp("MC-47", "IMPLEMENTED_LOCAL", evidence=["status.py", "__main__.py", "schemas/status.schema.json"],
     tests=t("tel.test_status_transitions_and_probe_cache", "con.test_documents_conform"),
     done="Liveness/readiness split, reason codes, cached probes, capability set, CLI view.",
     remaining="HTTP endpoint (deployment).")
comp("MC-48", "PARTIAL", evidence=["telemetry.py"], tests=t("tel.test_metrics_logs_and_redaction"),
     done="Counters/gauges with Prometheus exposition, JSON logs, W3C trace ids.", remaining="Exporter to a real backend.", blockers=[NO_ENV])
comp("MC-49", "PARTIAL", evidence=["telemetry.py", "errors.py"], tests=t("tel.test_metrics_logs_and_redaction", "err.test_codes_unique_and_unsafe_detail_hidden"),
     done="Field allowlist, redaction, hashed tenant refs, error-code decision reasons.", remaining="Explain view, lineage.")
comp("MC-50", "OPEN", remaining="Dashboards/alerts and telemetry governance.", blockers=[NO_ENV])
# ---- Verification -------------------------------------------------------------------------
comp("MC-51", "IMPLEMENTED_LOCAL", evidence=["tests/test_contracts.py"],
     tests=t("con.test_documents_conform", "con.test_validator_rejects_bad_documents", "con.test_no_schema_drift"),
     done="Every public document validated against its schema.")
comp("MC-52", "PARTIAL", evidence=[".github/workflows/ci.yml"], done="CI matrix 3.10-3.12 declared; run here on 3.11 only.",
     remaining="Matrix actually executed.")
comp("MC-53", "IMPLEMENTED_LOCAL", evidence=["tests/test_property.py"],
     tests=t("prop.test_encoding_roundtrip_is_exact_and_canonical", "prop.test_any_single_byte_mutation_of_history_is_detected_or_harmless",
             "prop.test_identity_fuzz_never_crashes_uncontrolled", "prop.test_random_divergence_always_detected",
             "prop.test_replay_equals_first_run_for_random_workflows", "r4.test_wrong_typed_fields", "r4.test_deep_nesting_and_bytes"),
     done="Seeded property/fuzz suite plus review-derived decoder cases (found the baseline KeyError escape and, via review, 3 more escape paths).")
comp("MC-54", "PARTIAL", evidence=["tests/test_property.py", "tests/test_store.py"],
     tests=t("conc.test_competing_workers_single_owner_no_lost_or_duplicate_appends", "store.test_concurrent_acquire_exactly_one_wins"),
     done="Multi-connection contention on the reference store.", remaining="Distributed-state races.", blockers=[NO_INV50])
comp("MC-55", "BLOCKED", remaining="Soak/burst/fleet suites.", blockers=[NO_ENV, NO_HW])
comp("MC-56", "BLOCKED", remaining="Partition/reconnect/control-plane tests.", blockers=[NO_ENV, NO_INV53])
# ---- Release & governance -----------------------------------------------------------------
comp("MC-57", "PARTIAL", evidence=["acceptance.py", "__main__.py", "tools/run_tests.py", "TRUST_POLICY.json"],
     tests=t("gate.test_package_gate_is_no_go_with_reasons", "gate.test_gate_rejects_unresolved_evidence_and_skipped_tests", "gate.test_waivers",
             "r3.test_symlinked_evidence_rejected", "r3.test_forged_everything_with_untrusted_key_is_still_no_go"),
     done="Executable fail-closed gate: evidence digests, skipped≠passed, waiver validity, owner check.",
     remaining="Signed attestation.", blockers=[NO_KEYS])
comp("MC-58", "BLOCKED", remaining="Measured production SLOs.", blockers=[NO_ENV])
comp("MC-59", "BLOCKED", evidence=["docs/OPERATIONS.md"], remaining="Canary/rollout procedures rehearsed.", blockers=[NO_ENV])
comp("MC-60", "BLOCKED", remaining="Patching/vulnerability/EOL policy.", blockers=[NO_OWNER])
comp("MC-61", "PARTIAL", evidence=["sqlite_store.py::SQLiteBackend.backup", "docs/OPERATIONS.md"],
     tests=t("bk.test_backup_restore_verifies_and_fences_old_workers", "bk.test_restore_detects_truncated_backup"),
     done="Online backup, verified restore with external tail manifest and epoch fencing.", remaining="Production-store backup; rehearsal.", blockers=[NO_INV50])
comp("MC-62", "PARTIAL", evidence=["docs/OPERATIONS.md"], done="Day-0/1/2 runbook draft.", remaining="Rehearsal.", blockers=[NO_ENV])
comp("MC-63", "BLOCKED", evidence=["docs/OPERATIONS.md"], done="Severity table draft.", remaining="Paging/escalation targets.", blockers=[NO_OWNER])
comp("MC-64", "BLOCKED", remaining="Recurring review process.", blockers=[NO_OWNER])
comp("MC-65", "PARTIAL", evidence=["WAIVERS.json", "acceptance.py::valid_waiver"], tests=t("gate.test_waivers"),
     done="Waiver ledger schema and validity rules enforced by the gate (0 waivers granted).", remaining="Debt/deprecation entries.", blockers=[NO_OWNER])
# ---- Structural gaps ----------------------------------------------------------------------
comp("SG-01", "PARTIAL", evidence=["sqlite_store.py"],
     tests=t("store.test_history_survives_process_restart_and_replays", "store.test_conditional_append_rejects_out_of_order",
             "store.test_tampered_row_quarantines", "crash.test_every_boundary"),
     done="Backend contract implemented on SQLite: ordered read, conditional append, fencing txn, chain-on-read, quarantine, fsync semantics.",
     remaining="Approved production store; encryption; retention hooks.", blockers=[NO_INV50])
comp("SG-02", "IMPLEMENTED_LOCAL", evidence=["identity.py", "schemas/identity.schema.json"],
     tests=t("id.test_rejects_bad_fields", "id.test_key_injective_and_roundtrip", "id.test_next_run_and_generated", "id.test_spoofing_rejected",
             "prop.test_identity_fuzz_never_crashes_uncontrolled"),
     done="Composite immutable identity, injective key, principal binding, run rollover, fuzzed parser.",
     remaining="Tombstones against id reuse.")
comp("SG-03", "PARTIAL", evidence=["sqlite_store.py"], tests=t("store.test_stale_owner_cannot_commit_after_takeover", "crash.test_every_boundary"),
     done="Fencing on every append/effect mutation in the reference store; multi-process takeover proven.",
     remaining="Production store + messaging.", blockers=[NO_INV50, NO_INV53])
comp("SG-04", "IMPLEMENTED_LOCAL", evidence=["effects.py"],
     tests=t("eff.test_effect_id_stable_and_replay_does_not_resubmit", "eff.test_crash_after_provider_commit_reconciled_without_duplicate",
             "eff.test_unsafe_class_goes_to_operator", "eff.test_request_change_is_nondeterminism",
             "r1.test_foreign_lease_cannot_mark_or_alias_effect", "r5.test_kill_at_every_effect_ledger_commit"),
     done="Effect classes, deterministic ids, prepared-before-dispatch, receipt reconciliation, operator path.",
     remaining="Real provider adapters; receipt lookup timeouts.")
comp("SG-05", "BLOCKED", remaining="INV-50 adapter.", blockers=[NO_INV50])
comp("SG-06", "BLOCKED", remaining="INV-53 adapter.", blockers=[NO_INV53])
comp("SG-07", "OPEN", remaining="Snapshots, compaction, archival.")
comp("SG-08", "PARTIAL", evidence=["lifecycle.py", "sqlite_store.py::SQLiteBackend.control"],
     tests=t("life.test_operator_only_controls", "life.test_cas_version", "life.test_terminal_refuses_and_idempotent_repeat"),
     done="Authorized, durable, idempotent controls with CAS.", remaining="Cancellation propagation into running activities/timers.")
comp("SG-09", "PARTIAL", evidence=["sqlite_store.py::_crash_point", "tests/test_crash_boundaries.py", "tests/test_review_findings.py"],
     tests=t("crash.test_every_boundary", "r5.test_kill_at_every_effect_ledger_commit"),
     done="Real subprocess killed before/after all 6 history commits and all 4 effect-ledger commits; exact recovered state and single real effect verified.",
     remaining="Kill points at lease-renew/lifecycle/config boundaries; power-loss (torn WAL); production-store failover.", blockers=[NO_INV50])
# ---- Repository engineering ---------------------------------------------------------------
comp("RG-01", "BLOCKED", evidence=["tests/test_component.py"], done="pk_core tests skip visibly; the gate never counts a skip.",
     remaining="Pin pk_core.", blockers=[NO_PK])
comp("RG-02", "IMPLEMENTED_LOCAL", evidence=["pyproject.toml", "ci.sh", "evidence/wheel.sha256"], tests=["tests.test_component::PackageMetadataTest.test_version"],
     done="pyproject, single version source, byte-reproducible wheel (two builds compared), installed-wheel tests, clean uninstall.",
     remaining="Supported-platform matrix beyond CPython 3.11/Linux.")
comp("RG-03", "PARTIAL", evidence=["ci.sh", ".github/workflows/ci.yml"], done="Local CI script run end-to-end; hosted workflow checked in.",
     remaining="Pin action SHAs; run on hosted CI; protected release.", blockers=[NO_OWNER])
comp("RG-04", "BLOCKED", remaining="Choose licence; NOTICE.", blockers=["licence choice belongs to the owner"])
comp("RG-05", "BLOCKED", remaining="Deployment manifests.", blockers=[NO_ENV])
comp("RG-06", "BLOCKED", remaining="SBOM/provenance/signing.", blockers=[NO_KEYS])
comp("RG-07", "IMPLEMENTED_LOCAL", evidence=["evidence/benchmark/BUNDLE.json", "evidence/benchmark/raw_samples.json",
     "evidence/benchmark/environment.json", "evidence/benchmark/evaluation.json"], tests=t("perf.test_1000_event_replay_under_slo"),
     done="Versioned bundle with raw samples, env, workload, evaluation and per-file hashes.")
comp("RG-08", "PARTIAL", evidence=["acceptance.py::absent_artifact_claims"], tests=t("gate.test_rg08_claim_check"),
     done="Validation check prevents docs claiming MASTER.md is present.", remaining="Governed retirement decision.", blockers=[NO_OWNER])


def main() -> int:
    mapping = json.load(open(os.path.join(PKG, "tools", "component_map.json")))
    missing = sorted(set(mapping) - set(C))
    if missing:
        raise SystemExit(f"components without a decision: {missing}")
    comps = []
    for cid in mapping:
        comps.append({"id": cid, "title": mapping[cid]["title"], "audit_status_4_2_0": mapping[cid]["audit"],
                      "c_items": mapping[cid]["c"], **C[cid]})
    counts = {}
    for c in comps:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    reg = {"schema": "INV57_STATUS_REGISTER/1", "version": "4.3.0", "counts": counts, "components": comps}
    with open(os.path.join(PKG, "STATUS_REGISTER.json"), "w") as fh:
        json.dump(reg, fh, indent=1)
        fh.write("\n")

    tr_path = os.path.join(PKG, "TRACEABILITY.json")
    tr = json.load(open(tr_path))
    by_c: dict[str, list[dict]] = {}
    for c in comps:
        for ci in c["c_items"]:
            by_c.setdefault(ci, []).append(c)
    for item in tr["items"]:
        cnum = re.search(r"C\d{3}", item["check_id"]).group(0)
        linked = by_c.get(cnum, [])
        item["remediation_components"] = [c["id"] for c in linked]
        if item["status"] == "present":
            continue
        worked = [c for c in linked if c["status"] in ("IMPLEMENTED_LOCAL", "PARTIAL") and c["evidence"] and c["tests"]]
        if worked:
            item["status"] = "partial"
            item["evidence"] = sorted({*item.get("evidence", []), *[e for c in worked for e in c["evidence"]]})
            item["tests"] = sorted({t_ for c in worked for t_ in c["tests"]})
            item["gap"] = "v4.3.0: " + " | ".join(f"{c['id']}: {c['remaining'] or 'production evidence/approval outstanding'}"
                                                  for c in worked)
        elif linked:
            item["gap"] = "v4.3.0: " + " | ".join(
                f"{c['id']} {c['status']}: {'; '.join(c['blockers']) or c['remaining']}" for c in linked)
    counts_c = {}
    for item in tr["items"]:
        counts_c[item["status"]] = counts_c.get(item["status"], 0) + 1
    tr.update(version="4.3.0", audit_date="2026-09-23", counts=counts_c,
              scope="Evidence physically present in the v4.3.0 package. A C-item is 'partial' when a mapped remediation "
                    "component has resolving evidence and cited tests; none is promoted to 'present' without the "
                    "production gate. External pk_core evidence remains unavailable.")
    with open(tr_path, "w") as fh:
        json.dump(tr, fh, indent=1)
        fh.write("\n")
    print(json.dumps({"components": counts, "c_items": counts_c}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
