"""Regenerate CHECKLIST_STATUS.json from the checklist markdown + the evidence map below.

Usage: python3 -B tools/build_status.py <PROFESSIONAL_COMPONENT_CHECKLIST.md>
"""
import json
import os
import re
import sys
from collections import Counter

md = open(sys.argv[1], encoding="utf-8").read()
titles = {int(m.group(1)): (m.group(2).strip(), m.group(3))
          for m in re.finditer(r"^## (\d+)\. (.+)$\n\*\*Priority:\*\* (P\d)", md, re.M)}
assert len(titles) == 70, len(titles)
CL = "cluster integration evidence (real API server + gVisor nodes) - none provided"
OWN = "named accountable owner / human approval - owner decision, not Claude's"
S = {}


def put(ns, status, mods, tests, blk):
    for n in ns:
        S[n] = (status, list(mods), list(tests), list(blk))


put([1, 4], "LOCAL_VERIFIED", ["hardening/controls.py::runtime_class", "hardening/runtime.py::RuntimeInventory.check", "hardening/engine.py::Engine._decide"], ["test_h_controls.ControlCases.test_item01_sandbox_runtime", "test_h_engine.Runtime.test_item04_fail_closed_runtime_selection"], [CL, OWN])
put([2], "LOCAL_VERIFIED", ["hardening/runtime.py"], ["test_h_engine.Runtime.test_item02_version_parse_and_minimum"], ["node agent reporting real runsc versions - not provided", OWN])
put([3], "LOCAL_VERIFIED", ["hardening/admission.py"], ["test_h_engine.Adapter.*"], [CL + "; ValidatingWebhookConfiguration never registered", OWN])
for n, t in {5: "test_item05_no_privilege_escalation", 6: "test_item06_host_namespaces", 7: "test_item07_host_devices",
             8: "test_item08_host_mounts", 9: "test_item09_kernel_surface", 10: "test_item10_mac_profile",
             11: "test_item11_uid_resolution", 12: "test_item12_user_namespace", 13: "test_item13_writable_volumes",
             14: "test_item14_resources", 15: "test_item15_network_isolation"}.items():
    put([n], "LOCAL_VERIFIED", ["hardening/controls.py"], [f"test_h_controls.ControlCases.{t}"], [CL, OWN])
