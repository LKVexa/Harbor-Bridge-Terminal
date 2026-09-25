"""Component -> implementation / test / blocker bindings for the 60-component
checklist.  ``tests`` are unittest ids (module.Class) that must PASS in the
run for a check of that component to reach VERIFYING.  ``blockers`` are
external dependencies that do not exist in this archive; checks that need
them are BLOCKED with the dependency named.  ``lacks`` lists aspects the
implementation does not cover (keywords matched against the check text)."""

T_CRYPTO = "test_c02_c04_c10_crypto"
T_XL = "test_c10_cross_language"
T_ATT = "test_c01_attestation"
T_DUR = "test_durability"
T_CTL = "test_controls_config"
T_AUTH = "test_auth_server"
T_SIG = "test_signals_pipelines"
T_P2 = "test_p2_conformance_fuzz_stress"

B_GAP06 = "real GAP-06 attestation service (TPM/TEE evidence) -- not in archive"
B_GAP07 = "real GAP-07 signature/provenance service and PKI -- not in archive"
B_PKCORE = "pk_core package -- not in archive"
B_SIBLINGS = "sibling components GAP-01/06/07/08 and PLN-05 -- not in archive"
B_KMS = "KMS / AEAD provider -- stdlib has no AEAD, none configured"
B_POLICY = "authoritative policy service -- not in archive"
B_GATEWAY = "production query gateway / IdP -- not in archive"
B_TIME = "trusted time source (NTS/PTP/roughtime) -- not in archive"
B_WASM = "Wasm runtime with component telemetry hooks -- not in environment"
B_VMM = "microVM hypervisor (e.g. Firecracker) -- not in environment"
B_BACKEND = "external observability backend / OTLP collector -- not in environment"
B_FLEET = "fleet-scale environment -- not in environment"
B_HW = "representative edge hardware with power/thermal instrumentation -- not in environment"
B_MULTINODE = "multi-node deployment for replication/failover -- not in environment"
B_OWNER = "named owner and independent reviewer -- none assigned"
B_MASTER = "authoritative MASTER.md source -- held by the owner, absent from archive"
B_NETCOLL = "live network flow/DNS source (eBPF/IPFIX) -- not in environment"
B_FEED = "advisory feed selection -- owner decision"

C = {}


def c(n, title, modules, tests, blockers=(), lacks=(), runbook=None):
    C[f"{n:02d}"] = dict(id=f"{n:02d}", title=title, modules=list(modules), tests=list(tests), blockers=list(blockers),
                         lacks=list(lacks), runbook=runbook, block_kw=[])


# Check-text keywords that can only be satisfied through the component's blocker.
BLOCK_KW = {
    "01": ["tpm", "tee", "pcr", "firmware", "hardware"],
    "02": ["certificate", "chain", "provenance chain"],
    "05": ["certif", "chain", "revocation", "pki"],
    "07": ["authoritative policy", "policy service"],
    "08": ["gateway", "identity provider", "idp"],
    "09": ["ntp", "ptp", "trusted time source", "time source"],
    "24": ["runtime", "live"],
    "25": ["hypervisor", "guest", "live"],
    "27": ["ebpf", "ipfix", "capture", "live"],
    "32": ["backend", "collector", "protocol"],
    "39": ["failover", "site", "consensus", "rpo", "rto"],
    "49": ["fleet", "soak", "hours"],
    "60": ["restor", "recover", "authoritative", "source revision", "provenance"],
}



c(1, "Real GAP-06 attestation adapter", ["attestation.py"], [f"{T_ATT}.TestAttestation"], [B_GAP06],
  ["benchmark", "p50", "hardware attestation", "real adjacent"],
  ("attestation reject spike (codes unverifiable/expired/revoked)", "check root set + policy version; revoke_device(); freeze reporter via QuarantineRegistry"))
c(2, "Real GAP-07 signature/provenance adapter", ["ed25519.py", "keys.py", "canonical.py"],
  [f"{T_CRYPTO}.TestEd25519RFC8032", f"{T_CRYPTO}.TestKeyLifecycleAndVerifier", f"{T_XL}.TestNodeReporter"], [B_GAP07],
  ["certificate", "chain", "fips", "real adjacent"],
  ("reporter_untrusted with reason unverifiable", "compare transcript key_id/fingerprint; revoke key; rotate"))
