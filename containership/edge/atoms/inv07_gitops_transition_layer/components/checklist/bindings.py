"""Component -> implementation / test / blocker bindings for the 54-component
INV-07 checklist (40 checks each: X01-X02, A01-A05, I01-I02, C01-C02,
S01-S04, R01-R03, P01-P02, O01-O02, T01-T05, D01, E01-E02, G01-G02,
DOD01-DOD08).

``tests``   unittest ids (module.Class) that must all PASS for any check of the
            component to reach VERIFYING.
``blockers`` external dependencies absent from this archive; checks that need
            them are BLOCKED naming the dependency.
``block_kw`` words in a check that can only be satisfied through a blocker.
``lacks``   aspects the implementation does not cover (-> IN_PROGRESS).
``flags``   which cross-cutting check families this component actually has
            code+tests for.  A flag is a claim that a reviewer can falsify by
            reading the bound modules/tests; the engine still applies the
            stem-overlap lower bound on top of it.

  c config schema coverage (C01/C02)      t threat-model row (S01)
  l least-privilege profile (S02)         f fail-closed tested (S04/DOD04)
  b bounded dependency failure (R01)      k crash consistency (R02)
  q rollback/disable/quarantine (R03)     p explicit limits (P01)
  m measured in tools/bench.py (P02)      o metrics/logs/traces/audit (O01/O02/DOD06)
  x concurrency/restart tests (T03)       a adversarial tests (T04)
  d component docs (D01)                  s lifecycle states (A05)
  i versioned wire/durable schema (I01)   r ADR table row (A03)
  e production implementation local (DOD01); absent -> adapter only
  L production-like deps available locally (X02/T02/DOD02)
"""

B_GITSERVER = "production Git server (smart HTTPS/SSH) reachable from the build -- not in environment"
B_CLUSTER = "Kubernetes cluster with Argo CD / Flux -- not in environment"
B_GAP07 = "GAP-07 provenance service, Fulcio-style certificate chain and Rekor-style transparency log -- not in archive"
B_KMS = "managed KMS/HSM/secret store and AEAD provider -- not in environment"
B_IDP = "production identity provider (OIDC/JWKS) -- not in environment"
B_REGISTRY = "OCI registry access to pin base-image digest, push and sign the image -- not in environment"
B_FEED = "vulnerability advisory feed/scanner selection -- owner decision"
B_TIME = "trusted time source (NTS/PTP/roughtime) -- not in environment"
B_OPA = "external policy engine (OPA/Rego, CEL) -- not in environment"
B_SIBLINGS = "sibling components INV-05/INV-06/INV-63 and pk_core -- not in archive"
B_COLLECTOR = "OTLP collector / tracing backend -- not in environment"
B_BACKEND = "Prometheus/Grafana backend to load dashboards and alerts -- not in environment"
B_FLEET = "fleet-scale, long-duration soak environment -- not in environment"
B_PLATFORMS = "declared OS/CPU/Python/container/Kubernetes combinations -- only Linux x86_64 CPython 3.11 here"
B_OWNER = "named engineering owner, security reviewer and operations owner -- none assigned"
B_MASTER = "owner ratification of the regenerated MASTER.md (original absent from archive)"
B_LICENSE = "governing project license -- owner decision"
B_RENDER = "pinned Helm/Kustomize renderer binaries -- not bundled"

T = "test_git_trust"
A = "test_apply_state"
S = "test_security"
K = "test_contracts"
O = "test_ops"
E2 = "test_e2e"
TT = "test_tools"

C: dict = {}


def c(n, title, modules, tests, blockers=(), flags="", block_kw=(), lacks=()):
    C[f"{n:02d}"] = dict(id=f"{n:02d}", title=title, modules=list(modules), tests=list(tests),
                         blockers=list(blockers), flags=set(flags), block_kw=[k.lower() for k in block_kw],
                         lacks=[k.lower() for k in lacks])


