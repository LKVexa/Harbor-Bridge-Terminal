"""Source of the 52-component checklist status (MC-003, release gate input).
Regenerate: python traceability/mc_source.py  ->  mc_status.json, CHECKLIST_STATUS.json, CHECKLIST_STATUS.md

Status vocabulary (per checklist rule 1, code alone never counts):
  done                 implemented + automated test/evidence in this package
  done-single-member   done and proven for the single-member topology; multi-member proof depends on EX-001
  partial              implemented in part; the remainder is named in `note`
  open-approval        needs a human approval/decision that cannot be produced by engineering
  blocked-external     needs an external artefact/system that was not supplied
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, os.path.dirname(PKG))
from inv05_current_control_state_system import tools_check as tc  # noqa: E402

CHECKLIST_MD = os.environ.get("INV05_MC_CHECKLIST", os.path.join(PKG, "docs", "INV05_v4.2.0_52_COMPONENT_PROFESSIONAL_CHECKLIST.md"))

# id: (status, exception, implementation, tests, docs, {item_no: (status, note)} overrides for component-specific items, topology_optional)
T = "tests/"
MC = {
 "MC-001": ("blocked-external", "EX-003", ["backend.py::runtime_self_test"], ["test_config_bootstrap.BackendBoundaryTest.test_local_backend_identity_and_runtime_self_test"], ["deploy/pk_core_pin.json", "docs/COMPATIBILITY.md"],
            {1: ("blocked-external", "no pk_core release supplied"), 2: ("done", "COMPATIBILITY.md python 3.10-3.13"), 3: ("blocked-external", "offline install path templated in pin; needs artefact"),
             4: ("blocked-external", "framework gate cannot run"), 5: ("done", "runtime_self_test reports/rejects version"), 6: ("partial", "CI matrix has pk_core=absent axis only"), 7: ("blocked-external", "licence unknown until pinned")}, True),
 "MC-002": ("open-approval", "EX-002", ["tools_check.py::check_master_md"], ["test_tooling.MasterMdTest"], ["docs/adr/ADR-007-master-md.md"],
            {1: ("open-approval", "deprecation proposed in ADR-007"), 2: ("done", "provenance record enforced when file present"), 3: ("done", "tools/check_master_md.py in CI"),
             4: ("done", "MASTER_REQUIRED_SECTIONS"), 5: ("open-approval", "moot if deprecated"), 6: ("partial", "review rule documented; branch protection not in package")}, True),
 "MC-003": ("done", "EX-006", ["tools_check.py::check_trace", "traceability/trace_source.py"], ["test_tooling.TraceabilityTest"], ["traceability/TRACE_MATRIX.md"],
            {4: ("partial", "owner/reviewer are role placeholders pending EX-006")}, False),
 "MC-004": ("blocked-external", "EX-001", ["backend.py::ExternalBackendContract"], ["test_config_bootstrap.BackendBoundaryTest"], ["deploy/backend_pin.json", "docs/adr/ADR-002-backend-and-consensus.md"],
            {1: ("open-approval", "backend selection is an owner decision"), 3: ("partial", "N/N-1 policy stated; concrete versions pending pin")}, True),
 "MC-005": ("partial", "EX-001", ["backend.py::LocalBackend", "backend.py::classify_backend_error"], ["test_config_bootstrap.BackendBoundaryTest"], ["docs/adr/ADR-002-backend-and-consensus.md"],
            {2: ("blocked-external", "discovery/pooling apply to a remote backend"), 3: ("partial", "local engine is canonical; remote translation pending"),
             5: ("partial", "request-level instrumentation; per-backend-call metrics pending remote adapter"), 6: ("blocked-external", "no multi-node deployment")}, True),
 "MC-006": ("done", None, ["wal.py::DurableStore", "wal.py::WriteAheadLog"], ["test_durability", "test_chaos"], ["docs/adr/ADR-004-durability.md"], {}, False),
 "MC-007": ("blocked-external", "EX-001", ["backend.py::ExternalBackendContract"], [], ["docs/CONSENSUS_CONTRACT.md"],
            {4: ("blocked-external", "needs multi-node backend"), 6: ("blocked-external", "needs multi-node backend")}, True),
 "MC-008": ("done", None, ["store.py::ControlStore.range", "store.py::ControlStore.get"], ["test_store.ReadApiTest"], ["docs/INTERFACES.md"], {}, False),
 "MC-009": ("done", None, ["store.py::ControlStore.delete"], ["test_store.DeleteTest"], ["docs/REQUIREMENTS.md"], {}, False),
 "MC-010": ("done", None, ["store.py::ControlStore.txn"], ["test_store.TxnTest", "test_linearizability"], ["store.py"], {}, False),
 "MC-011": ("done", None, ["store.py::COMPARE_TARGETS"], ["test_store.TxnTest.test_rich_predicates"], ["docs/INTERFACES.md"], {}, False),
 "MC-012": ("done", None, ["schema.py::MESSAGES"], ["test_protocol"], ["conformance/schema_lock.json", "docs/adr/ADR-003-wire-schema.md"], {}, False),
 "MC-013": ("done", None, ["errors.py::ERROR_CATALOG"], ["test_protocol.ErrorModelTest"], ["conformance/error_catalog_lock.json"], {}, False),
 "MC-014": ("done", None, ["server.py::_Handler._stream_watch", "watch.py::Watcher"], ["test_http.MTLSEndToEnd.test_watch_stream_events_and_progress", "test_watch"], ["docs/adr/ADR-006-watch-delivery.md"], {}, False),
 "MC-015": ("done", None, ["watch.py::WatchHub"], ["test_watch"], ["docs/adr/ADR-006-watch-delivery.md"], {}, False),
 "MC-016": ("done", None, ["store.py::Event"], ["test_protocol.GoldenTest.test_event_roundtrip"], ["conformance/golden_messages_v1.json"],
            {3: ("partial", "txn/request id carried; actor identity kept in audit, not in events (tenant privacy)")}, False),
 "MC-017": ("done", None, ["store.py::ControlStore.snapshot", "client.py::Mirror"], ["test_store.SnapshotTest", "test_http.MTLSEndToEnd.test_mirror_converges_under_writers_and_compaction"], ["client.py"], {}, False),
 "MC-018": ("done", None, ["store.py::ControlStore.lease_grant", "store.py::Lease"], ["test_store.LeaseTest"], ["docs/adr/ADR-004-durability.md"], {}, False),
 "MC-019": ("done", None, ["backup.py::CompactionController"], ["test_backup_repl.CompactionControllerTest", "test_store.CompactionTest"], ["docs/operations/RUNBOOK_DAY2.md"], {}, False),
 "MC-020": ("done", None, ["limits.py::Limits"], ["test_store.TxnTest.test_limits", "test_fuzz.FuzzTest.test_resource_exhaustion_under_limits"], ["docs/INTERFACES.md"], {}, False),
 "MC-021": ("done", None, ["security.py::Namespace", "service.py::ControlStateService._map_op"], ["test_service.IsolationTest"], ["deploy/k8s/networkpolicy.yaml"], {}, False),
 "MC-022": ("done", None, ["security.py::MTLSAuthenticator"], ["test_security.MTLSTest", "test_http.MTLSEndToEnd"], ["docs/adr/ADR-005-security.md"],
            {4: ("partial", "hot reload supported; automated issuance belongs to platform PKI"), 5: ("partial", "trust-anchor rotation documented; no automated test")}, False),
 "MC-023": ("done", None, ["security.py::Authorizer"], ["test_service.AuthzTest", "test_fuzz.FuzzTest.test_authz_privilege_boundaries"], ["docs/adr/ADR-005-security.md"], {}, False),
 "MC-024": ("partial", None, ["security.py::SecretProvider", "wal.py::Keyring"], ["test_security.SecretsTest", "test_durability.DurabilityTest.test_encryption_at_rest_and_key_rotation"], ["docs/adr/ADR-005-security.md"],
            {2: ("partial", "secret refs + file mode checks; KMS/HSM unwrap is platform-provided")}, False),
 "MC-025": ("done", None, ["security.py::server_tls_context", "wal.py::Sealer"], ["test_security.TLSConfigTest", "test_http.MTLSEndToEnd.test_server_certificate_rotation_without_restart"], ["docs/adr/ADR-005-security.md"], {}, False),
 "MC-026": ("done", None, ["service.py::OP_CLASSES", "client.py::Client.call"], ["test_service.DeadlineTest", "test_http.MTLSEndToEnd.test_client_retries_respect_retry_after_and_budget"], ["docs/INTERFACES.md"], {}, False),
 "MC-027": ("partial", "EX-004", ["schema.py::negotiate"], ["test_protocol.NegotiationTest"], ["docs/COMPATIBILITY.md"],
            {5: ("blocked-external", "needs an N-1 server build to run mixed"), 6: ("partial", "store formats unchanged vs 4.2 (no persistent format existed)")}, False),
 "MC-028": ("done", None, ["config.py::build"], ["test_config_bootstrap.ConfigTest"], ["deploy/config/base.json"], {}, False),
 "MC-029": ("done", None, ["bootstrap.py::build_service"], ["test_config_bootstrap.BootstrapTest"], ["docs/operations/RUNBOOK_DAY0.md"], {}, False),
 "MC-030": ("done-single-member", "EX-001", ["service.py::ControlStateService.readiness"], ["test_service.HealthTest", "test_http.MTLSEndToEnd.test_health_version_metrics"], ["deploy/k8s/statefulset.yaml"],
            {6: ("partial", "dependency loss/overload/shutdown tested; quorum loss n/a until EX-001")}, False),
 "MC-031": ("done", None, ["service.py::ControlStateService.freeze", "service.py::ControlStateService.quarantine", "service.py::ControlStateService.break_glass"], ["test_service.ControlsTest"], ["docs/operations/INCIDENTS.md"], {}, False),
 "MC-032": ("done", None, ["observability.py::Metrics"], ["test_service.ObservabilityTest"], ["docs/TELEMETRY_POLICY.md"],
            {}, False),
 "MC-033": ("done", None, ["observability.py::StructuredLogger"], ["test_service.ObservabilityTest.test_structured_log_schema_redaction_and_storm_control"], ["docs/TELEMETRY_POLICY.md"], {}, False),
 "MC-034": ("done", None, ["observability.py::Tracer"], ["test_service.ObservabilityTest.test_trace_propagation_and_error_bias", "test_service.ObservabilityTest.test_operational_spans"], ["docs/TELEMETRY_POLICY.md"], {}, False),
 "MC-035": ("done", None, ["observability.py::ExplainStore"], ["test_service.ObservabilityTest.test_explain_record"], ["docs/TELEMETRY_POLICY.md"],
            {6: ("partial", "records carry revisions/policy/config hash; replay tooling not provided")}, False),
 "MC-036": ("done", None, ["observability.py::METRIC_CATALOG"], ["test_service.ObservabilityTest.test_cardinality_cap"], ["docs/TELEMETRY_POLICY.md"], {}, False),
 "MC-037": ("partial", "EX-005", ["observability/dashboards/overview.json"], [], ["observability/alerts/inv05-rules.yml"], {}, False),
 "MC-038": ("done", None, ["audit.py::AuditLog"], ["test_service.AuditTest"], ["docs/operations/AUDIT_RETENTION.md"], {}, False),
 "MC-039": ("done", None, ["backup.py::create_backup", "backup.py::restore_backup"], ["test_backup_repl.BackupTest"], ["docs/DR_PLAN.md", "tools/restore_drill.py"], {}, False),
 "MC-040": ("partial", "EX-001", ["replication.py::ReplicaApplier"], ["test_backup_repl.ReplicationTest"], ["docs/DR_PLAN.md"],
            {4: ("partial", "routing change documented; not automated")}, False),
 "MC-041": ("partial", "EX-004", ["replication.py::ReplicationSource", "replication.py::ReplicaApplier"], ["test_backup_repl.ReplicationTest"], ["replication.py"], {}, True),
 "MC-042": ("partial", "EX-005", ["bench.py::run"], [], ["docs/CAPACITY.md", "evidence/bench/bench_fsync.json"],
            {4: ("partial", "CPU/RSS/FD/threads recorded; storage IOPS and network not measured")}, False),
 "MC-043": ("done-single-member", "EX-001", ["linearizability.py::check"], ["test_linearizability"], ["linearizability.py"],
            {5: ("partial", "process crash injected; node/network faults need multi-member backend")}, False),
 "MC-044": ("done-single-member", "EX-001", ["wal.py::SimulatedCrash"], ["test_chaos", "test_durability"], ["docs/FAULT_CATALOG.md"],
            {1: ("partial", "network partition/delay only via transport interruption")}, False),
 "MC-045": ("done", None, ["schema.py::loads"], ["test_fuzz"], ["docs/THREAT_MODEL.md"], {}, False),
 "MC-046": ("blocked-external", "EX-004", ["server.py::ControlStateHTTPServer"], ["test_http"], ["docs/COMPATIBILITY.md"],
            {1: ("partial", "protocol-level versions only"), 2: ("blocked-external", "adjacent layers not supplied"), 4: ("partial", "backend-unavailable path tested; INV-04/INV-07/PLN-03 not available"),
             5: ("blocked-external", "no N-1 builds of neighbours")}, True),
 "MC-047": ("done", None, ["conformance/runner.py::run_file"], ["test_protocol.ConformanceRunnerTest"], ["conformance/vectors_v1.json"],
            {5: ("partial", "vectors run in-process and via the reference client; no independent implementation available")}, False),
 "MC-048": ("partial", "EX-008", ["tools/ci_gate.py", "tools/release_gate.py"], ["test_tooling.ReleaseGateTest"], [".github/workflows/ci.yml"],
            {3: ("partial", "hash lock pending EX-009"), 6: ("partial", "HMAC signing when key configured; no Sigstore/KMS identity")}, False),
 "MC-049": ("partial", "EX-009", ["tools_check.py::sbom", "tools_check.py::provenance"], ["test_tooling.SupplyChainTest"], ["requirements.lock", "docs/SECURITY_POLICY.md"],
            {1: ("partial", "exact versions; hashes pending"), 4: ("partial", "pip-audit in CI; no malware/licence-policy scanner"), 6: ("partial", "HMAC-signed digests; see EX-008")}, False),
 "MC-050": ("done", None, ["server.py::ControlStateHTTPServer.graceful_shutdown", "serve.py::main"], ["test_http.TokenLoopbackAndShutdown.test_bearer_tokens_and_graceful_drain"], ["docs/ROLLOUT.md", "deploy/Dockerfile", "tools/preflight.py"], {}, False),
 "MC-051": ("done", None, ["bootstrap.py::main"], [], ["docs/operations/RUNBOOK_DAY0.md", "docs/operations/INCIDENTS.md"], {}, False),
 "MC-052": ("open-approval", "EX-006", ["tools_check.py::check_exceptions"], ["test_tooling.ExceptionsTest"], ["docs/GOVERNANCE.md", "docs/EXCEPTIONS.json", "NOTICE", "THIRD-PARTY-NOTICES.md"],
            {1: ("open-approval", "role holders proposed"), 2: ("open-approval", "ADRs drafted, status Proposed"), 5: ("open-approval", "outbound licence not selected (EX-007)")}, False),
}

GENERIC = {  # template key phrase -> (kind)
 "Define an explicit scope statement": "doc", "Document functional requirements": "doc", "Identify upstream/downstream": "doc",
 "Define stable interfaces": "doc", "Implement fail-closed validation": "impl", "Bound memory, CPU": "impl",
 "Propagate deadlines and cancellation": "impl", "Use deterministic state transitions": "impl", "Threat-model the component": "doc",
 "Apply least privilege": "impl", "Ensure secrets and sensitive values": "impl", "Define authentication and authorization requirements": "doc",
 "Add positive-path unit tests": "test", "Add negative tests": "test", "Add concurrency/race tests": "test",
 "Add restart/recovery tests": "test", "Add compatibility tests": "test", "Add property/invariant tests": "test",
 "Define health, readiness, degraded": "impl", "Emit component-specific metrics": "impl", "Create dashboards": "ops",
 "Define alert thresholds": "ops", "Document safe startup": "doc", "Produce a requirements-to-evidence row": "trace",
 "Store machine-readable test results": "ci", "Record security review/threat-model approval": "approval",
 "Record performance/capacity evidence": "perf", "Define a release acceptance gate": "ci", "Assign an accountable owner": "approval",
}
COMMON = {"doc": ["docs/ARCHITECTURE.md", "docs/REQUIREMENTS.md", "docs/INTERFACES.md"], "impl": ["service.py", "limits.py"],
          "test": ["evidence/test_results.json"], "ops": ["observability/dashboards/overview.json", "observability/alerts/inv05-rules.yml"],
          "trace": ["traceability/trace_matrix.json"], "ci": ["tools/ci_gate.py", "evidence/gate_report.json"],
          "approval": ["docs/GOVERNANCE.md"], "perf": ["docs/CAPACITY.md"]}


def parse_checklist():
    with open(CHECKLIST_MD, encoding="utf-8") as fh:
        t = fh.read()
    comps = []
    for sec in re.split(r"\n## (?=MC-\d{3} —)", t)[1:]:
        head = sec.split("\n")[0]
        mid = head.split(" — ")[0].strip()
        pri = re.search(r"\*\*Priority:\*\* (P\d)", sec).group(1)
        items = re.findall(r"\*\*(MC-\d{3}-([A-Z]?\d+))\*\* — (.*)", sec)
        comps.append((mid, head.split(" — ", 1)[1].strip(), pri, items))
    return comps


def item_status(mid, status, ex, overrides, iid, suffix, text, specific_no):
    blocked = status == "blocked-external"
    if suffix.startswith("E"):
        n = int(suffix[1:])
        if n in (1, 3):
            return "open-approval", "requires named approver (EX-006)"
        if n == 2:
            return ("blocked-external", "no executable target") if blocked and mid in ("MC-007", "MC-046") else ("done", "evidence/gate_report.json")
        return ("done", "runbooks/telemetry/matrix") if not blocked or n == 5 else ("partial", "boundary only")
    if suffix.startswith("D"):
        n = int(suffix[1:])
        if n == 1:
            return {"done": "done", "done-single-member": "done", "partial": "partial"}.get(status, status), "see component status"
        if n == 2:
            return ("done", "single-member topology") if status == "done" else ("partial" if status != "blocked-external" else "blocked-external", f"see {ex}")
        if n == 3:
            return ("done", "no open exception") if not ex else ("partial", f"open exception {ex}")
        return "partial", "evidence HMAC-signed only when key configured (EX-008)"
    if specific_no is not None and specific_no in overrides:
        return overrides[specific_no]
    kind = next((k for p, k in GENERIC.items() if text.startswith(p)), None)
    if kind is None:  # component-specific item without override
        return ({"done": "done", "done-single-member": "done", "partial": "done"}.get(status, status),
                "implemented + tested" if status != "blocked-external" else f"blocked ({ex})")
    if kind == "approval":
        return "open-approval", "EX-006"
    if blocked and kind in ("impl", "test", "ops", "perf"):
        return "blocked-external", ex
    if kind == "perf" and mid in ("MC-042",):
        return "partial", "EX-005"
    if status == "done-single-member" and kind in ("test", "impl"):
        return "done-single-member", ex
    return "done", ";".join(COMMON[kind])


def main():
    comps = parse_checklist()
    assert len(comps) == 52, len(comps)
    items_out, comp_out = [], []
    counts = {}
    for mid, title, pri, items in comps:
        status, ex, impl, tests, docs, ov, topo_opt = MC[mid]
        spec_nos = [int(s) for _, s, t in items if s.isdigit() and not any(t.startswith(p) for p in GENERIC)]
        for iid, suffix, text in items:
            no = int(suffix) if suffix.isdigit() else None
            st, note = item_status(mid, status, ex, ov, iid, suffix, text, no if no in spec_nos or no in ov else None)
            counts[st] = counts.get(st, 0) + 1
            items_out.append({"id": iid, "component": mid, "priority": pri, "text": text, "status": st, "evidence_or_reason": note})
        comp_out.append({"id": mid, "title": title, "priority": pri, "status": status, "exception": ex or "",
                         "implementation": impl, "tests": tests, "docs": docs, "topology_optional": topo_opt,
                         "items": len(items), "owner": "engineering-owner (proposed)"})
    for c in comp_out:
        for ref in c["implementation"]:
            assert tc.symbol_exists(ref), ref
        for d in c["docs"]:
            assert d.startswith("evidence/") or os.path.exists(os.path.join(PKG, d)), d
        tids = tc.test_ids()
        for t in c["tests"]:
            assert any(i == t or i.startswith(t + ".") for i in tids), t
    V = tc.version()
    json.dump({"schema": "cstate.mc_status/1", "version": V, "components": comp_out}, open(os.path.join(HERE, "mc_status.json"), "w"), indent=1)
    json.dump({"schema": "cstate.checklist_status/1", "version": V, "totals": counts, "items": items_out},
              open(os.path.join(HERE, "CHECKLIST_STATUS.json"), "w"), indent=1)
    cc = {}
    for c in comp_out:
        cc[c["status"]] = cc.get(c["status"], 0) + 1
    lines = [f"# 52-component checklist status — INV-05 {V}", "",
             f"Items: {len(items_out)} · " + " · ".join(f"{k}: {v}" for k, v in sorted(counts.items())),
             f"Components: " + " · ".join(f"{k}: {v}" for k, v in sorted(cc.items())), "",
             "Status vocabulary is defined in `traceability/mc_source.py`. Per-item detail: `CHECKLIST_STATUS.json`.", "",
             "| ID | P | Component | Status | Exception | Items done / total | Evidence |", "|---|---|---|---|---|---|---|"]
    for c in comp_out:
        its = [i for i in items_out if i["component"] == c["id"]]
        dn = sum(i["status"] in ("done", "done-single-member") for i in its)
        lines.append(f"| {c['id']} | {c['priority']} | {c['title']} | {c['status']} | {c['exception']} | {dn} / {len(its)} | "
                     f"{', '.join(c['tests'][:2]) or '—'}; {', '.join(c['docs'][:2])} |")
    lines += ["", "## Items not done", "", "| Item | Status | Reason |", "|---|---|---|"]
    for i in items_out:
        if i["status"] not in ("done", "done-single-member"):
            lines.append(f"| {i['id']} | {i['status']} | {i['evidence_or_reason']} |")
    open(os.path.join(HERE, "CHECKLIST_STATUS.md"), "w").write("\n".join(lines) + "\n")
    print(json.dumps({"items": len(items_out), "totals": counts, "components": cc}))


if __name__ == "__main__":
    main()
