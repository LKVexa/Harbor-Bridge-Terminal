"""Single source of truth: the 64 MC components -> artifacts, tests, status, blockers.

``status`` uses the checklist vocabulary.  Nothing is ``PASS``: the checklist's
universal definition of done needs a named owner/approver and verification on
an immutable release candidate in the target environment, neither of which
exists in this pass.  ``local`` records what was implemented and verified here.
"""
from __future__ import annotations

OWNER_BLOCKER = "accountable owner/approver not assigned (universal DoD)"
KVM = "requires approved KVM host run (real-host integration tests are NOT_TESTED)"
PIN = "Firecracker/jailer/kernel/rootfs release + SHA-256 pins not approved"
STAGING = "requires staging/fleet exercise"
SIGN = "requires organisational signing identity"

P = "inv24_microvm_runtime/"
T = "inv24_microvm_runtime.tests."

# id: (local_implementation, artifacts, test_prefixes, extra_blockers, notes)
C: dict[str, tuple[str, list[str], list[str], list[str], str]] = {
 "MC-001": ("COMPLETE", [P+"adapters/firecracker.py", P+"supervision/vmm_process.py", "artifacts/firecracker/manifest.json", P+"tests/integration/test_firecracker_adapter.py"],
            [T+"unit.test_firecracker_adapter"], [PIN, KVM], "typed adapter + supervisor verified against a stub VMM over a real Unix socket"),
 "MC-002": ("COMPLETE", [P+"virtualization/kvm.py", "docs/KVM_PREREQUISITES.md", P+"tests/integration/test_kvm_preflight.py"],
            [T+"unit.test_host_devices_io.KvmTest"], [KVM], "real ioctl probe; fake-KVM matrix covers absent/denied/busy/revoked/incompatible"),
 "MC-003": ("PARTIAL", [P+"devices/specs.py", P+"schemas/PK_MICROVM_DEVICE_V1.json", P+"tests/integration/test_device_backends.py"],
            [T+"unit.test_host_devices_io.DeviceTest"], [KVM, "TAP/netns provisioning fixture not supplied"], "typed specs + ownership registry; e2e boot per device pending"),
 "MC-004": ("PARTIAL", [P+"snapshot/store.py", P+"schemas/PK_MICROVM_SNAPSHOT_V1.json", "docs/SNAPSHOT_RECOVERY.md", P+"tests/integration/test_snapshot_restore.py"],
            [T+"unit.test_config_snapshot_obs.SnapshotTest"], [PIN, KVM, "adapter /snapshot/create and /snapshot/load calls not wired"], "metadata, crash-consistent commit, restore validation"),
 "MC-005": ("PARTIAL", [P+"admission/controller.py", P+"schemas/PK_MICROVM_ADMISSION_V1.json", P+"tests/integration/test_execution_plane_admission.py"],
            [T+"unit.test_admission_resilience.AdmissionTest"], ["PLN-04 client binding / real contract not supplied"], "controller complete against the published contract"),
 "MC-006": ("PARTIAL", [P+"io/datapath.py", P+"tests/integration/test_inv35_datapath.py"],
            [T+"unit.test_host_devices_io.DatapathTest"], ["INV-35 not installed", "benchmark profile not approved"], "negotiation/fallback + bounds; acceleration benefit unproven"),
 "MC-007": ("DOCUMENT_ONLY", ["docs/OWNERS.md", "CODEOWNERS"], [], ["names must be supplied by the organisation"], "structure present, holders UNASSIGNED"),
 "MC-008": ("DOCUMENT_ONLY", ["docs/ADR-0001-firecracker-vmm.md"], [], ["ADR approval signatures missing"], "PROPOSED"),
 "MC-009": ("DOCUMENT_ONLY", ["docs/REQUIREMENTS.md"], [], ["requirements review/approval"], "SHALL set per environment + precedence"),
 "MC-010": ("COMPLETE", ["traceability/TRACEABILITY.json", "tools/components.py"], [T+"unit"], [], "generated, mechanically resolved by the gate"),
 "MC-011": ("DOCUMENT_ONLY", ["docs/COMPATIBILITY.md", "release/compatibility.json"], [], ["matrix cells NOT_TESTED", "pk_core version unpinned"], ""),
 "MC-012": ("DOCUMENT_ONLY", ["docs/INTERFACES.md"], [], [], "20-boundary catalog"),
 "MC-013": ("COMPLETE", [P+"schemas/"], [T+"unit.test_config_snapshot_obs.SchemaContractTest"], [], "10 JSON Schemas + bounded validator + conformance tests"),
 "MC-014": ("DOCUMENT_ONLY", ["docs/MASTER.md", "docs/checklist/INV24_v4.2.0_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST.md"], [], ["original master prompt absent (P2 disposition)"], ""),
 "MC-015": ("COMPLETE", [P+"config/loader.py", "config/base.json", "config/overlays.json", "docs/CONFIGURATION.md"],
            [T+"unit.test_config_snapshot_obs.ConfigTest"], [], "narrow-only overlays, provenance, transactional activate/rollback"),
 "MC-016": ("COMPLETE", [P+"security/secrets.py", "tools/secret_scan.py"], [T+"unit.test_security.SecretsTest"], ["production secret provider binding"], ""),
 "MC-017": ("PARTIAL", ["pyproject.toml", "requirements.lock", "tools/bootstrap.sh"], [], ["offline install verification on clean host"], ""),
 "MC-018": ("PARTIAL", [P+"security/artifacts.py", "artifacts/firecracker/manifest.json", "docs/SUPPLY_CHAIN.md"],
            [T+"unit.test_firecracker_adapter.ArtifactGateTest"], [PIN, SIGN], "SBOM + digests emitted by run_evidence; signing pending"),
 "MC-019": ("DOCUMENT_ONLY", ["NOTICE"], [], ["owner must choose licence"], "no LICENSE file by design — not invented"),
 "MC-020": ("DOCUMENT_ONLY", ["docs/THREAT_MODEL.md"], [T+"unit.test_security"], ["security review sign-off"], ""),
 "MC-021": ("PARTIAL", [P+"security/identity.py"], [T+"unit.test_security.IdentityTest"], ["mTLS/SPIFFE or attested identity (DEBT-021)"], "HMAC tokens fail closed"),
 "MC-022": ("PARTIAL", [P+"security/identity.py", P+"security/isolation.py"], [T+"unit.test_security.IsolationTest", T+"unit.test_security.IdentityTest"], [KVM], "capability model + jailer/cgroup/seccomp policy"),
 "MC-023": ("PARTIAL", [P+"security/isolation.py", P+"devices/specs.py"], [T+"unit.test_security.IsolationTest", T+"unit.test_host_devices_io.DeviceTest"], [KVM], "policy + live verifier; real jailed-process evidence pending"),
 "MC-024": ("PARTIAL", [P+"security/keys.py"], [T+"unit.test_security.KeyTest"], ["KMS/HSM adapter", "transport/at-rest encryption not in scope of local code"], "keyring rotation + fail closed"),
 "MC-025": ("COMPLETE", [P+"security/audit.py"], [T+"unit.test_security.AuditTest"], ["WORM/off-host shipping"], ""),
 "MC-026": ("PARTIAL", [P+"tests/unit/test_security.py", P+"tests/unit/test_property_fuzz_faults.py"], [T+"unit.test_security.AdversarialTest", T+"unit.test_property_fuzz_faults"], [KVM, "guest-side escape/side-channel tests"], ""),
 "MC-027": ("COMPLETE", [P+"resilience/health.py"], [T+"unit.test_admission_resilience.HealthTest"], ["guest agent heartbeat source"], ""),
 "MC-028": ("COMPLETE", [P+"resilience/retry.py", P+"resilience/lease.py"], [T+"unit.test_admission_resilience.RetryBreakerTest", T+"unit.test_admission_resilience.AdmissionTest.test_idempotent_retry_and_restart"], [], ""),
 "MC-029": ("COMPLETE", [P+"admission/controller.py", P+"resilience/breaker.py"], [T+"unit.test_admission_resilience.AdmissionTest.test_overload_is_bounded_and_fair", T+"unit.test_admission_resilience.RetryBreakerTest.test_breaker_open_half_open_close"], [], ""),
 "MC-030": ("PARTIAL", [P+"resilience/controls.py", "docs/REQUIREMENTS.md"], [T+"unit.test_admission_resilience.ControlsTest"], ["scheduler failover belongs to PLN-04", STAGING], ""),
 "MC-031": ("COMPLETE", [P+"resilience/lease.py"], [T+"unit.test_admission_resilience.LeaseTest"], ["multi-node lease backend (file lease is single-host)"], ""),
 "MC-032": ("COMPLETE", [P+"resilience/controls.py"], [T+"unit.test_admission_resilience.ControlsTest"], [STAGING], ""),
 "MC-033": ("PARTIAL", [P+"tests/unit/test_property_fuzz_faults.py"], [T+"unit.test_property_fuzz_faults.FaultInjectionTest"], [KVM, "node loss / partition on real fleet"], ""),
 "MC-034": ("PARTIAL", [P+"perf/bench.py", "tools/run_evidence.py", "benchmarks/baseline.json"], [], [KVM], "control-path baselines on this host only"),
 "MC-035": ("PARTIAL", [P+"perf/bench.py", "docs/PERFORMANCE.md"], [], [KVM], "targets declared; real cold-boot tails NOT_TESTED"),
 "MC-036": ("DOCUMENT_ONLY", ["docs/PERFORMANCE.md"], [], ["profiling on real host"], "P2"),
 "MC-037": ("COMPLETE", [P+"admission/controller.py", "docs/PERFORMANCE.md", P+"devices/specs.py"], [T+"unit.test_admission_resilience.AdmissionTest.test_quota_fleet_tenant_and_headroom", T+"unit.test_admission_resilience.AdmissionTest.test_concurrent_admissions_never_exceed_caps"], [], ""),
 "MC-038": ("DOCUMENT_ONLY", ["docs/PERFORMANCE.md", "release/WAIVERS.json"], [], ["far-edge measurement (DEBT-038)"], "P2; NOT_APPLICABLE proposed for cloud/datacenter"),
 "MC-039": ("COMPLETE", [P+"perf/bench.py", "tools/production_gate.py"], [], ["baseline must be re-captured on the release runner"], ""),
 "MC-040": ("COMPLETE", [P+"observability/metrics.py"], [T+"unit.test_config_snapshot_obs.TelemetryTest.test_metrics_exposition_and_cardinality_cap"], ["scrape endpoint wiring in host service"], ""),
 "MC-041": ("COMPLETE", [P+"observability/logging.py"], [T+"unit.test_config_snapshot_obs.TelemetryTest.test_structured_log_correlation_and_redaction"], [], ""),
 "MC-042": ("COMPLETE", [P+"observability/tracing.py"], [T+"unit.test_config_snapshot_obs.TelemetryTest.test_trace_propagation"], ["exporter (OTLP) binding"], ""),
 "MC-043": ("COMPLETE", [P+"security/secrets.py", P+"observability/metrics.py", "docs/TELEMETRY_POLICY.md"], [T+"unit.test_security.SecretsTest", T+"unit.test_config_snapshot_obs.TelemetryTest"], [], ""),
 "MC-044": ("COMPLETE", [P+"observability/explain.py", P+"admission/controller.py"], [T+"unit.test_admission_resilience.AdmissionTest.test_accept_and_decision_record"], ["live infrastructure graph linkage"], ""),
 "MC-045": ("DOCUMENT_ONLY", ["docs/TELEMETRY_POLICY.md"], [], ["privacy/security approval"], ""),
 "MC-046": ("DOCUMENT_ONLY", ["observability/dashboards/inv24-overview.json", "observability/alerts/inv24-rules.yaml"], [], ["load into monitoring stack + alert drill"], ""),
 "MC-047": ("COMPLETE", [P+"tests/unit/test_config_snapshot_obs.py"], [T+"unit.test_config_snapshot_obs.SchemaContractTest"], [], ""),
 "MC-048": ("PARTIAL", [P+"tests/integration/"], [], [KVM, "PLN-04 / INV-35 not available"], "suites present, all NOT_TESTED here"),
 "MC-049": ("DOCUMENT_ONLY", ["release/compatibility.json", ".github/workflows/ci.yml"], [], ["aarch64 + Firecracker-version matrix runners"], "CI python matrix defined"),
 "MC-050": ("COMPLETE", [P+"tests/unit/test_property_fuzz_faults.py"], [T+"unit.test_property_fuzz_faults.PropertyTest"], [], "seeded; found and fixed a non-ASCII MAC crash in keys.verify"),
 "MC-051": ("COMPLETE", [P+"tests/unit/test_admission_resilience.py"], [T+"unit.test_admission_resilience.AdmissionTest.test_concurrent_admissions_never_exceed_caps", T+"unit.test_admission_resilience.LeaseTest.test_concurrent_acquire_single_winner"], [], "synchronisation contract: controller/registry/keyring/audit are thread-safe; MicroVM is single-owner"),
 "MC-052": ("NONE", [], [], [KVM, STAGING], "soak/burst/fleet absent"),
 "MC-053": ("PARTIAL", [P+"tests/unit/test_admission_resilience.py"], [T+"unit.test_admission_resilience.LeaseTest.test_fencing_and_takeover"], [STAGING], "partition/fencing simulated in-process"),
 "MC-054": ("COMPLETE", ["tools/run_evidence.py", P+"schemas/PK_MICROVM_EVIDENCE_V1.json", "evidence/"], [], [], ""),
 "MC-055": ("PARTIAL", [".github/workflows/ci.yml"], [], ["CI not executed in a hosted runner from this archive"], ""),
 "MC-056": ("DOCUMENT_ONLY", ["docs/SLO.md"], [], ["support ownership"], ""),
 "MC-057": ("DOCUMENT_ONLY", ["docs/ROLLOUT.md"], [], [STAGING], ""),
 "MC-058": ("DOCUMENT_ONLY", ["docs/SECURITY_POLICY.md"], [], ["security contact"], ""),
 "MC-059": ("DOCUMENT_ONLY", ["docs/RUNBOOKS.md", "docs/SNAPSHOT_RECOVERY.md"], [], [STAGING], ""),
 "MC-060": ("DOCUMENT_ONLY", ["docs/RUNBOOKS.md"], [], [STAGING], ""),
 "MC-061": ("DOCUMENT_ONLY", ["docs/INCIDENT_RESPONSE.md"], [], ["paging integration + tabletop"], ""),
 "MC-062": ("DOCUMENT_ONLY", ["docs/REVIEWS.md", "release/REVIEW_TEMPLATE.json"], [], [], ""),
 "MC-063": ("COMPLETE", ["release/WAIVERS.json", "tools/production_gate.py"], [], [], "gate enforces owner/approver/expiry"),
 "MC-064": ("COMPLETE", ["release/PRODUCTION_EXIT_GATE.json", "tools/production_gate.py", "evidence/production-gate.json"], [], [], "deterministic; yields NO_GO while any P0 is not PASS"),
}
