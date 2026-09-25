"""v4.3.0 closure map: the single source for RTM, AUDIT_MATRIX update and closure ledger.

For each open row: implementation evidence (paths / path::symbol), tests, docs,
and the blockers that still prevent `present`.  Every row carries the
OWNER_APPROVAL blocker because the checklist's definition of done requires a
recorded owner/reviewer approval, which cannot be minted by the build.
"""
from __future__ import annotations

OWNER = "owner/reviewer approval not yet recorded (governance/APPROVALS.json)"
PK = "approved pinned pk_core unavailable; full certification path cannot run"
BACKEND = "needs a real production virtio/vhost backend or adjacent-layer build (WVR-002/WVR-003)"
HW = "needs physical far-edge hardware (WVR-001)"
LIC = "repository license not selected (governance/LICENSE_DECISION.json)"
ROLES = "OWNERS roles UNASSIGNED (governance/OWNERS.json)"
KEY = "evidence sealing key not provisioned; Sigstore signing is TD-002"

T_SEC = "tests/security/test_adversarial.py"
T_FLT = "tests/faults/test_faults.py"
T_CON = "tests/contracts/test_contracts.py"
T_UNIT = "tests/integration/test_units.py"
T_INT = "tests/integration/test_adjacent_layers.py"
T_PERF = "tests/performance/test_perf_gate.py"
T_FUZZ = "tests/fuzz/test_fuzz.py"
T_CC = "tests/concurrency/test_concurrency.py"
T_CMP = "tests/compatibility/test_matrix.py"
T_SBX = "tests/security/test_sandbox_policy.py"
T_REL = "tests/test_release_gate.py"
T_RI = "tests/test_repository_integrity.py"
ARCH = "docs/architecture/ARCHITECTURE.md"
REQ = "docs/requirements/INV-35_REQUIREMENTS.md"
PERF = "docs/performance/PERFORMANCE_MODEL.md"
OBS = "docs/observability/OBSERVABILITY.md"