c(1, "Real Git transport and repository adapter", ["gitrepo.py"],
  [f"{T}.TestGitTransport", f"{E2}.TestFaultInjection"], [B_GITSERVER], "ctfbpmoare",
  block_kw=["production-like"])
c(2, "Approved-branch/ref policy enforcement", ["refpolicy.py", "controller.py"],
  [f"{T}.TestRefPolicy", f"{T}.TestFreshness"], [], "ctfqoareiL")
c(3, "Asymmetric commit/tag signature verification", ["signing.py", "ed25519.py", "gitrepo.py"],
  [f"{T}.TestSignatures"], [], "ctfpmoareiL", lacks=["sigstore", "tag"])
c(4, "Artifact provenance integration", ["provenance.py", "repotools.py"], [f"{T}.TestProvenance"], [B_GAP07],
  "tfoar", block_kw=["certificate", "transparency", "gap-07"])
c(5, "Argo CD/Flux/controller adapter", ["controllers.py"], [f"{A}.TestControllerAdapters"], [B_CLUSTER],
  "sr", block_kw=["production reconciliation", "kubernetes", "production-like", "renderer"])
c(6, "Live-state reader and applier", ["target.py"],
  [f"{A}.TestTarget", f"{A}.TestKubernetesAdapter", f"{E2}.TestEndToEnd"], [B_CLUSTER], "ctfqpoxare",
  block_kw=["production control-plane", "authenticated production", "production-like"])
c(7, "Atomic apply/transaction strategy", ["apply.py", "state.py"],
  [f"{A}.TestTransaction", f"{E2}.TestFaultInjection", f"{E2}.TestEndToEnd"], [], "fbkqpmoxaresL")
c(8, "Persistent controller state", ["state.py"], [f"{A}.TestState", f"{A}.TestRecovery"], [], "kpoxreiL")
c(9, "Leader election / duplicate-controller protection", ["lease.py", "target.py"],
  [f"{A}.TestLease", f"{E2}.TestEndToEnd"], [], "ctfbkqoxaresL")
c(10, "Authentication and authorization boundary", ["authz.py", "server.py"],
  [f"{S}.TestAuthz", f"{O}.TestServer"], [B_IDP], "tlfoare", block_kw=["identity provider", "oidc", "sso"])
c(11, "Secret/key management integration", ["keys.py", "redact.py"], [f"{S}.TestKeys"], [B_KMS], "tfar",
  block_kw=["kms", "hsm", "secret-store", "managed", "short-lived"])
c(12, "Tamper-evident audit ledger", ["audit.py"], [f"{S}.TestAudit", f"{E2}.TestEndToEnd"], [], "tfkoareiL",
  lacks=["worm", "retention"])
c(13, "Versioned interface schemas", ["schemas.py", "schemas/PK_GITOPS_SYNC_1.schema.json"],
  [f"{K}.TestSchemas", f"{K}.TestContractFixtures"], [], "fidreL")
c(14, "Machine-readable error model", ["errors.py", "redact.py"], [f"{K}.TestErrors", f"{S}.TestAdversarial"], [],
  "fidreaL")
c(15, "Production bootstrap/deployment packaging", ["deploy/Dockerfile", "deploy/kubernetes/controller.yaml",
                                                     "deploy/inv07.service"], [f"{TT}.TestPackaging"], [B_REGISTRY],
  "ld", block_kw=["oci", "sign", "provenance", "image", "clean-environment", "production-like"])
c(16, "Retry/backoff/jitter policy", ["resilience.py"], [f"{O}.TestRetry", f"{E2}.TestFaultInjection"], [],
  "cfbpoesL", lacks=["queue"])
c(17, "Dependency circuit breaking / admission control", ["resilience.py"],
  [f"{O}.TestAdmission", f"{E2}.TestFaultInjection"], [], "cbpmoxaesL")
c(18, "Offline/disconnected operation policy", ["operations.py", "controller.py"], [f"{O}.TestOffline"], [],
  "cfbqoesL", lacks=["backlog"])