c(3, "Durable replay protection", ["durable.py"], [f"{T_DUR}.TestReplay", f"{T_P2}.TestConcurrency", f"{T_P2}.TestFaultInjection"], [],
  ["encrypt", "replicat", "migration"],
  ("replay_detected on legitimate retries", "confirm submission id reuse; ids are single-use once signature verifies (ADR-001 #5)"))
c(4, "Key/certificate lifecycle", ["keys.py", "audit_ledger.py"], [f"{T_CRYPTO}.TestKeyLifecycleAndVerifier"], [B_GAP07],
  ["certificate", "hsm", "kms", "real adjacent"],
  ("key compromise", "KeyRegistry.revoke(); rotate() new key; audit ledger shows lifecycle"))
c(5, "mTLS/authenticated transport", ["auth.py", "server.py"], [f"{T_AUTH}.TestMTLS"], [B_GAP07],
  ["revocation", "ocsp", "crl", "benchmark", "real adjacent", "rotation"],
  ("TLS handshake failures", "check client CA bundle; principal_from_peercert CN; expired certs"))
c(6, "Secret/KMS and at-rest encryption integration", ["auth.py"], [f"{T_AUTH}.TestKMSGuard"], [B_KMS],
  ["encrypt", "rotation", "kms", "key separation", "benchmark", "real adjacent"],
  ("dependency_unavailable purpose=wal", "a KMS provider is not configured; persistence of sensitive state is refused by design"))
c(7, "Central authorization-policy integration", ["auth.py"], [f"{T_AUTH}.TestPolicyAndPrincipal"], [B_POLICY],
  ["real adjacent", "benchmark", "cache"],
  ("all queries unauthorized/expired", "policy bundle expired or not loaded -> load a newer signed bundle"))
c(8, "Authenticated query-principal binding", ["auth.py", "server.py"], [f"{T_AUTH}.TestPolicyAndPrincipal", f"{T_AUTH}.TestServer"],
  [B_GATEWAY], ["real adjacent", "benchmark"],
  ("401 unauthenticated on /v1/query", "token kid unknown, audience or window wrong; check gateway issuer keys"))
c(9, "Time authority / clock-skew policy", ["controls.py"], [f"{T_CTL}.TestTime"], [B_TIME],
  ["real adjacent", "ntp", "ptp", "benchmark"],
  ("time_untrusted everywhere", "trusted source unsynchronised > max_sync_age; ingestion halts by design until sync returns"))
c(10, "Canonical cross-language signing profile", ["canonical.py", "reporters/node_reporter.mjs"],
  [f"{T_CRYPTO}.TestCanonicalProfile", f"{T_XL}.TestNodeReporter", f"{T_P2}.TestFuzzProperty"], [], [],
  ("signature mismatch from a non-Python reporter", "diff reporter canonical text against canonical.canonicalize() for the same envelope"))
c(11, "Durable local write-ahead buffer", ["durable.py", "ingest.py"], [f"{T_DUR}.TestWAL", f"{T_SIG}.TestReconnect", f"{T_P2}.TestFuzzProperty"],
  [], ["encrypt", "partition-safe", "benchmark"],
  ("WAL at disk bound (quota_exceeded)", "reconnect and reconcile(); raise max_bytes only with capacity approval"))
c(12, "Admission control and backpressure", ["controls.py", "server.py"], [f"{T_CTL}.TestAdmissionQuota", f"{T_AUTH}.TestServer"], [],
  ["benchmark", "fleet"],
  ("429 throttled storms", "inspect DecisionLog rules ADM-*; tune buckets via config (audited)"))
c(13, "Per-tenant cardinality quotas", ["controls.py"], [f"{T_CTL}.TestAdmissionQuota"], [], ["benchmark"],
  ("quota_exceeded for one tenant", "confirm with quota.usage(); raise override only via config change"))
c(14, "Tamper-evident security audit ledger", ["audit_ledger.py"], [f"{T_DUR}.TestAuditLedger", f"{T_P2}.TestConcurrency"], [],
  ["encrypt", "replicat", "external anchor service"],
  ("audit verify fails (corrupted)", "stop writers, preserve file, compare head against external anchor, open incident"))
