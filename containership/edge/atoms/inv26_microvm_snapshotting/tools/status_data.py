"""Per-control status for the INV-26 v5.0.0 missing-component checklist (87 controls + C086 + X001-X014).

Vocabulary (never "COMPLETE": every item's acceptance package requires an owner/reviewer sign-off, and
no owner is assigned):
  IMPLEMENTED_LOCAL   code/spec + automated tests + machine-readable evidence exist in this repository;
                      only independent review/sign-off is outstanding
  PARTIAL             part of the engineering checklist is implemented and evidenced; named gaps remain
  BLOCKED_EXTERNAL    the remaining work needs something this build cannot have (KVM/real VMM, managed KMS,
                      fleet, pk_core, a second release)
  GOVERNANCE_PENDING  artifacts exist; completion needs named humans, approvals or performed reviews

Each row: (status, artifacts, tests, evidence, gaps)
"""
from __future__ import annotations

S = {}


def row(cid, status, artifacts, tests, evidence, gaps):
    S[cid] = {"status": status, "artifacts": artifacts, "tests": tests, "evidence": evidence, "gaps": gaps}


IL, P, BE, GP = "IMPLEMENTED_LOCAL", "PARTIAL", "BLOCKED_EXTERNAL", "GOVERNANCE_PENDING"
T_SVC, T_SEC, T_CON, T_ADP, T_FUZ = ("tests/test_service.py", "tests/test_security_units.py",
                                     "tests/test_concurrency.py", "tests/test_adapters.py", "tests/test_fuzz.py")

row("C009", GP, ["ops/ownership.json", "CODEOWNERS", "tools/governance_check.py", "GOVERNANCE.md"], [],
    ["evidence/GOVERNANCE.json"], ["no person assigned to any role", "no paging route", "escalation drill not performed"])
row("C010", GP, ["ADR-0001-microvm-snapshotting.md"], [], [],
    ["ADR status PROPOSED: architecture/security/operations approval pending",
     "comparison is qualitative; no measured VMM comparison (no KVM)"])
row("C012", IL, ["policy.py", "ops/policy.json", "APPLICABILITY.md"], [f"{T_SVC}::Precedence.test_tier_applicability"],
    ["evidence/TESTS.json"], ["tier targets PROPOSED; TPM/attestation per tier specified but not enforced (C044)"])
row("C014", IL, ["errors.py", "ERRORS.json", "SEMANTICS.md", "service.py"], [f"{T_SVC}::Outcomes", f"{T_SVC}::OperatorControls"],
    ["evidence/TESTS.json", "evidence/FAULTS.json"], ["degraded_success/partial_success are reserved, never emitted"])
row("C015", IL, ["lifecycle.py", "ops/lifecycle.json", "SEMANTICS.md"], [f"{T_SEC}::LifecycleTests", "tools/faults.py crash_matrix"],
    ["evidence/FAULTS.json"], ["distributed multi-controller ownership limited to lease/fencing on a shared-filesystem metastore"])
row("C016", P, ["compatibility.json", "COMPATIBILITY.md", "schema.py"], [f"{T_SVC}::Boundaries.test_unknown_fields_and_versions_rejected",
    f"{T_SEC}::SchemaTests.test_conformance_fixtures"], ["evidence/TESTS.json"],
    ["no N+1 fixtures", "no CI job diffing schemas against the previous release (only one release exists)"])
row("C017", IL, ["config.py (quotas, admission)", "resilience.py", "service.gc", "CONFIGURATION.md"],
    [f"{T_SVC}::Admission", f"{T_SVC}::CaptureSemantics.test_quota_rejects_before_hypervisor_work", f"{T_SVC}::MetadataGC",
     f"{T_CON}::ThreadRaces.test_admission_ceiling_holds"], ["evidence/BENCH.json", "evidence/SOAK.json"],
    ["weighted fair queueing not implemented (per-tenant slot cap + token bucket instead)", "KMS request quota is implicit via admission"])
row("C018", P, ["OFFLINE.md", "policy.OUTAGE", "service.reconcile"], ["tools/faults.py dependency_matrix"], ["evidence/FAULTS.json"],
    ["no local KMS replica for edge", "no multi-node partition/reconnect test", "no clock-discontinuity test beyond skew checks"])