c(19, "Crash recovery and replay", ["state.py", "controller.py"], [f"{A}.TestRecovery", f"{E2}.TestFaultInjection"],
  [], "kqoxeL")
c(20, "Quarantine/freeze/emergency disable", ["operations.py", "server.py"], [f"{O}.TestFreeze"], [], "fqodesL")
c(21, "Multi-tenant hard isolation", ["tenancy.py", "target.py"], [f"{S}.TestTenancy"], [], "tlfaeL",
  lacks=["network", "quotas", "telemetry"])
c(22, "Residency/site policy enforcement", ["tenancy.py"], [f"{S}.TestResidency"], [], "feL",
  lacks=["data/control-plane residency"])
c(23, "Policy engine integration", ["policy.py"], [f"{S}.TestPolicy"], [B_OPA], "fpoaeL",
  block_kw=["opa", "rego", "cel"])
c(24, "Manifest/input parser hardening", ["manifests.py"], [f"{S}.TestParsers", f"{E2}.TestFuzz"], [B_RENDER],
  "tfpmaeL", block_kw=["helm", "kustomize", "rendering", "sandbox"])
c(25, "Supply-chain dependency controls", ["tools/gates.py"], [f"{TT}.TestSBOM", f"{TT}.TestLint"], [B_FEED, B_REGISTRY],
  "t", block_kw=["vulnerabilit", "images", "scan"])
c(26, "Network security profile", ["netsec.py", "gitrepo.py"], [f"{S}.TestNetsec", f"{T}.TestGitTransport"], [],
  "ctfaeL", lacks=["rotation", "mtls", "pool"])
c(27, "Replay/freshness protection", ["refpolicy.py", "controller.py"], [f"{T}.TestFreshness", f"{T}.TestRefPolicy"],
  [], "ctfqoaeL")
c(28, "Time service behavior", ["operations.py"], [f"{O}.TestTime"], [B_TIME], "tfes",
  block_kw=["time-source protection", "trusted time"])
c(29, "Configuration system", ["config.py", "cli.py"], [f"{K}.TestConfig"], [], "cfdeirL",
  lacks=["secret references"])
c(30, "Compatibility matrix", ["docs/COMPATIBILITY.md", "tools/gates.py"], [f"{TT}.TestDocs", f"{TT}.TestPlatform"],
  [B_CLUSTER, B_GITSERVER, B_PLATFORMS], "d", block_kw=["argo", "flux", "kubernetes", "helm", "kms"])
c(31, "Migration plan from traditional IaC", ["migration.py", "docs/MIGRATION_FROM_IAC.md"], [f"{O}.TestMigration"],
  [B_SIBLINGS], "sqde", block_kw=["inventory"])
c(32, "Backup/restore/reconstruction procedure", ["state.py", "docs/BACKUP_RESTORE.md"],
  [f"{A}.TestBackup", f"{E2}.TestCLI"], [B_KMS], "kqde", block_kw=["encrypt"])
c(33, "Incident runbook", ["docs/RUNBOOKS.md"], [f"{TT}.TestDocs"], [B_OWNER], "d",
  block_kw=["exercised", "paging", "roles"])
c(34, "Patch/EOL/vulnerability SLA", ["docs/VULN_EOL_POLICY.md"], [f"{TT}.TestDocs"], [B_OWNER, B_FEED], "d",
  block_kw=["cve", "eol evidence"])
c(35, "Metrics endpoint", ["telemetry.py", "server.py"], [f"{O}.TestTelemetry", f"{O}.TestServer"], [],
  "cfpoaeL")
c(36, "Structured operational logging", ["telemetry.py", "redact.py"], [f"{O}.TestTelemetry"], [], "poaeiL")
c(37, "Distributed tracing", ["telemetry.py", "controller.py"], [f"{O}.TestTelemetry"], [B_COLLECTOR], "oe",
  lacks=["queues", "retries"])
