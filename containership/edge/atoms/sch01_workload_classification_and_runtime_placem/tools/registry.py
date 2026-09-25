"""Single source of truth: what this pass built for each MC/EXT component, which executed
test classes evidence it, and what still blocks completion.  Consumed by rtm.py,
checklist_status.py, evidence_bundle.py and exit_gate.py.

State vocabulary (never merged):
  IMPLEMENTED_TESTED    code present + named test classes executed and passing in this run
  DRAFTED_UNAPPROVED    document/policy artifact present; requires an accountable approver
  BLOCKED_EXTERNAL      needs something not in this archive (real adjacent element, fleet, KMS, ...)
  BLOCKED_SOURCE        needs source evidence that does not exist here
No component is COMPLETE: every definition of done requires a named owner and approver
(Dxx.D01), and OWNERS.json is deliberately UNASSIGNED.
"""
T = "IMPLEMENTED_TESTED"; D = "DRAFTED_UNAPPROVED"; X = "BLOCKED_EXTERNAL"; S = "BLOCKED_SOURCE"
tg, ts, tr, tc, te = ("tests/test_governed_placement.py", "tests/test_security.py",
                      "tests/test_resilience_state.py", "tests/test_contracts_integration.py", "tests/test_engine.py")
tt = "tests/test_tooling.py"

