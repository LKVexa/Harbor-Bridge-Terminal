"""Machine-readable map of the 55 checklist components → implementation, tests, status, blockers.

Status vocabulary (never 'COMPLETE' without independent sign-off):
  LOCALLY_VERIFIED  implemented; automated tests named below pass in this build
  CONTRACT_VERIFIED implemented against sibling contract fakes; real sibling test pending
  PARTIAL           some mandatory parts done, others blocked
  BLOCKED           cannot be honestly completed in this build (reason stated)
"""
REVIEW = "independent reviewer/owner sign-off not recorded (checklist Definition of Done)"
LAB = "physical-hardware execution not performed (fixtures/lab_manifest.json)"
SIB = "real sibling package not present in this build"

C = [
 (1, "Vendor-grade GPU compute probes", "P0", "LOCALLY_VERIFIED", ["production/accelerators.py"], ["TestGpu_MC01"], [LAB, REVIEW]),
 (2, "NPU/AI accelerator probes", "P0", "LOCALLY_VERIFIED", ["production/accelerators.py"], ["TestNpu_MC02"], [LAB, "vendor runtime-check commands must be supplied per deployment", REVIEW]),
 (3, "Cross-platform CPU feature engine", "P0", "LOCALLY_VERIFIED", ["production/cpu.py"], ["TestCpu_MC03"], ["Windows/macOS paths fixture-only; native CPUID not in stdlib (kernel view used)", REVIEW]),
 (4, "NUMA and memory-topology discovery", "P0", "LOCALLY_VERIFIED", ["production/topology.py"], ["TestNuma_MC04"], ["Linux only; bandwidth class not measured", LAB, REVIEW]),
 (5, "Storage-device capability discovery", "P0", "LOCALLY_VERIFIED", ["production/storage.py"], ["TestStorage_MC05"], ["Linux only; SMART health needs broker deployment", REVIEW]),
 (6, "NIC capability discovery", "P0", "LOCALLY_VERIFIED", ["production/nic.py"], ["TestNic_MC06"], ["Linux only; ethtool offloads need broker deployment", LAB, REVIEW]),
 (7, "Virtualization/IOMMU discovery", "P0", "LOCALLY_VERIFIED", ["production/virt.py"], ["TestVirt_MC07"], [LAB, REVIEW]),
 (8, "Confidential-computing probes", "P0", "LOCALLY_VERIFIED", ["production/confidential.py"], ["TestConfidential_MC08"], [LAB, "attested tier needs GAP-06 verifier", REVIEW]),
 (9, "Cross-platform secure-device probes", "P0", "LOCALLY_VERIFIED", ["production/securedev.py"], ["TestSecureDevice_MC09"], ["EK/AK enumeration needs broker + tpm2 tooling", LAB, REVIEW]),
 (10, "Signed report envelope API", "P0", "LOCALLY_VERIFIED", ["production/envelope.py"], ["TestEnvelope_MC10"], ["reference HMAC signer only; GAP-07 asymmetric binding pending", REVIEW]),
 (11, "Replay protection and report sequencing", "P0", "LOCALLY_VERIFIED", ["production/replay.py"], ["TestReplay_MC11", "TestConcurrency_MC45"], [REVIEW]),
 (12, "Trusted time policy", "P0", "LOCALLY_VERIFIED", ["production/timepolicy.py"], ["TestTrustedTime_MC12"], ["trusted sync source (NTS/PTP/attested) must be wired per deployment", REVIEW]),
 (13, "Probe configuration model", "P0", "LOCALLY_VERIFIED", ["production/config.py"], ["TestConfig_MC13"], [REVIEW]),
 (14, "Probe executor/service loop", "P0", "LOCALLY_VERIFIED", ["production/executor.py", "production/agent.py"], ["TestExecutor_MC14"], [REVIEW]),
 (15, "Atomic sweep semantics", "P0", "LOCALLY_VERIFIED", ["production/sweep.py"], ["TestAtomicSweep_MC15", "TestConcurrency_MC45"], [REVIEW]),
 (16, "Control-plane publisher transport", "P0", "PARTIAL", ["production/publisher.py"], ["TestPublisher_MC16"], ["concrete authenticated control-plane transport not specified/available", REVIEW]),
 (17, "Structured error-code taxonomy", "P0", "LOCALLY_VERIFIED", ["production/errors.py"], ["TestErrorTaxonomy_MC17"], [REVIEW]),
 (18, "Probe privilege broker", "P0", "PARTIAL", ["production/broker.py"], ["TestBroker_MC18"], ["service identity / device ACL deployment not performed", REVIEW]),
 (19, "Report authorization policy", "P0", "LOCALLY_VERIFIED", ["production/authz.py"], ["TestAuthz_MC19"], ["principal bindings must come from the estate IdP", REVIEW]),
 (20, "Package/artifact provenance enforcement", "P0", "LOCALLY_VERIFIED", ["production/provenance.py"], ["TestProvenance_MC20"], ["release signing key (GAP-07) not provisioned", REVIEW]),
 (21, "GAP-06 integration tests", "P1", "CONTRACT_VERIFIED", ["production/integration.py"], ["TestGap06Contract_MC21"], [SIB + " (GAP-06)", REVIEW]),
 (22, "GAP-07 integration tests", "P1", "CONTRACT_VERIFIED", ["production/integration.py"], ["TestGap07Contract_MC22"], [SIB + " (GAP-07)", REVIEW]),
 (23, "GAP-01 supervisor integration", "P1", "CONTRACT_VERIFIED", ["production/integration.py"], ["TestGap01Contract_MC23"], [SIB + " (GAP-01)", REVIEW]),
 (24, "SCH-01 placement integration", "P1", "CONTRACT_VERIFIED", ["production/integration.py"], ["TestSch01Contract_MC24"], [SIB + " (SCH-01)", REVIEW]),
 (25, "PLN-04 execution-plane integration", "P1", "CONTRACT_VERIFIED", ["production/integration.py"], ["TestPln04Contract_MC25"], [SIB + " (PLN-04)", REVIEW]),
 (26, "GAP-11 accelerator-scheduler integration", "P1", "CONTRACT_VERIFIED", ["production/integration.py"], ["TestGap11Contract_MC26"], [SIB + " (GAP-11)", REVIEW]),
 (27, "Compatibility negotiation", "P1", "LOCALLY_VERIFIED", ["production/compat.py", "COMPATIBILITY_MATRIX.json"], ["TestCompat_MC27"], [REVIEW]),
 (28, "Persistent probe cache", "P1", "LOCALLY_VERIFIED", ["production/cache.py"], ["TestCache_MC28"], [REVIEW]),
 (29, "Hot-plug watcher adapters", "P1", "PARTIAL", ["production/hotplug.py"], ["TestHotplug_MC29", "TestExecutor_MC14"], ["polling adapter only; udev/WMI/IOKit event adapters not built", REVIEW]),
 (30, "Health/readiness endpoint", "P1", "LOCALLY_VERIFIED", ["production/health.py"], ["TestHealth_MC30"], [REVIEW]),
 (31, "Metrics exporter", "P1", "LOCALLY_VERIFIED", ["production/observability.py"], ["TestMetrics_MC31"], [REVIEW]),
 (32, "Structured logging", "P1", "LOCALLY_VERIFIED", ["production/observability.py"], ["TestLogging_MC32"], [REVIEW]),
 (33, "Distributed tracing/OpenTelemetry hooks", "P1", "LOCALLY_VERIFIED", ["production/observability.py"], ["TestTracing_MC33"], ["OpenTelemetry path untested (package not installed)", REVIEW]),
 (34, "Tamper-evident audit stream", "P1", "LOCALLY_VERIFIED", ["production/audit.py"], ["TestAudit_MC34"], ["head export to GAP-07 pending", REVIEW]),
 (35, "Operator explain view", "P1", "LOCALLY_VERIFIED", ["production/explain.py"], ["TestExplain_MC35"], [REVIEW]),
 (36, "Alert/dashboard definitions", "P1", "LOCALLY_VERIFIED", ["ops/alerts.json", "ops/dashboard.json"], ["TestAlerts_MC36"], ["not loaded into a live monitoring stack", REVIEW]),
 (37, "Load shedding / circuit breaker", "P1", "LOCALLY_VERIFIED", ["production/breaker.py"], ["TestBreaker_MC37"], [REVIEW]),
 (38, "Crash/restart/resume semantics", "P1", "LOCALLY_VERIFIED", ["production/executor.py"], ["TestRestart_MC38"], [REVIEW]),
 (39, "Quarantine/freeze control", "P1", "LOCALLY_VERIFIED", ["production/quarantine.py"], ["TestQuarantine_MC39", "TestGap01Contract_MC23"], [REVIEW]),
 (40, "Resource ceilings", "P1", "LOCALLY_VERIFIED", ["production/limits.py"], ["TestResourceCeilings_MC40"], ["Windows job-object ceilings not implemented", REVIEW]),
 (41, "OS/architecture compatibility matrix", "P2", "PARTIAL", ["COMPATIBILITY_MATRIX.json"], ["TestConformance_MC43"], ["only linux/x86_64 host-verified", LAB]),
 (42, "Physical hardware fixture lab", "P2", "BLOCKED", ["fixtures/lab_manifest.json", "tests/fixtures.py"], [], [LAB]),
 (43, "Contract conformance fixtures", "P2", "LOCALLY_VERIFIED", ["conformance/cases.json"], ["TestConformance_MC43"], [REVIEW]),
 (44, "Property/fuzz tests", "P2", "LOCALLY_VERIFIED", ["tests/test_production.py"], ["TestPropertyFuzz_MC44"], ["random-sample fuzzing, not coverage-guided", REVIEW]),
 (45, "Concurrency/race tests", "P2", "LOCALLY_VERIFIED", ["tests/test_production.py"], ["TestConcurrency_MC45"], [REVIEW]),
 (46, "Fault-injection suite", "P2", "LOCALLY_VERIFIED", ["tests/test_production.py"], ["TestFaultInjection_MC46"], [REVIEW]),
 (47, "Performance/soak benchmarks", "P2", "PARTIAL", ["tools/bench.py"], ["TestTools_MC47"], ["soak (hours-long) run not performed", LAB]),
 (48, "Release regression gates", "P2", "LOCALLY_VERIFIED", ["tools/release_gate.py"], ["TestTools_MC48"], [REVIEW]),
 (49, "Formal ADR and accountable ownership record", "P2", "BLOCKED", ["ADR-0001-production-layer.md"], [], ["accountable owner not named — only the GAP-02 owner can assign"]),
 (50, "Support/security lifecycle policy", "P2", "BLOCKED", ["SUPPORT_POLICY.md"], [], ["drafted; windows/SLAs/contact need owner approval"]),
 (51, "Incident runbooks", "P2", "PARTIAL", ["RUNBOOKS.md"], ["TestTools_MC51"], ["not exercised in a game day"]),
 (52, "Reproducible packaging + SBOM", "P2", "LOCALLY_VERIFIED", ["tools/build.py"], ["TestTools_MC52"], ["artifact signing needs GAP-07 release key", REVIEW]),
 (53, "Explicit pk_core dependency/version contract", "P2", "PARTIAL", ["PK_CORE_CONTRACT.json"], ["TestTools_MC53"], ["pk_core version range unconfirmed (pk_core not available)"]),
 (54, "Restore original MASTER.md provenance artifact", "P2", "BLOCKED", ["tools/release_gate.py"], ["TestTools_MC48"], ["authentic MASTER.md not supplied; synthesizing a substitute is prohibited by the checklist"]),
 (55, "Full 100-check evidence package", "P2", "BLOCKED", ["tools/evidence.py"], [], ["pk_core and sibling estate not present; gate not run"]),
]