row("C019", IL, ["policy.PRECEDENCE/CONFLICTS", "APPLICABILITY.md", "explain.py"], [f"{T_SVC}::Precedence"],
    ["evidence/TESTS.json"], ["policy changes are versioned by POLICY_VERSION in code, not a separately signed bundle"])
row("C020", IL, ["tools/rtm.py", "tools/status_data.py", "REQUIREMENTS_TRACEABILITY.md", "evidence/RTM.json"],
    ["tools/rtm.py --check (in CI)"], ["evidence/RTM.json"], ["RTM hash is in the signed SHA256SUMS; signer is ephemeral"])
row("C021", IL, ["ops/boundaries.json", "INTERFACES.md"], ["tools/rtm.py boundary check"], ["evidence/RTM.json"],
    ["diagram is hand-maintained Mermaid (CI checks boundary ids referenced, not the drawing)"])
row("C022", IL, ["schema.py", "schemas/*.schema.json", "schema.canonical_bytes"], [f"{T_SEC}::SchemaTests", f"{T_FUZ}"],
    ["evidence/SCHEMAS.json", "evidence/FUZZ.json"], ["no generated typed bindings for other languages"])
row("C023", P, ["auth.py", "SECURITY.md"], [f"{T_SEC}::AuthTests"], ["evidence/TESTS.json"],
    ["no mTLS/SPIFFE transport identity", "no automated rotation/distribution of trust roots", "local-socket peer-credential checks are the deployer's"])
row("C024", IL, ["auth.authorize", "service._preamble"], [f"{T_SEC}::AuthTests.test_authorization_matrix",
    f"{T_SVC}::Boundaries.test_caller_scope_cannot_be_bypassed_by_request_fields", f"{T_SVC}::OperatorControls"],
    ["evidence/TESTS.json"], [])
row("C025", IL, ["resilience.py", "service.py", "INTERFACES.md"], [f"{T_SVC}::Outcomes.test_deadline_exceeded",
    f"{T_SVC}::Outcomes.test_cancel", f"{T_SVC}::AntiReplay", f"{T_CON}"], ["evidence/TESTS.json", "evidence/FAULTS.json"],
    ["cancellation cannot interrupt a blocking VMM/KMS call already in flight (checked between steps)"])
row("C026", IL, ["errors.py", "ERRORS.json"], [f"{T_SVC}::Outcomes.test_every_catalog_code_has_valid_envelope",
    f"{T_SVC}::Outcomes.test_unexpected_exception_does_not_leak", f"{T_SEC}::ErrorCatalogTests"], ["evidence/TESTS.json"], [])
row("C027", P, ["compatibility.json", "COMPATIBILITY.md"], [f"{T_SEC}::SchemaTests.test_conformance_fixtures"], [],
    ["no mixed-version rolling-upgrade/rollback test (single release)", "no runtime feature negotiation beyond major refusal"])
row("C028", IL, ["schema.py limits", "auth.MAX_TOKEN_BYTES", "INTERFACES.md#limits"], [f"{T_SEC}::SchemaTests.test_bounded_parse",
    f"{T_SVC}::CaptureSemantics.test_limits", f"{T_FUZ}"], ["evidence/FUZZ.json"], [])
row("C029", IL, ["examples/", "tests/fixtures/conformance/cases.json", "tools/gen_artifacts.py"],
    [f"{T_SEC}::SchemaTests.test_conformance_fixtures"], ["evidence/SCHEMAS.json"], ["no downstream adapter consumes the fixtures in CI"])
row("C030", BE, ["tests/test_adapters.py", "tests/fakes.py"], [f"{T_ADP}"], ["evidence/INTEGRATION.json"],
    ["only protocol fakes on real Unix sockets; no real VMM/KMS/object store; INV-24/INV-25 contracts not available"])
row("C031", P, ["compatibility.json", "requirements.lock", "evidence/sbom.cdx.json"], ["tools/release.py"], ["evidence/RELEASE.json"],
    ["VMM/guest-kernel/KMS versions are not pinned to digests (not present)", "pk_core unpinned (unknown)"])
row("C032", IL, ["CONFIGURATION.md#artifacts-vs-state", "storage.py", "metastore.py"], ["tools/release.py install check (read-only package)"],
    ["evidence/INSTALL.json"], ["read-only root filesystem run not performed"])
row("C033", IL, ["config.py", "examples/config.production.json", "examples/config.restrictive.json", "CONFIGURATION.md"],
    [f"{T_SEC}::ConfigTests"], ["evidence/TESTS.json"], [])