c(38, "Operator explain view", ["telemetry.py", "controller.py", "server.py"], [f"{O}.TestExplain", f"{O}.TestServer"],
  [], "foieL")
c(39, "Dashboards and alerts", ["tools/gates.py", "deploy/prometheus-alerts.yaml", "deploy/grafana-dashboard.json"],
  [f"{TT}.TestDashboards"], [B_BACKEND], "do", block_kw=["production-like"])
c(40, "Telemetry retention/privacy policy", ["docs/TELEMETRY_POLICY.md", "redact.py", "telemetry.py"],
  [f"{TT}.TestDocs", f"{O}.TestTelemetry"], [B_OWNER], "de", block_kw=["privacy review"])
c(41, "Integration tests against real Git and target control planes", ["tests/test_e2e.py"],
  [f"{E2}.TestEndToEnd"], [B_GITSERVER, B_CLUSTER], "xe",
  block_kw=["real supported", "control planes", "controller compatibility", "production-like"])
c(42, "Contract tests for all public interfaces", ["tests/test_contracts.py", "tests/contract_fixtures.json"],
  [f"{K}.TestContractFixtures", f"{K}.TestSchemas", f"{K}.TestErrors"], [], "ieL",
  lacks=["n-1", "consumer/provider", "language-neutral"])
c(43, "Security/adversarial test suite", ["tests/test_security.py"],
  [f"{S}.TestAdversarial", f"{S}.TestAuthz", f"{S}.TestTenancy", f"{S}.TestParsers", f"{S}.TestNetsec"], [], "aeL")
c(44, "Fuzz testing", ["tests/test_e2e.py", "tests/fuzz_corpus/anchor_alias.yaml"], [f"{E2}.TestFuzz"], [], "aeL",
  lacks=["minimization", "provenance", "policy inputs", "apis", "schemas"])
c(45, "Fault-injection/chaos tests", ["tests/test_e2e.py"], [f"{E2}.TestFaultInjection", f"{O}.TestTime"], [B_KMS],
  "kxeL", block_kw=["kms", "database", "dns/tls"])
c(46, "Scale/soak/burst benchmarks", ["tools/bench.py"], [f"{TT}.TestBench"], [B_FLEET], "me",
  block_kw=["long-duration", "tenant/target scale", "network"])
c(47, "Release regression gates", ["tools/gates.py"], [f"{TT}.TestRegressionGate"], [B_OWNER], "e",
  lacks=["migration", "vulnerability", "reliability"])
c(48, "Cross-platform/runtime certification", ["tools/gates.py"], [f"{TT}.TestPlatform"], [B_PLATFORMS], "e",
  block_kw=["container runtime", "kubernetes", "cpu"])
c(49, "Coverage/reporting artifacts", ["tools/gates.py"], [f"{TT}.TestCoverage", f"{TT}.TestLint"], [], "eL",
  lacks=["branch", "mutation", "type", "risk-weighted"])
c(50, "Full checklist evidence bundle", ["checklist/engine.py", "tools/gates.py", "tools/master.py"],
  [f"{TT}.TestEvidence", "test_checklist_engine.TestEngine"], [B_OWNER], "eL", lacks=["provenance"])
c(51, "MASTER.md", ["tools/master.py"], [f"{TT}.TestDocs"], [B_MASTER], "de", block_kw=["canonical"])
c(52, "Standalone packaging metadata", ["tools/gates.py"], [f"{TT}.TestPackaging"], [], "eL",
  lacks=["isolated", "sdist"])
c(53, "License/NOTICE files", ["tools/gates.py"], [f"{TT}.TestSBOM", f"{TT}.TestDocs"], [B_LICENSE], "e",
  block_kw=["governing license", "contribution"])
c(54, "Generated API/reference documentation", ["tools/gates.py", "docs/API_REFERENCE.md"], [f"{TT}.TestDocs"], [],
  "deiL", lacks=["executable examples", "ci validation"])