# id: (implementation evidence, tests, docs, extra blockers, still_missing)
ROWS: dict[str, tuple[list[str], list[str], list[str], list[str], bool]] = {
    "C005": (["contract.py::assumptions"], [T_SEC, T_FLT], [ARCH + "#5"], [], False),
    "C009": (["governance/OWNERS.json", "CODEOWNERS", "SECURITY.md", "runtime/release.py::governance_findings"], [T_REL], [], [ROLES], False),
    "C010": (["docs/adr/ADR-0001-separate-orchestration-and-bulk-data-channels.md"], [T_SEC], [], ["ADR status is Proposed, not Accepted"], False),
    "C011": (["runtime/datapath.py::ControlPlane/Datapath"], [T_SEC, T_CON, T_FLT], [REQ + "#1"], [], False),
    "C012": (["runtime/config.py::PROFILES", "config/defaults/"], [T_UNIT, T_CMP], [REQ + "#2"], [], False),
    "C013": (["benchmarks/thresholds.json"], [T_PERF, T_FUZZ, T_CC], [REQ + "#3", "docs/operations/SLO.md"], [BACKEND], False),
    "C014": (["runtime/errors.py::Outcome", "schemas/errors/error_codes.json"], [T_CON], [REQ + "#4"], [], False),
    "C015": (["runtime/lifecycle.py::TRANSITIONS", "schemas/status/lifecycle.json"], [T_UNIT, T_CON], [], [], False),
    "C016": (["runtime/health.py::SUPPORTED", "schemas/errors/published_codes_4.3.0.json"], [T_CON], ["docs/requirements/COMPATIBILITY_POLICY.md"], [], False),
    "C017": (["runtime/policy.py::QuotaManager", "runtime/policy.py::TokenBucket"], [T_SEC], [REQ + "#5"], [], False),
    "C018": (["runtime/datapath.py::Runtime.control_plane_lost", "runtime/config.py::offline_policy"], [T_FLT], [REQ + "#6"], [], False),
    "C019": ([REQ + "#7"], [T_FLT], [], [], False),
    "C020": (["requirements/traceability.json", "tools/build_rtm.py"], [T_REL], [], [], False),
    "C021": (["docs/architecture/BOUNDARY_INVENTORY.md"], [T_INT, T_SEC], [], [], False),
    "C022": (["schemas/", "tools/gen_schemas.py", "runtime/schema_check.py"], [T_CON], [], [], False),
    "C023": (["runtime/security.py::Authority"], [T_SEC], ["docs/security/SECURITY_ARCHITECTURE.md"], [], False),
    "C024": (["runtime/security.py::Capability", "runtime/datapath.py::BULK_ACTIONS/CONTROL_ACTIONS"], [T_SEC], ["docs/security/SECURITY_ARCHITECTURE.md"], [], False),
    "C025": (["runtime/policy.py", "runtime/datapath.py::Datapath.submit"], [T_UNIT, T_FLT], ["docs/requirements/INTERFACE_CONTRACT.md"], [], False),
    "C026": (["runtime/errors.py", "schemas/errors/error.schema.json", "schemas/errors/error_codes.json"], [T_CON], [], [], False),
    "C027": (["runtime/health.py::negotiate"], [T_INT], ["docs/requirements/COMPATIBILITY_POLICY.md"], [], False),
    "C028": (["io_model.py::VirtQueue.depth_limit/chain_limit/byte_limit"], [T_SEC, T_UNIT], ["docs/requirements/INTERFACE_LIMITS.md"], [], False),
    "C029": (["fixtures/valid", "fixtures/invalid", "fixtures/adversarial", "tools/inv35ctl.py::smoke"], [T_CON], [], [], False),
    "C030": ([T_INT], [T_INT], ["docs/architecture/BOUNDARY_INVENTORY.md"], [BACKEND], False),
    "C031": (["release/NEXUS_SPEC_MANIFEST.json"], [T_REL], ["docs/adr/ADR-0001-separate-orchestration-and-bulk-data-channels.md"], ["Nexus spec manifest is generated but not approved"], False),
    "C032": ([ARCH + "#7"], [T_REL], [], [], False),
    "C033": (["runtime/config.py::FIELDS", "schemas/config/config.schema.json"], [T_UNIT, T_CON], [], [], False),
    "C034": (["runtime/config.py::validate", "runtime/config.py::ConfigStore.apply"], [T_UNIT], [], [], False),
    "C035": (["runtime/config.py::merge", "runtime/config.py::load_file", "config/examples/"], [T_UNIT], [], [], False),
    "C036": (["runtime/config.py::build (provenance)"], [T_UNIT], [], [], False),
    "C037": (["runtime/config.py::ConfigStore.apply"], [T_UNIT, T_CC], [], [], False),
    "C038": (["runtime/config.py::ConfigStore.rollback"], [T_UNIT], ["docs/operations/ROLLOUT_AND_ROLLBACK.md"], [], False),
    "C039": (["runtime/security.py::redact", "runtime/config.py::validate (E504)"], [T_SEC], ["docs/security/CRYPTO_AND_KEY_POLICY.md"], [], False),
    "C040": (["pyproject.toml", "release/dependencies.json"], [T_REL], [], [PK], False),
    "C041": (["docs/security/THREAT_MODEL.md"], [T_SEC], [], [], False),
    "C042": (["runtime/security.py::Capability"], [T_SEC], ["docs/security/SECURITY_ARCHITECTURE.md"], [], False),
    "C043": (["runtime/datapath.py::Runtime._auth"], [T_SEC, T_SBX], ["docs/security/SECURITY_ARCHITECTURE.md"], [], False),
    "C044": (["runtime/security.py::Authority.authorize"], [T_SEC], ["docs/security/SECURITY_ARCHITECTURE.md"], ["node/peer mTLS and attestation are production bindings"], False),
    "C045": (["runtime/release.py::build_manifest/verify_manifest"], [T_REL], [], [KEY], False),
    "C046": ([ARCH + "#6", "runtime/datapath.py (tenant binding)"], [T_SEC], [], [], False),
    "C047": (["runtime/security.py::KeyRing.rotate/retire"], [T_SEC], ["docs/security/CRYPTO_AND_KEY_POLICY.md"], ["production KMS/HSM binding"], False),
    "C048": (["runtime/security.py::KeyRing.available", "runtime/security.py::Authority.time_trusted"], [T_SEC, T_FLT], ["docs/security/SECURITY_ARCHITECTURE.md"], [], False),
    "C049": (["runtime/security.py::AuditLog"], [T_SEC], [], [], False),
    "C050": ([T_SEC, T_FUZZ], [T_SEC, T_FUZZ], ["docs/security/THREAT_MODEL.md"], ["microarchitectural side channels owned by INV-43"], False),
    "C051": (["docs/resilience/FMEA.md"], [T_FLT], [], [], False),
    "C052": (["runtime/health.py::StallDetector"], [T_FLT], [], [], False),
    "C053": (["runtime/policy.py::RetryPolicy"], [T_UNIT], [], [], False),
    "C054": (["runtime/policy.py::CircuitBreaker"], [T_FLT], [], [], False),
    "C055": (["docs/resilience/FMEA.md#failover"], [T_FLT], [], [], False),
    "C056": (["runtime/lifecycle.py::DegradedMode"], [T_FLT], ["docs/resilience/FMEA.md"], [], False),
    "C057": (["runtime/datapath.py::Runtime.recover"], [T_FLT], ["docs/operations/STATELESSNESS_DECISION.md"], [], False),
    "C058": (["runtime/lifecycle.py::Lifecycle.claim"], [T_SEC], ["docs/resilience/FMEA.md"], [], False),
    "C059": (["runtime/lifecycle.py::State.QUARANTINED/FROZEN/DISABLED"], [T_FLT], [], [], False),
    "C060": ([T_FLT + "::FaultInjector"], [T_FLT], ["docs/resilience/FMEA.md#recovery-objectives"], [], False),
    "C061": (["benchmarks/bench.py", "benchmarks/baselines/"], [T_PERF], [PERF], [BACKEND], False),
    "C062": (["benchmarks/thresholds.json"], [T_PERF], [PERF], [], False),
    "C063": (["benchmarks/bench.py::run"], [T_PERF], [PERF], [], False),
    "C064": (["benchmarks/bench.py (facade_overhead_ratio, per-tenant)"], [T_PERF], [PERF], [], False),
    "C065": ([PERF + "#hop-analysis"], [T_PERF], [], [], False),
    "C066": (["runtime/security.py::Authority._verified"], [T_PERF, T_SEC], [PERF], ["zero-copy/kernel-bypass are backend-owned (WVR-003)"], False),
    "C067": (["docs/requirements/INTERFACE_LIMITS.md"], [T_SEC], [], [], False),
    "C068": ([PERF + "#power-thermal"], [], [], [HW], True),
    "C069": (["runtime/policy.py::QuotaManager.saturation", "alerts/inv35_alerts.json"], [T_PERF], [PERF], [], False),
    "C070": ([T_PERF, "benchmarks/thresholds.json"], [T_PERF], [], [], False),
    "C071": (["runtime/health.py::status_document", "schemas/status/status.schema.json"], [T_CON, T_UNIT], [OBS], [], False),
    "C072": (["runtime/telemetry.py::Metrics", "telemetry/metrics_catalog.json"], [T_UNIT], [OBS], [], False),
    "C073": (["runtime/telemetry.py::StructuredLog", "telemetry/log_schema.json"], [T_UNIT], [OBS], [], False),
    "C074": (["runtime/telemetry.py::TraceContext"], [T_UNIT, T_INT], [OBS], [], False),
    "C075": (["runtime/telemetry.py::MAX_SERIES_PER_METRIC", "runtime/security.py::redact"], [T_SEC], [OBS], [], False),
    "C076": (["runtime/telemetry.py::decision", "schemas/status/decision.schema.json"], [T_CON], [OBS], [], False),
    "C077": (["runtime/telemetry.py::explain", "tools/inv35ctl.py"], [T_UNIT], [OBS], [], False),
    "C078": (["runtime/release.py::build_provenance", "conformance/PK_GATE_RESULTS.json"], [T_REL], [OBS], [], False),
    "C079": ([OBS + "#retention"], [T_SEC], [], [], False),
    "C080": (["dashboards/inv35_overview.json", "alerts/inv35_alerts.json"], [T_REL], [OBS], [], False),
    "C082": (["schemas/"], [T_CON], [], [], False),
    "C083": ([T_INT], [T_INT], [], [BACKEND], False),
    "C084": (["tests/compatibility/matrix.json", "docs/testing/COMPATIBILITY_MATRIX.md"], [T_CMP], [], [BACKEND], False),
    "C085": ([T_FUZZ], [T_FUZZ], [], [], False),
    "C086": ([T_CC], [T_CC], [], [], False),
    "C087": ([T_SEC, T_SBX], [T_SEC, T_SBX], ["docs/security/THREAT_MODEL.md"], [], False),
    "C088": (["benchmarks/bench.py"], [T_PERF], [PERF], ["fleet-scale runs need a real fleet"], False),
    "C089": (["runtime/datapath.py::control_plane_lost/restored"], [T_FLT], ["docs/operations/STATELESSNESS_DECISION.md"], [], False),
    "C090": (["runtime/release.py::seal", "conformance/PK_GATE_RESULTS.json", "evidence/"], [T_REL], [], [KEY], False),
    "C091": (["docs/operations/SLO.md"], [], [], [], False),
    "C092": (["docs/operations/ROLLOUT_AND_ROLLBACK.md"], [T_FLT, T_UNIT], [], ["canary/rollback not yet exercised on a candidate (G13)"], False),
    "C093": (["docs/requirements/COMPATIBILITY_POLICY.md#supported-adjacent-versions-c093"], [T_CMP], [], [PK, BACKEND], False),
    "C094": (["docs/operations/PATCHING_AND_EOL.md", "SECURITY.md"], [], [], [], False),
    "C095": (["docs/operations/STATELESSNESS_DECISION.md"], [T_FLT], [], [], False),
    "C096": (["runbooks/RUNBOOKS.md", "tools/inv35ctl.py"], [T_REL], [], [], False),
    "C097": (["docs/operations/INCIDENT_RESPONSE.md"], [], [], [ROLES + " (on-call destination)"], False),
    "C098": (["governance/REVIEW_SCHEDULE.json"], [T_REL], [], [], False),
    "C099": (["governance/WAIVERS.json"], [T_REL], [], ["waivers WVR-001..003 await approval"], False),
    "C100": (["verify.py", "runtime/release.py", "docs/operations/PRODUCTION_EXIT_GATE.md"], [T_REL], [], [PK, ROLES, LIC, KEY], False),
}