c(15, "Production configuration subsystem", ["config.py"], [f"{T_CTL}.TestConfig"], [], ["reload signal", "benchmark"],
  ("config_rejected on apply", "active version unchanged; fix document; rollback() available"))
c(16, "pk_core dependency/package", [], [], [B_PKCORE], [], None)
c(17, "Actual production gate evidence", [], [], [B_PKCORE, B_SIBLINGS], [], None)
c(18, "Evidence-gate hardening", ["checklist/engine.py"], ["test_checklist_engine.TestEngine"], [B_PKCORE], ["pk_core"],
  ("a record claims PASS", "engine.validate refuses PASS without owner+reviewer; re-run engine"))
c(19, "Network service / RPC handlers", ["server.py"], [f"{T_AUTH}.TestServer"], [], ["wit", "grpc", "http/2", "cancellation", "benchmark"],
  ("5xx from /v1/*", "codes are stable; internal_error means a bug -- capture request id and reproduce"))
c(20, "Multi-signal event model", ["signals.py"], [f"{T_SIG}.TestModelAndContext"], [], ["schema evolution"], None)
c(21, "Trace-context propagation", ["signals.py", "adapters.py"], [f"{T_SIG}.TestModelAndContext", f"{T_SIG}.TestAdapters", f"{T_P2}.TestFuzzProperty"],
  [B_WASM, B_VMM], ["real adjacent"], None)
c(22, "Causal-context graph", ["signals.py"], [f"{T_SIG}.TestModelAndContext"], [], ["persist", "benchmark"], None)
c(23, "Signal catalogue service/registry", ["signals.py", "server.py"], [f"{T_SIG}.TestModelAndContext", f"{T_P2}.TestSchemaConformance"], [],
  ["persist", "event"], None)
c(24, "Wasm instrumentation/collector adapter", ["adapters.py"], [f"{T_SIG}.TestAdapters"], [B_WASM], ["real adjacent", "benchmark"], None)
c(25, "microVM/hypervisor adapter", ["adapters.py"], [f"{T_SIG}.TestAdapters"], [B_VMM], ["real adjacent", "benchmark"], None)
c(26, "Host/node collectors", ["adapters.py"], [f"{T_SIG}.TestAdapters"], [], ["kernel", "windows", "benchmark"], None)
c(27, "Network telemetry adapters", ["adapters.py"], [f"{T_SIG}.TestAdapters"], [B_NETCOLL], ["real adjacent", "transport", "benchmark"], None)
c(28, "Log ingestion pipeline", ["pipelines.py", "policy.py"], [f"{T_SIG}.TestPipelines"], [], ["benchmark", "persist"], None)
c(29, "Metrics pipeline", ["pipelines.py"], [f"{T_SIG}.TestPipelines"], [], ["benchmark", "persist", "exponential"], None)
c(30, "Trace pipeline", ["pipelines.py"], [f"{T_SIG}.TestPipelines"], [], ["tail sampling", "benchmark", "persist"], None)
c(31, "Continuous profiling pipeline", ["pipelines.py"], [f"{T_SIG}.TestPipelines"], [], ["symboliz", "pprof", "benchmark"], None)
c(32, "Export/sink adapters", ["export.py"], [f"{T_SIG}.TestPolicyExportQuery"], [B_BACKEND], ["real adjacent", "benchmark", "certified"], None)
c(33, "Query service beyond latest value", ["query_service.py"], [f"{T_SIG}.TestPolicyExportQuery"], [], ["persist", "benchmark"], None)
c(34, "Retention/sampling/privacy policy engine", ["policy.py"], [f"{T_SIG}.TestPolicyExportQuery", f"{T_SIG}.TestPipelines"], [],
  ["deletion", "legal", "benchmark"], None)