R = {
 "MC-01": (S, ["tools/verify_master_provenance.py", "evidence/master_provenance.json"], [f"{tt}::ProvenanceTest"],
           "canonical MASTER.md not supplied; verifier reports EVIDENCE_GAP; waiver needs an approver"),
 "MC-02": (T, ["pyproject.toml", "requirements.lock"], [f"{tt}::PackagingTest"], "wheel build/sign on a release host not run"),
 "MC-03": (D, ["governance/OWNERS.json"], [f"{tt}::GovernanceTest"], "owner, backup, escalation and on-call are UNASSIGNED"),
 "MC-04": (D, ["docs/adr/ADR-0001-governed-placement-path.md", "docs/adr/ADR-0002-fencing-and-journal.md", "docs/adr/ADR-0003-fail-closed-isolation.md"],
           [f"{tt}::GovernanceTest"], "ADRs are PROPOSED; approver UNASSIGNED"),
 "MC-05": (D, ["governance/SHALL.json"], [f"{tt}::ShallTest"], "requirements need owner sign-off"),
 "MC-06": (T, ["tools/rtm.py", "evidence/RTM.json"], [f"{tt}::RtmTest"], "RTM rows carry owner UNASSIGNED"),
 "MC-07": (T, ["model.py", "scheduler.py"], [f"{tg}::DeploymentContextTest"], "context semantics need owner approval"),
 "MC-08": (T, ["lifecycle.py"], [f"{tr}::LifecycleTest"], ""),
 "MC-09": (T, ["lifecycle.py", "docs/COMPATIBILITY.md"], [f"{tr}::LifecycleTest"], "support policy unapproved"),
 "MC-10": (T, ["allocators.py"], [f"{tg}::QuotaFairShareTest"], "quota values are policy decisions; none approved"),
 "MC-11": (T, ["scheduler.py", "model.py"], [f"{tg}::RuntimeSelectorTest"], ""),
 "MC-12": (T, ["scheduler.py"], [f"{tg}::LatencyAwareTest"], "latency budget value PROPOSED"),
 "MC-13": (T, ["scheduler.py"], [f"{tg}::TopologyTest"], "no GAP-03 topology graph (EXT-06); zone-level only"),
 "MC-14": (T, ["scheduler.py", "model.py"], [f"{tg}::ResidencyDataPathTest"], "jurisdiction policy source not bound"),
 "MC-15": (T, ["allocators.py"], [f"{tg}::AcceleratorTest"], "MIG/partition health from real devices not bound"),
 "MC-16": (T, ["config.py"], [f"{tr}::ConfigTest", f"{ts}::AdversarialTest"], "signing key is test-generated; no policy owner"),
 "MC-17": (T, ["schemas.py", "schemas/", "tools/gen_schemas.py"], [f"{tc}::SchemaContractTest"], ""),
 "MC-18": (T, ["errors.py"], [f"{tr}::ErrorContractTest"], ""),
 "MC-19": (T, ["security.py"], [f"{ts}::AuthenticationTest"], "no real IdP/mTLS; HMAC mechanism only"),
 "MC-20": (T, ["security.py"], [f"{ts}::AuthorizationTest"], "role bindings to real principals absent"),
 "MC-21": (T, ["resilience.py"], [f"{tr}::RequestContractTest"], ""),
 "MC-22": (T, ["config.py"], [f"{tr}::ConfigTest"], ""),
 "MC-23": (T, ["config.py"], [f"{tr}::ConfigTest"], ""),
 "MC-24": (X, ["security.py"], [f"{ts}::SecretsTest"], "provider interface + fail-closed tested; no KMS/HSM bound"),
 "MC-25": (X, ["security.py"], [f"{ts}::AttestationTest"], "HMAC evidence verifier only; TPM/SEV/TDX quote verification is GAP-02/EXT-04"),
 "MC-26": (T, ["model.py", "scheduler.py"], [f"{tg}::OccupancyIsolationTest"], ""),
 "MC-27": (T, ["audit.py"], [f"{ts}::AuditLedgerTest"], "sealing key test-generated; external anchoring of head absent"),
 "MC-28": (T, ["tests/test_security.py"], [f"{ts}::AdversarialTest"], "side channels and escape are out of scope of a decision function; not tested"),
 "MC-29": (T, ["resilience.py"], [f"{tr}::OperatorAndFaultTest"], "thresholds PROPOSED"),
 "MC-30": (T, ["resilience.py"], [f"{tr}::RequestContractTest"], "failover across instances needs EXT consensus"),
 "MC-31": (T, ["state.py"], [f"{tr}::DurableStateTest"], ""),
 "MC-32": (X, ["state.py"], [f"{tr}::FencingRaceTest"], "single-host file fencing tested; multi-host linearizable store not bound"),
 "MC-33": (T, ["scheduler.py"], [f"{tr}::OperatorAndFaultTest"], ""),
 "MC-34": (T, ["tests/test_resilience_state.py"], [f"{tr}::OperatorAndFaultTest", f"{tr}::DurableStateTest"], "partition/controller loss only simulated in-process"),
 "MC-35": (T, ["tools/bench.py", "evidence/bench.json"], [f"{tt}::BenchTest"], "power/network/storage not measured"),
 "MC-36": (T, ["tools/bench.py"], [f"{tt}::BenchTest"], "thresholds PROPOSED, no approver"),
 "MC-37": (T, ["scheduler.py"], [f"{tr}::ObservabilityTest"], ""),
 "MC-38": (T, ["telemetry.py"], [f"{tr}::ObservabilityTest"], "no exporter endpoint bound"),
 "MC-39": (T, ["telemetry.py"], [f"{tr}::ObservabilityTest"], ""),
 "MC-40": (T, ["telemetry.py"], [f"{tr}::ObservabilityTest"], "no trace backend bound"),
 "MC-41": (T, ["scheduler.py"], [f"{tr}::ObservabilityTest"], "no UI; API only"),
 "MC-42": (D, ["telemetry.py", "docs/TELEMETRY_GOVERNANCE.md"], [f"{tt}::GovernanceTest"], "dashboards/alerts defined as code-free spec; not deployed"),
 "MC-43": (T, ["tests/test_contracts_integration.py"], [f"{tc}::SchemaContractTest"], ""),
 "MC-44": (X, ["adapters.py"], [f"{tc}::IntegrationMatrixTest"], "fakes only; real PLN/GAP/INV elements absent"),
 "MC-45": (X, ["ci/ci.sh", "docs/COMPATIBILITY.md"], [f"{tt}::CiTest"], "one platform executed (Linux x86_64, CPython 3.11); matrix not run"),
 "MC-46": (T, ["tests/test_contracts_integration.py"], [f"{tc}::PropertyFuzzTest"], "seeded stdlib fuzz; no coverage-guided fuzzer"),
 "MC-47": (T, ["tests/test_resilience_state.py"], [f"{tr}::FencingRaceTest"], "multi-host split-brain not testable here"),
 "MC-48": (X, ["tools/bench.py"], [f"{tt}::BenchTest"], "no soak/burst/fleet-scale environment"),
 "MC-49": (T, ["tools/evidence_bundle.py", "evidence/RELEASE_EVIDENCE.json"], [f"{tt}::EvidenceTest"], "bundle unsigned by a release authority"),
 "MC-50": (D, ["docs/policy/SUPPORT_AND_ERROR_BUDGET.md"], [f"{tt}::GovernanceTest"], "approver UNASSIGNED"),
 "MC-51": (T, ["canary.py"], [f"{tt}::CanaryTest"], "not wired to a real deployment system"),
 "MC-52": (D, ["docs/policy/VULNERABILITY_PATCH_EOL.md"], [f"{tt}::GovernanceTest"], "approver UNASSIGNED"),
 "MC-53": (T, ["state.py", "docs/runbooks/RB-04-backup-restore.md"], [f"{tr}::DurableStateTest"], "drill on production storage not run"),
 "MC-54": (D, ["docs/runbooks/"], [f"{tt}::GovernanceTest"], "drills not executed; commands untested on a real environment"),
 "MC-55": (D, ["docs/policy/INCIDENT_RESPONSE.md"], [f"{tt}::GovernanceTest"], "paging tree UNASSIGNED"),
 "MC-56": (D, ["governance/REVIEW_PROGRAM.json"], [f"{tt}::GovernanceTest"], "no review has occurred"),
 "MC-57": (T, ["governance/WAIVERS.json", "tools/exit_gate.py"], [f"{tt}::ExitGateTest"], "register empty; no waiver approved"),
 "MC-58": (T, ["tools/exit_gate.py"], [f"{tt}::ExitGateTest"], "gate returns NO_GO by construction until owners/approvals exist"),
 "MC-59": (T, ["ci/ci.sh", "ci/github-workflow.yml"], [f"{tt}::CiTest"], "not executed on a hosted CI runner"),
 "MC-60": (X, ["sbom/sbom.cdx.json", "RELEASE_SHA256SUMS.txt", "LICENSE-STATUS.md"], [f"{tt}::SbomTest"], "license terms unknown - owner must choose; provenance unsigned"),
 "EXT-01": (X, ["tests/test_component.py"], [], "pk_core not available; conformance tests skip"),
 "EXT-02": (X, ["adapters.py"], [f"{tc}::IntegrationMatrixTest"], "PLN-02 not bundled"),
 "EXT-03": (X, ["adapters.py"], [f"{tc}::IntegrationMatrixTest"], "PLN-05 not bundled"),
 "EXT-04": (X, ["adapters.py", "security.py"], [f"{tc}::IntegrationMatrixTest"], "GAP-02 not bundled; hardware attestation absent"),
 "EXT-05": (X, ["adapters.py"], [f"{tc}::IntegrationMatrixTest"], "PLN-04 not bundled; enforcement unproven"),
 "EXT-06": (X, ["adapters.py"], [f"{tc}::IntegrationMatrixTest"], "GAP-03 not bundled"),
 "EXT-07": (X, ["adapters.py"], [f"{tc}::IntegrationMatrixTest"], "GAP-10 not bundled"),
 "EXT-08": (X, ["adapters.py"], [f"{tc}::IntegrationMatrixTest"], "INV-33 not bundled; reclamation unproven end-to-end"),
}