REPO: dict[str, tuple[str, list[str], list[str]]] = {
    "REPO-001": ("License and notice files", ["governance/LICENSE_DECISION.json", "THIRD-PARTY-NOTICES.md", "runtime/release.py::governance_findings (license gate)"], [LIC]),
    "REPO-002": ("Pinned dependency/bootstrap manifest", ["pyproject.toml", "release/dependencies.json"], [PK]),
    "REPO-003": ("Continuous-integration configuration", [".github/workflows/verify.yml"], ["CI not yet executed on a hosted runner"]),
    "REPO-004": ("Static-analysis and repository security configuration", ["pyproject.toml ([tool.ruff/mypy/bandit])", ".gitleaks.toml", ".github/workflows/verify.yml"], ["scanners run only in CI (not installed here)"]),
    "REPO-005": ("Machine-readable interface schema directory", ["schemas/", "tools/gen_schemas.py"], []),
    "REPO-006": ("Evidence and conformance output ledger", ["evidence/", "conformance/PK_GATE_RESULTS.json"], [KEY]),
    "REPO-007": ("Benchmark assets and reproducibility package", ["benchmarks/"], []),
    "REPO-008": ("Fuzz corpus and property-testing package", ["tests/fuzz/test_fuzz.py", "fixtures/"], []),
    "REPO-009": ("Operational telemetry assets", ["telemetry/", "dashboards/", "alerts/"], []),
    "REPO-010": ("Software supply-chain artifacts", ["release/manifest/MANIFEST.json", "release/sbom/sbom.cdx.json", "release/provenance/provenance.intoto.json"], [KEY]),
    "REPO-011": ("Ownership and governance metadata package", ["governance/", "CODEOWNERS", "SECURITY.md"], [ROLES]),
}