row("C034", IL, ["config.validate", "ConfigStore.activate"], [f"{T_SEC}::ConfigTests", f"{T_FUZ}"], ["evidence/FUZZ.json"], [])
row("C035", IL, ["config.compose"], [f"{T_SEC}::ConfigTests.test_overlay_order_and_emergency_scope"], ["evidence/TESTS.json"],
    ["artifact identity across environments is shown by one wheel digest; no multi-environment deployment exists"])
row("C036", IL, ["ConfigStore (provenance, history, governing)", "audit.py"], [f"{T_SEC}::ConfigTests.test_atomic_activation_provenance_rollback"],
    ["evidence/DRILLS.json"], [])
row("C037", IL, ["ConfigStore.activate", "metastore.py (WAL, CAS)"], [f"{T_SEC}::ConfigTests.test_crash_during_activation_is_all_or_nothing"],
    ["evidence/TESTS.json"], ["multi-node barrier semantics specified only (single-node metastore)"])
row("C038", P, ["ConfigStore.rollback", "ops/ROLLOUT_POLICY.json"], ["tools/drills.py rollback"], ["evidence/DRILLS.json"],
    ["software rollback between two releases not drilled (one release)", "canary/partial-fleet drill needs a fleet"])
row("C039", IL, ["redaction.py", "config.validate", "errors.envelope", "DATA_LIFECYCLE.md", "tools/secret_scan.py"],
    [f"{T_SVC}::Observability.test_no_secret_material_in_logs_audit_or_responses", f"{T_SEC}::ConfigTests.test_negative_values"],
    ["evidence/SECRET_SCAN.json"], ["no secret-provider adapter (only secretref:// references)", "CPython cannot zeroize immutable bytes"])
row("C040", P, ["tools/bootstrap.sh", "tools/preflight.py", "tools/smoke.py", "RUNBOOK.md#day-0"], ["CI bootstrap-smoke"],
    ["evidence/PREFLIGHT.json", "evidence/SMOKE.json"], ["clean-node run with KVM + Firecracker + encrypted capture/restore not performed"])
row("C041", GP, ["THREAT_MODEL.md"], ["tests/test_threats.py"], ["evidence/TESTS.json"], ["security-owner review pending"])
row("C042", P, ["ops/least_privilege.json", "SECURITY.md"], [f"{T_SVC}::Boundaries"], [],
    ["seccomp/capabilities/IAM enforcement is the deployer's; compromised-worker negative tests need the deployment"])
row("C043", P, ["hypervisor.HypervisorPort (brokered)", "ops/boundaries.json B12", "SECURITY.md"], [], [],
    ["no sandbox/policy-denial test harness (needs deployment sandbox)"])
row("C044", P, ["auth.TrustStore (role, trust domain, revocation)", "grant audience=node"],
    [f"{T_SEC}::AuthTests.test_revocation_and_trust_domain_and_role"], ["evidence/TESTS.json"],
    ["no hardware attestation", "no out-of-band trust-anchor verification tooling", "storage/KMS provider authentication is the adapters'"])
row("C045", P, ["provenance.py", "tools/release.py"], ["tools/release.py verify (tamper test)"], ["evidence/RELEASE.json"],
    ["ephemeral signer (no publisher identity)", "consumed-artifact allowlist of builder identities not enforced"])
row("C047", P, ["crypto.py", "service.rewrap_all"], [f"{T_SEC}::CryptoTests", f"{T_SVC}::HappyPath.test_blob_at_rest_is_ciphertext"],
    ["evidence/DRILLS.json"], ["LocalKeyService is not a managed KMS", "in-transit TLS belongs to remote adapters (none)"])
row("C048", IL, ["policy.OUTAGE", "OFFLINE.md", "telemetry.Health"], ["tools/faults.py dependency_matrix"], ["evidence/FAULTS.json"],
    ["attestation/time services modelled but not present"])
row("C049", IL, ["audit.py (hash chain, HMAC, anchor)", "service.py (audit events)"],
    [f"{T_SVC}::Observability.test_audit_chain_verifies_and_detects_tamper", f"{T_SVC}::OperatorControls.test_privileged_ops_fail_closed_without_audit"],
    ["evidence/AUDIT_VERIFY.json"], ["anchor must be copied off-node (WORM/audit service not included)"])
