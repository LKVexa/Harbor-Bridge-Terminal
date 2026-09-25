"""Single source for remediation/STATUS.json and TRACEABILITY.json.

States (never COMPLETE: the checklist requires independent reproduction and an
approved production gate, neither of which this pass can supply for itself):

* ``LOCAL_IMPLEMENTED`` - code/docs plus positive AND negative tests exist in
  this package and pass; not independently reviewed.
* ``PARTIAL``           - the in-repo part is implemented and tested; a named
  external or human part is still missing (``blocked_on``).
* ``BLOCKED``           - cannot be done inside this repository; the local
  controls that make the gap visible and fail closed are listed.
"""

L, P, B = "LOCAL_IMPLEMENTED", "PARTIAL", "BLOCKED"
OWNER = "accountable owner (governance/OWNERS.json is unassigned)"

ITEMS = {
    "01": (B, ["provenance/PROVENANCE.json", "tools/verify_governance.py", "governance/EXCEPTIONS.json#EXC-001",
               "tests/test_governance.py::ProvenanceTest"],
           ["original MASTER.md (not in any supplied source)", "approval of EXC-001 by " + OWNER]),
    "02": (B, ["deps/pk_core.lock.json", "verify.py (PK_REQUIRE_CORE=1 fails closed)"],
           ["pk_core package + approved pin"]),
    "03": (P, ["tools/build_release.py", "evidence/ledger.jsonl", "conformance/INV43_LOCAL_GATE.json"],
           ["pk_core gate output (item 02)", "independent reproduction"]),
    "04": (L, ["pyproject.toml", "requirements-dev.lock", "sbom.cdx.json"], ["wheel hashes in the lock (item 23)"]),
    "05": (P, ["docs/adr/ADR-0001-transient-execution-defense.md"], ["ADR approval by " + OWNER]),
    "06": (P, ["docs/adr/ADR-0002-sfi-resolution.md", "governance/EXCEPTIONS.json#EXC-002"],
           ["PLN-04 SFI ADR", "approval by " + OWNER]),
    "07": (B, ["governance/OWNERS.json", "tools/verify_governance.py"], ["named owner, team, on-call, escalation"]),
    "08": (L, ["TRACEABILITY.json", "tools/status_table.py", "tests/test_governance.py::TraceabilityTest"], []),
    "09": (P, ["collector.py", "tests/test_signal_path.py::CollectorTest", "evidence/host_readback.json"],
           ["core-scheduling observability (per-task prctl state lives in SCH-01)", "non-Linux read-back sources"]),
    "10": (L, ["collector.py::Observation", "registry.py::_fresh_entry", "tests/test_decision_plane.py::RegistryTest"], []),
    "11": (P, ["attestation.py", "tests/test_signal_path.py::AttestationTest", "governance/EXCEPTIONS.json#EXC-003"],
           ["hardware-rooted attestation (TPM/SEV-SNP/TDX) service"]),
    "12": (L, ["authz.py", "tests/test_signal_path.py::AuthzTest"], ["identity-provider binding for principals"]),
    "13": (P, ["policy.py", "policy/default_policy.json", "schemas/INV43_POLICY_1.schema.json", "tests/test_signal_path.py::PolicyTest"],
           ["policy content approval by a policy owner"]),
    "14": (L, ["config.py", "schemas/INV43_CONFIG_1.schema.json", "tests/test_signal_path.py::ConfigTest"], []),
    "15": (P, ["placement.py", "tests/test_decision_plane.py::PlacementTest"], ["SCH-01 implementation to integrate against"]),
    "16": (P, ["policy.py::gap02_contradictions", "tests/test_decision_plane.py::RegistryTest.test_gap02_contradiction_downgrades"],
           ["GAP-02 implementation / real capability records"]),
    "17": (P, ["policy/default_policy.json#isolation_tiers", "tests/test_signal_path.py::PolicyTest"], ["PLN-04 implementation"]),
    "18": (P, ["policy/default_policy.json#legacy_cpu", "tests/test_decision_plane.py::IntegrationTest"], ["INV-34 implementation"]),
    "19": (P, ["service.py", "tests/test_decision_plane.py::ServiceTest"], ["TLS certificate issuance/rotation (deployment)"]),
    "20": (L, ["negotiation.py", "docs/COMPATIBILITY.md", "tests/test_decision_plane.py::NegotiationTest"], []),
    "21": (L, ["schemas/*.json", "tests/test_hardening.py::SchemaConformanceTest", "requirements-dev.lock"], []),
    "22": (P, ["auditlog.py", "tests/test_decision_plane.py::AuditChainTest"], ["WORM/remote retention sink"]),
    "23": (P, ["sbom.cdx.json", "SHA256SUMS.txt", "release/provenance.intoto.json", "release/signature.json", "tools/verify_release.py"],
           ["release signing key (current signature is an ephemeral dev key)", "approved dependency policy"]),
    "24": (P, ["docs/THREAT_MODEL.md"], ["independent security review"]),
    "25": (L, ["tests/test_hardening.py::AdversarialTest", "tests/test_hardening.py::SecretLeakageTest"], []),
    "26": (L, ["tests/test_hardening.py::PropertyFuzzTest (INV43_FUZZ_SEED/INV43_FUZZ_N)"], ["coverage-guided fuzzing infrastructure (optional)"]),
    "27": (L, ["docs/CONCURRENCY.md", "tests/test_hardening.py::ConcurrencyTest"], []),
    "28": (L, ["resilience.py::FailureClass/HealthMonitor", "tests/test_hardening.py::ResilienceTest"], []),
    "29": (L, ["resilience.py::RetryPolicy", "tests/test_hardening.py::ResilienceTest"], []),
    "30": (L, ["resilience.py::TokenBucket/ConcurrencyLimiter/CircuitBreaker", "service.py"], []),
    "31": (P, ["docs/RECOVERY.md", "registry.py", "tests/test_decision_plane.py::RegistryTest"], ["multi-replica HA (declared unsupported)"]),
    "32": (L, ["registry.py::quarantine/release/freeze", "tests/test_decision_plane.py::RegistryTest.test_freeze_and_kill_switch"], []),
    "33": (P, ["tests/test_hardening.py::FaultInjectionTest"], ["real network-partition / disaster lab"]),
    "34": (P, ["bench/run_bench.py", "evidence/perf/baseline.json"], ["per-mitigation cost attribution via A/B boots on target hardware"]),
    "35": (P, ["perf/thresholds.json", "evidence/perf/gate.json"], ["threshold approval by " + OWNER]),
    "36": (P, ["docs/CAPACITY.md", "evidence/perf/baseline.json"], ["power/thermal and edge-node measurements"]),
    "37": (L, ["telemetry.py::Metrics", "service.py /metrics"], []),
    "38": (L, ["telemetry.py::StructuredLogger", "tests/test_hardening.py::SecretLeakageTest"], []),
    "39": (L, ["telemetry.py::parse_traceparent", "tests/test_decision_plane.py::ServiceTest"], []),
    "40": (L, ["registry.py::explain", "service.py /v1/explain"], []),
    "41": (P, ["ops/alerts.yaml", "ops/dashboard.json"], ["deployment and validation on live monitoring"]),
    "42": (P, ["tests/test_decision_plane.py::IntegrationTest"], ["real SCH-01/GAP-02/PLN-04/INV-34 components"]),
    "43": (P, ["docs/COMPATIBILITY.md", "tests/fixtures/kernel_strings.json"], ["hypervisor/provider/kernel lab runs"]),
    "44": (P, ["tests/test_hardening.py::SoakBurstTest (INV43_SOAK_*)"], ["fleet-scale soak environment"]),
    "45": (L, ["rollout.py", "tests/test_hardening.py::RolloutTest"], ["approver identity verification (platform IdP)"]),
    "46": (L, ["docs/RECOVERY.md", "tests/test_decision_plane.py::RegistryTest.test_controls_survive_restart_via_audit_chain"], []),
    "47": (P, ["docs/RUNBOOK.md"], ["on-call names (" + OWNER + ")"]),
    "48": (P, ["docs/INCIDENT_RESPONSE.md"], ["paging targets (" + OWNER + ")"]),
    "49": (P, ["governance/REVIEW_SCHEDULE.json", "tools/verify_governance.py"], ["reviews actually held and recorded"]),
    "50": (L, ["governance/EXCEPTIONS.json", "tools/verify_governance.py", "tests/test_governance.py::ExceptionLedgerTest"],
           ["approval of each PROPOSED entry"]),
    "51": (P, ["SECURITY.md"], ["security contact and SLA approval (" + OWNER + ")"]),
    "52": (B, ["NOTICE", "pyproject.toml (no license field)", "tools/verify_governance.py"], ["license decision by " + OWNER]),
}