S[11][3].insert(0, "image user-database resolver (resolved_uids input) is a host adapter - not provided")
S[15][3].insert(0, "verifying a default-deny NetworkPolicy needs a live cluster; the namespace fact is host-supplied")
put([16, 17], "LOCAL_VERIFIED", ["hardening/engine.py::Engine.reconcile", "hardening/engine.py::Engine.quarantine_plan"], ["test_h_engine.Lifecycle.test_item16_17_drift_and_quarantine"], ["executing the plan against a running workload needs a cluster", OWN])
put([18], "LOCAL_VERIFIED", ["hardening/engine.py::Engine.set_emergency"], ["test_h_engine.Lifecycle.test_item18_emergency_deny_all"], [OWN])
put([19], "LOCAL_VERIFIED", ["schemas/*.schema.json", "hardening/baseline.py::validate_document"], ["test_h_schemas.*", "test_h_integrity.Baselines.test_item19_document_validation_fails_closed"], [OWN])
put([20], "LOCAL_VERIFIED", ["hardening/baseline.py::sign_baseline/verify_signed"], ["test_h_integrity.Baselines.test_item20_signature_and_tamper"], ["HMAC keyring only; asymmetric signing + signer identity via KMS/PKI is item 35", OWN])
put([21, 22], "LOCAL_VERIFIED", ["hardening/baseline.py::BaselineStore"], ["test_h_integrity.Baselines.test_item21_22_atomic_activation_cache_and_rollback", "test_h_certification.Concurrency.test_item50_concurrent_rollout_single_winner"], ["fleet-wide distribution transport not provided", OWN])
put([23, 24, 25], "LOCAL_VERIFIED", ["hardening/authority.py::ExceptionStore"], ["test_h_integrity.Authority.*"], ["replicated store backend not provided (single-node ledger file)", OWN])
put([26], "LOCAL_VERIFIED", ["hardening/core.py::TrustedClock"], ["test_h_integrity.TimeAndAudit.test_item26_*"], ["real NTP/roughtime reference source not bound", OWN])
put([27, 28], "LOCAL_VERIFIED", ["hardening/baseline.py::resolve_settings"], ["test_h_integrity.Baselines.test_item27_28_overlays_only_tighten"], ["precedence against residency/SLO/cost policy needs the GAP-13 policy engine - not provided", OWN])
put([29], "LOCAL_VERIFIED", ["hardening/baseline.py::migrate"], ["test_h_integrity.Baselines.test_item29_migration"], [OWN])
put([30, 31, 36], "LOCAL_VERIFIED", ["hardening/integrations.py::VerdictGate"], ["test_h_engine.Integrations.test_items30_31_36_verdicts"], ["no real attestor/scanner/provenance source bound", OWN])
put([32], "LOCAL_VERIFIED", ["hardening/controls.py::seccomp", "hardening/baseline.py (seccomp_profiles digests)"], ["test_h_controls.ControlCases.test_item32_localhost_seccomp_needs_registered_profile"], ["node-side profile file digest check needs a node agent", OWN])
put([33, 34], "LOCAL_VERIFIED", ["hardening/authority.py::Authenticator/Authorizer"], ["test_h_integrity.Authority.test_item33_authentication", "test_h_integrity.Authority.test_item34_authorization"], ["IdP binding not provided; directory is empty by design", OWN])
put([35], "BLOCKED", [], [], ["no KMS supplied; encryption at rest and key rotation cannot be evidenced", OWN])
put([37], "LOCAL_VERIFIED", ["hardening/integrations.py::ids_finding_to_action"], ["test_h_engine.Integrations.test_item37_ids_to_quarantine"], ["no IDS feed bound", OWN])
put([38], "LOCAL_VERIFIED", ["hardening/core.py::AuditLedger"], ["test_h_integrity.TimeAndAudit.test_item38_*"], ["external head anchoring (WORM / transparency log) not provided", OWN])
put([39, 40, 41, 42, 43], "LOCAL_VERIFIED", ["hardening/telemetry.py", "hardening/engine.py"], ["test_h_engine.Observability.*"], ["no metrics/log/trace backend bound", OWN])
put([44, 45], "PARTIAL", ["hardening/telemetry.py::RETENTION_POLICY/ALERT_RULES"], ["test_h_engine.Observability.test_items44_45_policy_and_alert_rules_are_data"], ["retention numbers PROPOSED, need owner approval", "dashboards need a monitoring backend", OWN])
put([46], "BLOCKED", ["__init__.py (degrades cleanly without pk_core)"], ["test_component.* (3 SKIP: pk_core absent)"], ["pk_core not supplied and not published; cannot be pinned or run"])
put([47], "BLOCKED", ["hardening/admission.py (unit + local HTTP end-to-end only)"], [], [CL])
put([48], "BLOCKED", [], [], ["no kernel/containerd/gVisor/architecture matrix available"])
put([49], "LOCAL_VERIFIED", ["tests/test_h_certification.py::Fuzz", "fixtures/"], ["test_h_certification.Fuzz.*"], ["coverage-guided fuzzing (atheris) not run", OWN])
put([50, 51], "LOCAL_VERIFIED", ["tests/test_h_certification.py"], ["test_h_certification.Concurrency.*", "test_h_certification.Adversarial.*"], ["side-channel scenarios need a real runtime", OWN])
put([52, 53], "PARTIAL", ["tests/test_h_certification.py::Performance/Faults"], ["test_h_certification.Performance.*", "test_h_certification.Faults.*"], ["soak/fleet/partition experiments need a fleet", OWN])
put([54], "PARTIAL", ["tools/release_gate.py", "RELEASE_GATE.json"], ["tools/release_gate.py"], ["gate record is generated but carries no human signature", OWN])
put([55], "BLOCKED", ["docs/OWNERSHIP.md (UNASSIGNED)"], [], [OWN])
put([56], "BLOCKED", ["docs/ADR-0001-sandbox-runtime.md (PROPOSED draft)"], [], ["the ADR must be approved by an accountable owner"])
put([57, 59, 60], "PARTIAL", ["docs/PATCHING_SLA.md", "docs/RUNBOOKS.md", "docs/INCIDENT_PLAYBOOK.md"], [], ["drafts PROPOSED; cluster-side commands unverified without a cluster", OWN])
put([58], "PARTIAL", ["docs/BACKUP_RESTORE.md", "hardening/authority.py (store rebuilds from ledger)"], ["test_h_integrity.Authority.test_item23_store_rebuilds_from_ledger", "test_h_certification.Faults.test_item53_restart_recovers_state"], ["restore drill on production storage not run", OWN])
put([61], "PARTIAL", ["tools/recurring_review.py"], ["tools/recurring_review.py"], ["scheduling and reviewer assignment are owner decisions"])
put([62], "LOCAL_VERIFIED", ["hardening/authority.py::ExceptionStore.registry/sweep"], ["test_h_integrity.Authority.test_item25_ttl_renewal_sweep"], ["expiry dashboard needs a monitoring backend", OWN])
put([63], "LOCAL_VERIFIED", ["hardening/integrations.py::Rollout"], ["test_h_engine.Integrations.test_item63_rollout"], [CL, OWN])
put([64], "LOCAL_VERIFIED", ["pyproject.toml"], ["pip install . (CI)"], ["pk_core extra cannot resolve (item 46)"])
put([65], "PARTIAL", ["requirements-dev.txt"], [], ["runtime has zero dependencies; dev tools pinned by version but not hash-locked"])
put([66, 67], "LOCAL_VERIFIED", [".github/workflows/ci.yml", "pyproject.toml [tool.ruff]/[tool.mypy]"], ["ruff check", "mypy", "tools/mutation_probe.py"], ["CI has never run on a hosted runner"])
put([68], "LOCAL_VERIFIED", ["fixtures/valid", "fixtures/invalid"], ["test_h_certification.Fuzz.test_item49_fixture_corpus"], [])
put([69], "BLOCKED", [], [], ["MASTER.md was never supplied; not synthesised"])
put([70], "PARTIAL", ["sbom.cdx.json", "THIRD-PARTY-NOTICES.md"], [], ["no LICENSE: the owner must choose one"])
assert sorted(S) == list(range(1, 71)), set(range(1, 71)) - set(S)
items = [{"n": n, "title": titles[n][0], "priority": titles[n][1], "status": S[n][0], "implemented_by": S[n][1],
          "tests": S[n][2], "blockers": S[n][3], "complete": False} for n in range(1, 71)]
doc = {"schema": "INV03_CHECKLIST_STATUS/1", "package_version": "4.3.0",
       "checklist": "PROFESSIONAL_COMPONENT_CHECKLIST 1.0.0 (70 components)",
       "status_meaning": {
           "LOCAL_VERIFIED": "implemented in this archive and exercised by passing tests here; checklist completion still needs the integration/ownership evidence named in blockers",
           "PARTIAL": "some artefact exists but at least one mandatory evidence class is missing",
           "BLOCKED": "nothing honest can be produced without an input this archive does not have"},
       "completion_rule": "complete=true only with every evidence class in the checklist's 'Required evidence package' present AND an independent human approval record; none exist, so 0/70 complete",
       "counts": dict(Counter(i["status"] for i in items)), "complete": 0, "items": items}
out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "CHECKLIST_STATUS.json")
with open(out, "w") as fh:
    json.dump(doc, fh, indent=1)
print(doc["counts"])