row("C050", P, ["tests/test_threats.py", "tools/fuzz.py"], ["tests/*"], ["evidence/FUZZ.json"],
    ["no side-channel, escape or local privilege-escalation testing (needs real VMM/host)"])
row("C051", IL, ["FAILURE_MODEL.md"], ["tools/faults.py"], ["evidence/FAULTS.json"], ["node/site loss rows state 'no failover' (C055)"])
row("C052", IL, ["telemetry.Health", "service.stalled", "lifecycle.STATE_TIMEOUT_S", "ops/alerts.json"],
    [f"{T_SVC}::Observability.test_health_metrics_logs_explain"], ["evidence/DRILLS.json"], [])
row("C053", IL, ["resilience.retry", "RetryBudget"], ["tools/faults.py breaker", f"{T_SVC}::Outcomes.test_hypervisor_failure_on_load"],
    ["evidence/FAULTS.json"], [])
row("C054", IL, ["resilience.Admission", "CircuitBreaker"], [f"{T_SVC}::Admission", f"{T_CON}::ThreadRaces.test_admission_ceiling_holds"],
    ["evidence/FAULTS.json", "evidence/BENCH.json"], [])
row("C055", BE, ["FAILURE_MODEL.md F15/F16", "APPLICABILITY.md (replication prohibited)"], [], [],
    ["no failover: node-local storage adapter only; cross-node restore needs shared storage + residency approval"])
row("C056", IL, ["policy.OUTAGE (telemetry/audit degrade)", "telemetry.Health degraded"], ["tools/faults.py audit_sink_down"],
    ["evidence/FAULTS.json"], [])
row("C057", IL, ["metastore.py", "service.reconcile", "lifecycle.recovery_action"], ["tools/faults.py crash_matrix", f"{T_SVC}::Recovery"],
    ["evidence/FAULTS.json"], [])
row("C058", IL, ["metastore leases/fencing", "grant CAS"], [f"{T_CON}::ProcessRaces", f"{T_CON}::ThreadRaces"], ["evidence/STRESS.json"],
    ["fencing is enforced on metastore writes; VMM-side fencing is INV-24's"])
row("C059", IL, ["service quarantine/release/disable/scrub"], [f"{T_SVC}::OperatorControls", f"{T_SVC}::Scrub"], ["evidence/DRILLS.json"], [])
row("C060", IL, ["tools/faults.py"], ["tools/faults.py"], ["evidence/FAULTS.json"], ["real-VMM fault injection pending (X001)"])
row("C061", P, ["tools/bench.py", "BENCHMARKS.md"], ["tools/bench.py"], ["evidence/BENCH.json"],
    ["reference VMM only: VMM cost, network and power excluded"])
row("C062", P, ["BENCHMARKS.md (p50/p95/p99/max)", "SLO.md"], [], ["evidence/BENCH.json"], ["thresholds PROPOSED, not approved; no real-VMM numbers"])
row("C063", P, ["tools/bench.py load scenarios", "tools/soak.py"], [], ["evidence/BENCH.json", "evidence/SOAK.json"],
    ["no scale-out/scale-in (single node)", "overload measured via admission only"])
row("C064", P, ["tools/bench.py breakdown", "metrics tenant labels"], [], ["evidence/BENCH.json"], ["per-tenant CPU/memory accounting not exported"])
row("C065", IL, ["BENCHMARKS.md#copies", "tools/bench.py breakdown"], [], ["evidence/BENCH.json"], [])
row("C066", P, ["crypto.open_envelope (digest off hot path, memoryview)"], [f"{T_SEC}::CryptoTests"], ["evidence/BENCH.json", "evidence/BENCH_PRE_OPT.json"],
    ["streaming decrypt into VMM memory file / UFFD not implemented (DEBT-1)"])
row("C067", IL, ["INTERFACES.md#limits", "service.gc", "Admission tenant table cap", "telemetry series cap"],
    ["tools/soak.py", f"{T_SVC}::MetadataGC"], ["evidence/SOAK.json"], ["plaintext image held fully in memory (DEBT-1)"])
row("C068", BE, [], [], [], ["no constrained edge hardware or power/thermal instrumentation available"])
row("C069", P, ["BENCHMARKS.md#capacity"], [], ["evidence/BENCH.json"], ["capacity model derived from reference-path throughput only"])
row("C070", P, ["tools/bench.py --compare", "bench/baseline.json"], ["CI perf-gate"], ["evidence/PERF_GATE.json"],
    ["gates INV-26 overhead only; startup/density/tail thresholds on real VMM unapproved"])
