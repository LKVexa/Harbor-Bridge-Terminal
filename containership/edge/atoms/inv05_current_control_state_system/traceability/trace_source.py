"""Source of the requirements-to-evidence matrix (MC-003).  Edit THIS file, then run
``python traceability/trace_source.py`` to regenerate trace_matrix.json + TRACE_MATRIX.md.
Test references may be class prefixes; they are expanded to exact test ids."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
from inv05_current_control_state_system import tools_check as tc  # noqa: E402

V = tc.version()
OWNER, REVIEWER = "engineering-owner (proposed: D. P. Russell)", "security-owner (to be named)"
D = "docs/"
R = {  # id: (status, impl[], tests[], evidence[], exception)
 "C001": ("verified", ["store.py::ControlStore", "contract.py::build"], ["test_store"], [D+"ARCHITECTURE.md"], None),
 "C002": ("verified", ["contract.py::build"], ["test_component.MetadataTest"], [D+"ARCHITECTURE.md"], None),
 "C003": ("verified", ["contract.py::build", "backend.py::ExternalBackendContract", "replication.py::ReplicationSource"], ["test_backup_repl.ReplicationTest"], [D+"ARCHITECTURE.md"], None),
 "C004": ("verified", ["store.py::ControlStore.revision"], ["test_store.ReadApiTest"], [D+"ARCHITECTURE.md"], None),
 "C005": ("verified", ["store.py::ControlStore"], ["test_chaos"], [D+"ARCHITECTURE.md"], None),
 "C006": ("verified", ["security.py::Namespace", "service.py::ControlStateService._map_key"], ["test_service.IsolationTest"], [D+"ARCHITECTURE.md"], None),
 "C007": ("verified", ["contract.py::build"], ["test_store.TxnTest"], [D+"ARCHITECTURE.md"], None),
 "C008": ("verified", ["config.py::build"], ["test_config_bootstrap.ConfigTest.test_validation_fails_closed"], [D+"ARCHITECTURE.md"], None),
 "C009": ("partial", ["docs/GOVERNANCE.md"], [], [D+"GOVERNANCE.md"], "EX-006"),
 "C010": ("partial", ["docs/adr/ADR-001-scope-and-role.md"], [], [D+"adr/ADR-001-scope-and-role.md", D+"adr/ADR-002-backend-and-consensus.md"], "EX-006"),
 "C011": ("verified", ["store.py::ControlStore.txn"], ["test_store", "test_watch"], [D+"REQUIREMENTS.md"], None),
 "C012": ("verified", ["config.py::SCHEMA"], ["test_config_bootstrap.ConfigTest"], [D+"REQUIREMENTS.md"], None),
 "C013": ("verified-single-member", ["wal.py::DurableStore", "bench.py::run"], ["test_durability", "test_linearizability"], [D+"REQUIREMENTS.md", "evidence/bench_smoke.json"], "EX-001"),
 "C014": ("verified", ["errors.py::ERROR_CATALOG"], ["test_protocol.ErrorModelTest", "test_store.TxnTest.test_failure_branch_executes"], [D+"REQUIREMENTS.md"], None),
 "C015": ("verified", ["service.py::ControlStateService.readiness", "watch.py::Watcher"], ["test_service.ControlsTest", "test_store.DeleteTest", "test_store.LeaseTest"], [D+"ARCHITECTURE.md"], None),
 "C016": ("verified", ["schema.py::check_message"], ["test_protocol.CompatibilityLockTest"], [D+"COMPATIBILITY.md"], None),
 "C017": ("verified", ["limits.py::Limits", "limits.py::TokenBucket"], ["test_service.IsolationTest.test_per_identity_rate_limit", "test_watch.WatchTest.test_quotas"], [D+"REQUIREMENTS.md"], None),
 "C018": ("verified", ["client.py::Mirror"], ["test_http.MTLSEndToEnd.test_mirror_converges_under_writers_and_compaction", "test_http.TokenLoopbackAndShutdown"], [D+"ARCHITECTURE.md"], None),
 "C019": ("verified", ["store.py::ControlStore._commit"], ["test_durability.DurabilityTest.test_io_error_fails_closed_and_never_acks"], [D+"ARCHITECTURE.md"], None),
 "C020": ("verified", ["tools_check.py::check_trace"], ["test_tooling"], ["traceability/trace_matrix.json", "traceability/TRACE_MATRIX.md"], None),
 "C021": ("verified", ["server.py::_Handler"], ["test_http"], [D+"INTERFACES.md"], None),
 "C022": ("verified", ["schema.py::MESSAGES"], ["test_protocol.GoldenTest"], ["conformance/schema_lock.json", "conformance/golden_messages_v1.json"], None),
 "C023": ("verified", ["security.py::MTLSAuthenticator", "security.py::TokenAuthenticator"], ["test_security.MTLSTest", "test_security.TokenTest", "test_http.MTLSEndToEnd.test_no_client_cert_rejected"], [D+"INTERFACES.md"], None),
 "C024": ("verified", ["security.py::Authorizer"], ["test_service.AuthzTest"], [D+"INTERFACES.md"], None),
 "C025": ("verified", ["service.py::OP_CLASSES", "client.py::Client.call", "watch.py::Watcher"], ["test_service.DeadlineTest", "test_http.MTLSEndToEnd.test_client_retries_respect_retry_after_and_budget", "test_watch.WatchTest.test_slow_consumer_falls_back_losslessly"], [D+"INTERFACES.md"], None),
 "C026": ("verified", ["errors.py::StateError"], ["test_protocol.ErrorModelTest"], ["conformance/error_catalog_lock.json"], None),
 "C027": ("verified", ["schema.py::negotiate"], ["test_protocol.NegotiationTest", "test_http.MTLSEndToEnd.test_negotiation_and_schema_errors"], [D+"COMPATIBILITY.md"], None),
 "C028": ("verified", ["limits.py::Limits"], ["test_store.TxnTest.test_limits", "test_fuzz.FuzzTest.test_resource_exhaustion_under_limits"], [D+"INTERFACES.md"], None),
 "C029": ("verified", ["conformance/runner.py::main"], ["test_protocol.ConformanceRunnerTest"], ["conformance/vectors_v1.json", "evidence/conformance.json"], None),
 "C030": ("partial", ["replication.py::ReplicaApplier", "server.py::ControlStateHTTPServer"], ["test_http", "test_backup_repl.ReplicationTest"], [D+"COMPATIBILITY.md"], "EX-004"),
 "C031": ("blocked-external", ["backend.py::ExternalBackendContract"], ["test_config_bootstrap.BackendBoundaryTest"], ["deploy/backend_pin.json", D+"adr/ADR-002-backend-and-consensus.md"], "EX-001"),
 "C032": ("verified", ["config.py::EffectiveConfig", "wal.py::DurableStore"], ["test_config_bootstrap.ConfigTest"], ["deploy/Dockerfile", D+"ROLLOUT.md"], None),
 "C033": ("verified", ["config.py::SCHEMA"], ["test_config_bootstrap.ConfigTest.test_defaults_are_secure"], ["deploy/config/base.json"], None),
 "C034": ("verified", ["config.py::build"], ["test_config_bootstrap.ConfigTest.test_validation_fails_closed"], [], None),
 "C035": ("verified", ["config.py::load_layers"], ["test_config_bootstrap.ConfigTest.test_overlay_precedence_and_provenance"], ["deploy/config/prod.json", "deploy/config/site-a.json"], None),
 "C036": ("verified", ["config.py::EffectiveConfig", "bootstrap.py::build_service"], ["test_config_bootstrap.BootstrapTest"], [], None),
 "C037": ("verified", ["config.py::EffectiveConfig.restart_required_diff", "security.py::Authorizer.rollout"], ["test_config_bootstrap.ConfigTest.test_restart_required_classification_and_redaction", "test_service.AuthzTest.test_policy_rollout_and_rollback"], [], None),
 "C038": ("verified", ["security.py::Authorizer.rollback"], ["test_service.AuthzTest.test_policy_rollout_and_rollback"], [D+"ROLLOUT.md"], None),
 "C039": ("verified", ["security.py::SecretProvider", "security.py::redact"], ["test_security.SecretsTest"], [D+"adr/ADR-005-security.md"], None),
 "C040": ("verified", ["bootstrap.py::build_service"], ["test_config_bootstrap.BootstrapTest"], [D+"operations/RUNBOOK_DAY0.md"], None),
 "C041": ("partial", ["docs/THREAT_MODEL.md"], ["test_security", "test_fuzz"], [D+"THREAT_MODEL.md"], "EX-006"),
 "C042": ("verified", ["security.py::DEFAULT_POLICY"], ["test_service.AuthzTest", "test_fuzz.FuzzTest.test_authz_privilege_boundaries"], ["deploy/inv05.service", "deploy/k8s/statefulset.yaml"], None),
 "C043": ("verified", ["security.py::SecretProvider.get"], ["test_durability.DurabilityTest.test_file_permissions"], ["deploy/inv05.service"], None),
 "C044": ("verified", ["security.py::MTLSAuthenticator.authenticate"], ["test_security.MTLSTest", "test_http.MTLSEndToEnd"], [], None),
 "C045": ("partial", ["backend.py::ExternalBackendContract.verify_artifact", "tools_check.py::manifest"], ["test_config_bootstrap.BackendBoundaryTest.test_pinned_backend_artifact_digest_verification"], ["evidence/gate_report.json"], "EX-008"),
 "C046": ("verified", ["service.py::ControlStateService._map_op"], ["test_service.IsolationTest", "test_fuzz.FuzzTest.test_service_txn_fuzz_never_leaks_or_crashes"], [], None),
 "C047": ("verified", ["wal.py::Sealer", "security.py::server_tls_context"], ["test_durability.DurabilityTest.test_encryption_at_rest_and_key_rotation", "test_http.MTLSEndToEnd.test_server_certificate_rotation_without_restart"], [D+"adr/ADR-005-security.md"], None),
 "C048": ("verified", ["bootstrap.py::build_service"], ["test_config_bootstrap.BootstrapTest.test_bootstrap_refuses_without_keys"], [D+"THREAT_MODEL.md"], None),
 "C049": ("verified", ["audit.py::AuditLog"], ["test_service.AuditTest"], [D+"operations/AUDIT_RETENTION.md"], None),
 "C050": ("verified", ["security.py::TokenAuthenticator"], ["test_fuzz", "test_security.TokenTest.test_forgery_and_replay_to_other_audience"], [D+"THREAT_MODEL.md"], None),
 "C051": ("verified", ["wal.py::DurableStore"], ["test_chaos"], [D+"FAULT_CATALOG.md"], None),
 "C052": ("verified", ["service.py::ControlStateService.liveness"], ["test_service.HealthTest"], ["observability/alerts/inv05-rules.yml"], None),
 "C053": ("verified", ["client.py::Client.call"], ["test_http.MTLSEndToEnd.test_client_retries_respect_retry_after_and_budget"], [], None),
 "C054": ("verified", ["limits.py::ConcurrencyGate", "limits.py::TokenBucket"], ["test_http.TokenLoopbackAndShutdown.test_quota_maps_to_429_with_retry_after"], [], None),
 "C055": ("partial", ["replication.py::ReplicaApplier"], ["test_backup_repl.ReplicationTest.test_stale_epoch_fenced_after_failover"], [D+"DR_PLAN.md"], "EX-001"),
 "C056": ("verified", ["service.py::ControlStateService.readiness"], ["test_service.ControlsTest.test_write_freeze_keeps_reads"], [], None),
 "C057": ("verified", ["wal.py::DurableStore.open"], ["test_durability"], [D+"adr/ADR-004-durability.md"], None),
 "C058": ("verified-single-member", ["store.py::ControlStore.lease_grant"], ["test_store.LeaseTest.test_fencing_blocks_stale_owner", "test_backup_repl.ReplicationTest.test_stale_epoch_fenced_after_failover"], [D+"CONSENSUS_CONTRACT.md"], "EX-001"),
 "C059": ("verified", ["service.py::ControlStateService.quarantine", "service.py::ControlStateService.break_glass"], ["test_service.ControlsTest"], [], None),
 "C060": ("verified", ["wal.py::SimulatedCrash"], ["test_chaos", "test_durability"], [D+"FAULT_CATALOG.md"], None),
 "C061": ("partial", ["bench.py::run"], [], ["evidence/bench_smoke.json", D+"CAPACITY.md"], "EX-005"),
 "C062": ("partial", ["bench.py::run"], [], [D+"CAPACITY.md"], "EX-005"),
 "C063": ("partial", ["bench.py::run"], ["test_fuzz.FuzzTest.test_resource_exhaustion_under_limits"], [D+"CAPACITY.md"], "EX-005"),
 "C064": ("partial", ["limits.py::TokenBucket"], ["test_service.IsolationTest.test_per_identity_rate_limit"], [D+"CAPACITY.md"], "EX-005"),
 "C065": ("verified", ["store.py::ControlStore.range"], [], [D+"CAPACITY.md"], None),
 "C066": ("verified", ["store.py::ControlStore.txn"], ["test_store.TxnTest.test_one_revision_per_txn_and_per_op_results"], [D+"CAPACITY.md"], None),
 "C067": ("verified", ["limits.py::Limits", "watch.py::Watcher"], ["test_watch", "test_fuzz.FuzzTest.test_resource_exhaustion_under_limits"], [], None),
 "C068": ("partial", ["bench.py::run"], [], [D+"CAPACITY.md"], "EX-005"),
 "C069": ("partial", ["observability.py::METRIC_CATALOG"], [], [D+"CAPACITY.md"], "EX-005"),
 "C070": ("verified", ["tools/ci_gate.py"], ["test_tooling"], ["evidence/gate_report.json"], None),
 "C071": ("verified", ["service.py::ControlStateService.version"], ["test_service.HealthTest", "test_http.MTLSEndToEnd.test_health_version_metrics"], [], None),
 "C072": ("verified", ["observability.py::Metrics"], ["test_service.ObservabilityTest.test_metrics_catalog_and_exposition"], [], None),
 "C073": ("verified", ["observability.py::StructuredLogger"], ["test_service.ObservabilityTest.test_structured_log_schema_redaction_and_storm_control"], [], None),
 "C074": ("verified", ["observability.py::Tracer"], ["test_service.ObservabilityTest.test_trace_propagation_and_error_bias"], [], None),
 "C075": ("verified", ["observability.py::Metrics._key"], ["test_service.ObservabilityTest.test_cardinality_cap"], [D+"TELEMETRY_POLICY.md"], None),
 "C076": ("verified", ["observability.py::ExplainStore"], ["test_service.ObservabilityTest.test_explain_record"], [], None),
 "C077": ("verified", ["service.py::ControlStateService.get_explanation"], ["test_service.ObservabilityTest.test_explain_record"], [], None),
 "C078": ("partial", ["service.py::BUILD_INFO"], ["test_service.ObservabilityTest.test_explain_record"], [], "EX-004"),
 "C079": ("verified", ["observability.py::METRIC_CATALOG"], [], [D+"TELEMETRY_POLICY.md"], None),
 "C080": ("partial", ["observability.py::Metrics"], [], ["observability/dashboards/overview.json", "observability/alerts/inv05-rules.yml"], "EX-005"),
 "C081": ("verified", ["store.py::ControlStore"], ["test_store", "test_state"], [], None),
 "C082": ("verified", ["conformance/runner.py::run_file"], ["test_protocol"], ["conformance/vectors_v1.json"], None),
 "C083": ("partial", ["server.py::ControlStateHTTPServer"], ["test_http"], [], "EX-004"),
 "C084": ("partial", ["backend.py::runtime_self_test"], ["test_protocol.NegotiationTest"], [".github/workflows/ci.yml"], "EX-004"),
 "C085": ("verified", ["schema.py::loads"], ["test_fuzz"], [], None),
 "C086": ("verified", ["linearizability.py::check"], ["test_linearizability", "test_store.TxnTest.test_contenders_single_winner"], [], None),
 "C087": ("verified", ["security.py::Authorizer"], ["test_security", "test_fuzz.FuzzTest.test_authz_privilege_boundaries"], [D+"THREAT_MODEL.md"], None),
 "C088": ("partial", ["bench.py::run"], [], ["evidence/bench_smoke.json"], "EX-005"),
 "C089": ("partial", ["replication.py::sync_once", "backup.py::restore_backup"], ["test_backup_repl", "test_http.TokenLoopbackAndShutdown.test_bearer_tokens_and_graceful_drain"], [D+"DR_PLAN.md"], "EX-001"),
 "C090": ("verified", ["tools/ci_gate.py"], ["test_tooling"], ["evidence/gate_report.json"], None),
 "C091": ("verified", ["contract.py::build"], [], [D+"REQUIREMENTS.md", "observability/alerts/inv05-rules.yml"], None),
 "C092": ("verified", ["service.py::ControlStateService.break_glass"], ["test_service.ControlsTest.test_break_glass_is_audited_and_disables_data_plane"], [D+"ROLLOUT.md"], None),
 "C093": ("partial", ["backend.py::SUPPORTED_PYTHON"], [], [D+"COMPATIBILITY.md"], "EX-001"),
 "C094": ("verified", ["tools_check.py::sbom"], [], [D+"SECURITY_POLICY.md"], None),
 "C095": ("verified", ["backup.py::create_backup", "backup.py::restore_backup"], ["test_backup_repl.BackupTest"], [D+"DR_PLAN.md", "evidence/restore_drill.json"], None),
 "C096": ("verified", ["bootstrap.py::main"], [], [D+"operations/RUNBOOK_DAY0.md", D+"operations/RUNBOOK_DAY1.md", D+"operations/RUNBOOK_DAY2.md"], None),
 "C097": ("verified", ["service.py::ControlStateService.quarantine"], [], [D+"operations/INCIDENTS.md"], None),
 "C098": ("partial", ["docs/GOVERNANCE.md"], [], [D+"GOVERNANCE.md"], "EX-006"),
 "C099": ("verified", ["tools_check.py::check_exceptions"], ["test_tooling"], [D+"EXCEPTIONS.json"], None),
 "C100": ("partial", ["tools/release_gate.py"], ["test_tooling"], ["evidence/gate_report.json"], "EX-001"),
}


def expand(refs):
    ids = sorted(tc.test_ids())
    out = []
    for r in refs:
        m = [i for i in ids if i == r or i.startswith(r + ".")]
        if not m:
            raise SystemExit(f"test ref {r} matches nothing")
        out += m
    return sorted(set(out))


def main():
    items = {i["check_id"]: i for i in tc.load_json("CHECKLIST.json")["items"]}
    rows = []
    for cid in items:
        st, impl, tests, ev, ex = R[cid[-4:]]
        rows.append({"id": cid, "requirement": items[cid]["requirement"], "dimension": items[cid]["dimension"],
                     "status": st, "implementation": impl, "tests": expand(tests), "evidence": ev,
                     "owner": OWNER, "reviewer": REVIEWER, "exception": ex or "", "last_verified": V})
    m = {"schema": "cstate.trace/1", "version": V, "rows": rows}
    with open(os.path.join(HERE, "trace_matrix.json"), "w") as fh:
        json.dump(m, fh, indent=1)
    with open(os.path.join(HERE, "TRACE_MATRIX.md"), "w") as fh:
        fh.write(tc.render_trace_md(m))


if __name__ == "__main__":
    main()