# Controls not referenced by any remediation item: mapped to their evidence here.
EXTRA_CONTROLS = {
    "C001": ["README.md#Responsibility", "docs/adr/ADR-0001-transient-execution-defense.md"],
    "C002": ["README.md#Owns", "contract.py"],
    "C005": ["docs/adr/ADR-0001-transient-execution-defense.md#Decision", "docs/THREAT_MODEL.md#Assumptions"],
    "C007": ["docs/adr/ADR-0001-transient-execution-defense.md (item 7)"],
    "C008": ["docs/adr/ADR-0001-transient-execution-defense.md#Unsupported"],
    "C012": ["docs/adr/ADR-0001-transient-execution-defense.md#Functional scope"],
    "C013": ["docs/adr/ADR-0001-transient-execution-defense.md#Non-functional", "perf/thresholds.json"],
    "C039": ["tests/test_hardening.py::SecretLeakageTest", "service.py::TokenStore (hashed tokens)"],
    "C047": ["service.py (TLS mandatory off-loopback)", "docs/RECOVERY.md (no posture at rest)",
             "BLOCKED: managed key rotation for audit-at-rest and TLS certs is a deployment dependency"],
    "C065": ["docs/CAPACITY.md#Avoidable work"],
    "C066": ["docs/CAPACITY.md#Avoidable work (no optimisation applied; documented why)"],
    "C081": ["tests/test_defense.py", "tests/test_signal_path.py", "tests/test_hardening.py::PropertyFuzzTest"],
}