row("C071", IL, ["telemetry.Health", "service.health"], [f"{T_SVC}::Observability", f"{T_SVC}::OperatorControls.test_emergency_disable"],
    ["evidence/TESTS.json"], ["no HTTP endpoint (in-process API)"])
row("C072", IL, ["telemetry.Metrics", "ops/metrics.json"], [f"{T_SVC}::Observability.test_health_metrics_logs_explain"], ["evidence/TESTS.json"], [])
row("C073", IL, ["telemetry.StructuredLogger"], [f"{T_SVC}::Observability.test_health_metrics_logs_explain"], ["evidence/TESTS.json"], [])
row("C074", P, ["telemetry traceparent", "service.handle"], [f"{T_SVC}::Observability.test_trace_context_continues"], ["evidence/TESTS.json"],
    ["cannot propagate into VMM/KMS APIs; no trace exporter"])
row("C075", IL, ["telemetry label policy", "explain decision records"], [f"{T_SVC}::Observability.test_lineage_is_allowlisted_and_redacted"],
    ["evidence/TESTS.json"], [])
row("C076", IL, ["explain.DecisionRecorder", "audit decision.* events"], [f"{T_SVC}::Observability.test_health_metrics_logs_explain"],
    ["evidence/TESTS.json"], [])
row("C077", IL, ["service.explain", "explain.render_text"], [f"{T_SVC}::Observability.test_health_metrics_logs_explain"], ["evidence/TESTS.json"], [])
row("C078", P, ["explain.lineage"], [f"{T_SVC}::Observability.test_lineage_is_allowlisted_and_redacted"], [],
    ["no live infrastructure graph to correlate with"])
row("C079", GP, ["OBSERVABILITY.md#telemetry-policy"], [], [], ["retention values proposed; privacy/legal approval pending"])
row("C080", P, ["ops/alerts.json", "dashboards/inv26-overview.json"], ["tools/drills.py alerts"], ["evidence/DRILLS.json"],
    ["dashboards not deployed; alert routing unassigned"])
row("C082", IL, ["tests/test_service.py", "tests/fixtures/conformance"], [f"{T_SVC}", f"{T_SEC}::SchemaTests"], ["evidence/TESTS.json"], [])
row("C083", BE, ["tests/test_adapters.py"], [f"{T_ADP}"], ["evidence/INTEGRATION.json"],
    ["adjacent layers (INV-24, INV-25, KMS, storage) not available; protocol fakes only"])
row("C084", BE, ["compatibility.json tested_matrix"], [], [], ["one OS/arch/Python; no aarch64, no real VMM versions"])
row("C085", IL, ["tools/fuzz.py"], [f"{T_FUZ}"], ["evidence/FUZZ.json"], ["mutation fuzzer (stdlib), not coverage-guided"])
row("C086", P, ["tests/test_concurrency.py"], [f"{T_CON}"], ["evidence/STRESS.json"],
    ["thread + multi-process races covered; distributed multi-node races need a cluster"])
row("C087", IL, ["THREAT_MODEL.md", "tests/test_threats.py"], ["tests/test_threats.py"], ["evidence/TESTS.json"],
    ["T18 (VMM escape/side channels) explicitly out of scope"])
row("C088", P, ["tools/bench.py", "tools/soak.py"], [], ["evidence/BENCH.json", "evidence/SOAK.json"],
    ["soak < 1 h, reference VMM, single node (no fleet-scale)"])
row("C089", P, ["tools/faults.py", "tools/drills.py backup_restore"], [], ["evidence/FAULTS.json", "evidence/DRILLS.json"],
    ["no multi-node partition/reconnect or control-plane degradation test"])
row("C090", IL, ["tools/gate.py", "tools/run_evidence.py"], ["tools/gate.py self-test (tampered evidence)"], ["evidence/EXIT_GATE.json"],
    ["pk_core gate cannot execute (X013)"])
row("C091", GP, ["SLO.md"], [], [], ["SLOs proposed; restore-time SLO unmeasured on real VMM and not supportable above ~4 MiB as specified"])
row("C092", P, ["ops/ROLLOUT_POLICY.json", "RUNBOOK.md#day-1"], ["tools/drills.py emergency"], ["evidence/DRILLS.json"],
    ["canary/staged rollout not exercised (no fleet)"])