c(35, "High-cardinality safety controls", ["policy.py", "controls.py"], [f"{T_SIG}.TestPolicyExportQuery", f"{T_CTL}.TestAdmissionQuota"], [], ["benchmark"], None)
c(36, "Health/readiness/dependency endpoint", ["controls.py", "server.py"], [f"{T_CTL}.TestQuarantineBreakerHealth", f"{T_AUTH}.TestServer"], [], [], None)
c(37, "Decision/explain records", ["controls.py", "policy.py"], [f"{T_CTL}.TestQuarantineBreakerHealth", f"{T_CTL}.TestAdmissionQuota"], [], ["persist"], None)
c(38, "Persistent state backend or reconstruction contract", ["durable.py"], [f"{T_DUR}.TestStateAndBackup"], [], ["replicat", "encrypt", "migration"], None)
c(39, "Replication/failover model", ["replication.py"], [f"{T_CTL}.TestFencing"], [B_MULTINODE], ["rpo", "rto", "consensus", "real adjacent", "partition"], None)
c(40, "Partition/reconnect protocol", ["ingest.py", "durable.py"], [f"{T_SIG}.TestReconnect"], [], ["long disconnected", "fleet"], None)
c(41, "Quarantine/freeze controls", ["controls.py"], [f"{T_CTL}.TestQuarantineBreakerHealth"], [], ["persist"], None)
c(42, "Dependency circuit breakers", ["controls.py", "export.py"], [f"{T_CTL}.TestQuarantineBreakerHealth", f"{T_P2}.TestFaultInjection"], [], [], None)
c(43, "Backup/restore/migration procedures", ["durable.py"], [f"{T_DUR}.TestStateAndBackup"], [], ["migration", "encrypt", "offsite"], None)
c(44, "Adjacent-layer integration tests", [], [], [B_SIBLINGS], [], None)
c(45, "Contract-schema conformance tests", ["server.py", "signals.py"], [f"{T_P2}.TestSchemaConformance"], [], ["codegen", "generated"], None)
c(46, "Fuzz/property tests", ["tests/test_p2_conformance_fuzz_stress.py"], [f"{T_P2}.TestFuzzProperty"], [], ["coverage-guided", "corpus"], None)
c(47, "Concurrency/race stress tests", ["tests/test_p2_conformance_fuzz_stress.py"], [f"{T_P2}.TestConcurrency"], [], ["multi-process", "sanitizer"], None)
c(48, "Fault-injection tests", ["tests/test_p2_conformance_fuzz_stress.py"], [f"{T_P2}.TestFaultInjection", f"{T_DUR}.TestReplay"], [], ["network partition", "real adjacent"], None)
c(49, "Soak/burst/fleet-scale tests", ["tests/test_p2_conformance_fuzz_stress.py"], [f"{T_P2}.TestSoakBurstLocal"], [B_FLEET], ["soak", "fleet", "24"], None)
c(50, "Performance baselines", ["tools/bench.py"], ["test_tools.TestBench"], [], ["representative", "fleet", "arm"], None)
c(51, "Edge power/thermal measurements", [], [], [B_HW], [], None)
c(52, "Release regression gates", ["tools/regression_gate.py"], ["test_tools.TestRegressionGate"], [B_OWNER], ["approved threshold"], None)
c(53, "Compatibility matrix", ["docs/COMPATIBILITY.md"], ["test_tools.TestDocs"], [], ["windows", "3.10"], None)
c(54, "Packaging/dependency lock/SBOM", ["tools/sbom.py"], ["test_tools.TestSBOM"], [], ["sign", "provenance attestation"], None)
c(55, "Vulnerability/EOL policy", ["docs/VULN_EOL_POLICY.md"], ["test_tools.TestDocs"], [B_FEED], ["feed", "scanner"], None)
c(56, "Owner/escalation and incident runbooks", ["docs/RUNBOOKS.md"], ["test_tools.TestDocs"], [B_OWNER], ["escalation", "on-call", "pager"], None)
c(57, "Architecture decision record", ["docs/ADR-001-v5.1-overlay.md"], ["test_tools.TestDocs"], [B_OWNER], ["accepted"], None)
c(58, "Exception/waiver/debt registry", ["docs/WAIVERS.json"], ["test_tools.TestDocs"], [B_OWNER], ["approved"], None)
c(59, "Dashboards and operational views", ["tools/dashboard.py"], ["test_tools.TestDashboard"], [B_BACKEND], ["grafana", "alert"], None)
c(60, "MASTER.md", ["tools/doc_check.py"], ["test_tools.TestDocs"], [B_MASTER], [], None)

for _k, _v in BLOCK_KW.items():
    C[_k]["block_kw"] = _v