row("C093", IL, ["compatibility.json", "COMPATIBILITY.md"], ["tools/rtm.py compat check"], ["evidence/RTM.json"], ["peer ranges untested on real peers"])
row("C094", GP, ["SECURITY_RESPONSE.md"], [], [], ["SLAs proposed; no reporting channel or security owner"])
row("C095", IL, ["BACKUP_RESTORE.md", "MetaStore.export/import_backup", "service.scrub"], ["tools/drills.py backup_restore", f"{T_SVC}::Scrub"],
    ["evidence/DRILLS.json"], [])
row("C096", P, ["RUNBOOK.md"], ["tools/smoke.py"], ["evidence/SMOKE.json"], ["not exercised by an operator; production day-0 needs KVM"])
row("C097", GP, ["INCIDENT_RESPONSE.md", "ops/ownership.json escalation"], [], [], ["paging destinations unassigned; no drill"])
row("C098", GP, ["ops/REVIEWS.json"], ["tools/governance_check.py"], ["evidence/GOVERNANCE.json"], ["no review performed"])
row("C099", GP, ["ops/REGISTER.json"], ["tools/governance_check.py"], ["evidence/GOVERNANCE.json"], ["waivers lack approver/expiry"])
row("C100", IL, ["tools/gate.py", "GOVERNANCE.md"], ["tools/gate.py"], ["evidence/EXIT_GATE.json"],
    ["gate verdict is NO_GO by construction until blockers close"])

X = {}


def xrow(xid, status, artifacts, gaps):
    X[xid] = {"status": status, "artifacts": artifacts, "gaps": gaps}


xrow("X001", BE, ["hypervisor.FirecrackerAdapter", "hypervisor.CloudHypervisorAdapter", "tests/fakes.py", "tests/test_adapters.py"],
     ["never run against a real VMM (no /dev/kvm)", "CPU-feature/page-size compatibility checks rely on the VMM refusing"])
xrow("X002", P, ["hypervisor.VsockAgentInjector (proof-of-receipt)", "service: READY only after ack"],
     ["in-guest agent not in repo (DEBT-2)", "VMGenID not driven"])
xrow("X003", P, ["storage.BlobStore port", "storage.FilesystemBlobStore (atomic, fsync, 0600, quota)"],
     ["object-store adapter not implemented"])
xrow("X004", IL, ["pyproject.toml", "requirements.lock", "tools/release.py (wheel, sdist, SBOM, SHA256SUMS, DSSE)"],
     ["build not bit-reproducible across hosts (timestamps normalised via SOURCE_DATE_EPOCH only for sdist)"])
xrow("X005", BE, ["provenance.py", "tools/release.py verify"], ["no managed signer; ephemeral key"])
xrow("X006", P, ["crypto.KeyService port", "crypto.LocalKeyService (versions, rotate, rewrap, disable, destroy)"],
     ["no cloud KMS/HSM adapter (WAIVER-2)"])
xrow("X007", BE, [], ["no attestation provider; trust-domain binding only"])
xrow("X008", IL, ["auth.verify_grant", "service grant CAS", "gc keeps nonces until expiry"],
     ["grant issuer (control plane) not in repo; tests issue grants with a test key"])
xrow("X009", IL, ["crypto.seal_envelope/open_envelope"], ["temp plaintext relies on tmpfs (deployer)"])
xrow("X010", P, ["DATA_LIFECYCLE.md", "delete crypto-erase", "hypervisor.wipe", "storage.delete overwrite"],
     ["forensic canary scan of swap/page cache not possible here"])
xrow("X011", IL, ["metastore.py (WAL, CAS, leases, export/import)", "service.reconcile"], ["shared-filesystem only; no replicated store"])
xrow("X012", P, ["telemetry.py", "ops/alerts.json", "dashboards/"], ["no HTTP endpoint/exporter process; dashboards not deployed"])
xrow("X013", BE, ["tests/test_component.py (skips loudly)", "tools/gate.py treats skips as blockers"],
     ["pk_core distribution/version/digest unknown; not in the upload or on the lot"])
xrow("X014", BE, ["tools/bench.py (certifiable=false)", "tools/soak.py"], ["real hypervisor/storage/KMS benchmark impossible here"])
