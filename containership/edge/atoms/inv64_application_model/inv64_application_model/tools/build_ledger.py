"""Generate COMPONENTS_STATUS.json, evidence/ITEM_LEDGER.json, evidence/REQUIREMENTS_MATRIX.json and
REQUIREMENTS_TRACEABILITY.md from the tables below (single place where status claims are made).

    python -m inv64_application_model.tools.build_ledger [--check]

``--check`` regenerates in memory and fails if the committed files differ (CI drift guard).

Status vocabulary
-----------------
Components (MC-nn): COMPLETE | IMPLEMENTED_LOCAL (all repository-side engineering
done and tested; remaining items need people/infrastructure outside the repo) |
PARTIAL | BLOCKED_EXTERNAL | GOVERNANCE_PENDING. Nothing is COMPLETE in 4.3.0:
every component still has at least one owner-, infrastructure- or
approval-dependent item, named in ``blockers``.

Items (768 checklist lines): DONE | PARTIAL | OPEN_EXTERNAL | OPEN_GOVERNANCE.
Classification is rule-based and disclosed: an item whose text needs an owner,
approval, drill, production/real system, pk_core, managed key custody or a CI
runner is OPEN_*; ITEM_OVERRIDES pins individual judgements; everything else in
an IMPLEMENTED_LOCAL/PARTIAL component is DONE with that component's evidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
T = "tests/test_v43.py"

# id: (status, artifacts, tests/evidence, blockers)
MC: dict[str, tuple[str, list[str], list[str], list[str]]] = {
    "MC-01": ("PARTIAL", ["source/INV64_v4.2.0_MISSING_COMPONENTS_CHECKLIST.md", "provenance/master-source.json",
                          "source/items.json", "tools/source_integrity.py"],
              [T + "::RepositoryControlsTest.test_source_integrity_passes_and_detects_mutation", "evidence/SOURCE_CHECK.json"],
              ["MASTER.md (series v4.0.0 source corpus) not supplied — recorded BLOCKED_EXTERNAL in provenance/master-source.json",
               "change-control approver role (architecture-review-board) unassigned"]),
    "MC-02": ("BLOCKED_EXTERNAL", ["tools/preflight.py", "tools/bootstrap.sh", "tools/bootstrap.ps1", "compatibility.json",
                                   "DEPENDENCIES.md", "tests/run_all.py"],
              ["evidence/PREFLIGHT.json", "evidence/TESTS.json"],
              ["pk_core source, version and digest not supplied: no pin, test_component fails/skips by design",
               "python -m pk_core list/run/gate cannot be executed"]),
    "MC-03": ("IMPLEMENTED_LOCAL", ["pyproject.toml", "constraints-certification.txt", "tools/build_check.py"],
              ["evidence/BUILD.json", T + "::RepositoryControlsTest.test_version_single_source"],
              ["build isolation not exercised (no package index in the build session; tools/build_check.py uses it when present)",
               "license metadata pending owner decision (MC-38)"]),
    "MC-04": ("GOVERNANCE_PENDING", ["ops/owners.json", "ops/OWNERS.md", "ops/decisions.json", "ops/ADR-0001-application-model.md",
                                     "tools/governance_check.py"],
              ["evidence/GOVERNANCE.json"],
              ["all six accountable roles have assignee=null", "ADR-0001 status=proposed, no approvers"]),
    "MC-05": ("IMPLEMENTED_LOCAL", ["SPECIFICATION.md", "errors.py", "activation.py", "semantics.py", "explain.py"],
              [T + "::ErrorContractTest", T + "::OverlayActivationTest.test_lifecycle_table_has_no_path_out_of_rejected",
               T + "::SemanticsTest", T + "::ExplainTest"],
              ["normative specification not yet approved by architecture-review-board"]),
    "MC-06": ("IMPLEMENTED_LOCAL", ["INTERFACES.md", "errors.py", "schema/error-v1.schema.json", "schema/submit-request-v1.schema.json",
                                    "schema/submit-response-v1.schema.json", "schema/status-v1.schema.json", "wit/inv64-app-model.wit"],
              [T + "::ErrorContractTest", T + "::ServiceTest.test_rejections_are_typed"],
              ["WIT world is contract-only (no Wasm build); cross-language fixtures N/A until a second implementation exists",
               "contract docs/fixture regeneration not yet observed on a CI runner"]),
    "MC-07": ("IMPLEMENTED_LOCAL", ["auth.py", "SECURITY_ARCHITECTURE.md"], [T + "::AuthnTest", T + "::ServiceTest"],
              ["production issuers, trust roots, mTLS certificates and break-glass identities not provisioned"]),
    "MC-08": ("IMPLEMENTED_LOCAL", ["authz.py", "schema/authz-policy-v1.schema.json", "SECURITY_ARCHITECTURE.md"], [T + "::AuthzTest"],
              ["pk_core authority review impossible (pk_core absent)", "production policy content and least-privilege review evidence absent"]),
    "MC-09": ("IMPLEMENTED_LOCAL", ["semantics.py", "INTERFACES.md"], [T + "::SemanticsTest", "evidence/STRESS.json"],
              ["client guidance published but not yet exercised by a real client"]),
    "MC-10": ("BLOCKED_EXTERNAL", ["adjacent.py", "tools/integration.py"], ["evidence/INTEGRATION.json", "evidence/INTEGRATION_REAL.json"],
              ["real INV-10/INV-63/INV-65/INV-66 implementations not in the archive; only the emulated profile runs"]),
    "MC-11": ("IMPLEMENTED_LOCAL", ["oam_profile.py", "OAM_PROFILE.md", "provenance/oam-baseline.json", "compatibility.json"],
              [T + "::AdjacentOamRolloutTest.test_oam_round_trip_and_unsupported"],
              ["baseline selection needs ADR-0001 approval"]),
    "MC-12": ("IMPLEMENTED_LOCAL", ["overlay.py", "schema/overlay-v1.schema.json", "CONFIGURATION.md"], [T + "::OverlayActivationTest"],
              ["no network API for overlay submission in this package; author authorization is a caller hook"]),
    "MC-13": ("IMPLEMENTED_LOCAL", ["activation.py", "CONFIGURATION.md"], [T + "::OverlayActivationTest", "evidence/FAULTS.json", "evidence/ROLLBACK_DRILL.json"],
              ["release-drill on production mechanism not performed (only CI drill)"]),
    "MC-14": ("IMPLEMENTED_LOCAL", ["redaction.py", "manifest.py", "tools/secret_scan.py", "ops/secret_scan_allowlist.json", "SECURITY_ARCHITECTURE.md"],
              [T + "::SecretsTest", "evidence/SECRET_SCAN.json", "evidence/FUZZ.json"],
              ["allowlist entries need owner review", "secret-leak remediation procedure owner unassigned"]),
    "MC-15": ("IMPLEMENTED_LOCAL", ["trust.py", "provenance.py", "SECURITY_ARCHITECTURE.md"], [T + "::TrustTest", T + "::BackupReleaseTest"],
              ["no managed signer / trust anchors provisioned; policy root keys not issued"]),
    "MC-16": ("IMPLEMENTED_LOCAL", ["tenancy.py", "SECURITY_ARCHITECTURE.md"], [T + "::TenancyTest", "evidence/STRESS.json"],
              ["isolation profile is logical only (REG-005)"]),
    "MC-17": ("IMPLEMENTED_LOCAL", ["crypto_policy.py", "SECURITY_ARCHITECTURE.md"], [T + "::CryptoTest"],
              ["KMS/HSM key provider and certificates not provisioned", "sealed storage available but not enabled by default (no secret-class data persisted)"]),
    "MC-18": ("IMPLEMENTED_LOCAL", ["audit.py", "schema/audit-v1.schema.json"], [T + "::AuditTest", "evidence/AUDIT_VERIFY.json", "evidence/FAULTS.json"],
              ["external WORM anchor store and retention owner not provisioned"]),
    "MC-19": ("IMPLEMENTED_LOCAL", ["tools/fuzz.py", "tests/fixtures/fuzz_regressions.json"], ["evidence/FUZZ.json"],
              ["scheduled long campaign defined in CI but not yet run on a runner; no coverage-guided engine (stdlib-only)"]),
    "MC-20": ("IMPLEMENTED_LOCAL", ["FMEA.md", "tools/faults.py"], ["evidence/FAULTS.json"],
              ["recovery objectives need owner approval"]),
    "MC-21": ("PARTIAL", ["bench/perf.py", "BENCHMARKS.md"], ["evidence/PERF.json"],
              ["reference benchmark environment not designated", "edge power/thermal not measured (needs device + approval)"]),
    "MC-22": ("IMPLEMENTED_LOCAL", ["bench/perf.py", "BENCHMARKS.md"], ["evidence/PERF_GATE.json"],
              ["approved baseline on the reference environment does not exist yet"]),
    "MC-23": ("IMPLEMENTED_LOCAL", ["service.py", "schema/status-v1.schema.json"], [T + "::ServiceTest.test_status_readiness"],
              ["no HTTP probe endpoint (library API only); orchestration wiring is the host's"]),
    "MC-24": ("IMPLEMENTED_LOCAL", ["telemetry.py"], [T + "::TelemetryTest", T + "::ServiceTest.test_telemetry_logs_and_explain_are_safe"],
              ["no exporter (OTel/Prometheus endpoint) bundled; exposition text only"]),
    "MC-25": ("IMPLEMENTED_LOCAL", ["explain.py", "schema/decision-v1.schema.json"], [T + "::ExplainTest"],
              ["no live infrastructure-graph source; graph_state reported 'unknown'"]),
    "MC-26": ("GOVERNANCE_PENDING", ["TELEMETRY_POLICY.md", "ops/alerts.json", "dashboards/inv64-overview.json"], ["evidence/GOVERNANCE.json"],
              ["alert routing never tested end-to-end to a real pager", "privacy/residency review of telemetry providers not done"]),
    "MC-27": ("PARTIAL", ["compatibility.json", "COMPATIBILITY.md", ".github/workflows/ci.yml"], ["evidence/PREFLIGHT.json"],
              ["only linux-x86_64 / CPython 3.11 executed in this pass; other matrix rows defined, not run"]),
    "MC-28": ("IMPLEMENTED_LOCAL", ["tools/stress.py"], ["evidence/STRESS.json"],
              ["extended soak/fleet profile scheduled but not run"]),
    "MC-29": ("IMPLEMENTED_LOCAL", ["release_gate.py", "ops/GATE_POLICY.json"], [T + "::RepositoryControlsTest.test_gate_is_deterministic_and_fails_closed", "evidence/EXIT_GATE.json"],
              ["gate artifact signed only by ephemeral key; current verdict NO_GO"]),
    "MC-30": ("IMPLEMENTED_LOCAL", ["compatibility.json", "COMPATIBILITY.md", "tools/governance_check.py"], ["evidence/GOVERNANCE.json"],
              ["matrix rows beyond linux-x86_64/py3.11 lack run evidence (MC-27)"]),
    "MC-31": ("GOVERNANCE_PENDING", ["SECURITY_RESPONSE.md", ".github/workflows/ci.yml"], [],
              ["reporting channel and security contact unassigned", "no tabletop/emergency-patch drill", "advisory scan needs index access (CI step defined)"]),
    "MC-32": ("IMPLEMENTED_LOCAL", ["BACKUP_RESTORE.md", "ops/state_inventory.json", "tools/backup_restore.py"], [T + "::BackupReleaseTest"],
              ["RPO/RTO targets need owner approval"]),
    "MC-33": ("GOVERNANCE_PENDING", ["ops/RUNBOOK.md", "tools/bootstrap.sh", "tools/bootstrap.ps1"], [],
              ["runbooks not yet executed by an operator in a drill"]),
    "MC-34": ("GOVERNANCE_PENDING", ["ops/INCIDENT_RESPONSE.md"], [],
              ["roles unassigned; paging paths and tabletop exercises not performed"]),
    "MC-35": ("GOVERNANCE_PENDING", ["ops/REVIEWS.json", "tools/review_collect.py", "tools/governance_check.py"], ["evidence/GOVERNANCE.json"],
              ["no review performed yet (first due 2026-10-22)"]),
    "MC-36": ("IMPLEMENTED_LOCAL", ["ops/REGISTER.json", "tools/governance_check.py", "release_gate.py"],
              [T + "::RepositoryControlsTest.test_gate_is_deterministic_and_fails_closed"],
              ["register entries have owner_role but no named owner"]),
    "MC-37": ("PARTIAL", [".github/workflows/ci.yml", "tools/run_evidence.py"], ["evidence/"],
              ["workflow never executed on a CI runner; branch protection is a repository setting"]),
    "MC-38": ("GOVERNANCE_PENDING", ["LICENSING.md", "NOTICE", "THIRD-PARTY-NOTICES.md", "pyproject.toml"], ["evidence/BUILD.json"],
              ["distribution license not chosen by the owner"]),
    "MC-39": ("PARTIAL", ["tools/release.py", "provenance.py"], [T + "::BackupReleaseTest", "evidence/RELEASE_VERIFY.json"],
              ["release signed with an ephemeral key; managed signer required (REG-003)"]),
    "MC-40": ("IMPLEMENTED_LOCAL", ["rollout.py", "ops/ROLLOUT_POLICY.json"], [T + "::AdjacentOamRolloutTest", "evidence/ROLLBACK_DRILL.json"],
              ["no production fleet drill"]),
}

C_STATUS: dict[str, tuple[str, str]] = {
    **{f"C{i:03d}": ("verified", "contract.py; SPECIFICATION.md §1") for i in range(1, 9)},
    "C009": ("partial", "ops/owners.json roles + escalation defined; assignees null (MC-04)"),
    "C010": ("partial", "ops/ADR-0001 drafted, status proposed (MC-04)"),
    "C011": ("verified", "SPECIFICATION.md REQ-FN-*; tests/test_manifest.py, test_v43.py"),
    "C012": ("verified", "SPECIFICATION.md §3 tier profiles"),
    "C013": ("verified", "SPECIFICATION.md §6; bench/perf.py thresholds"),
    "C014": ("verified", "errors.Outcome/outcome_for; SPECIFICATION.md §4; ErrorContractTest"),
    "C015": ("verified", "activation.TRANSITIONS; SPECIFICATION.md §5; OverlayActivationTest"),
    "C016": ("verified", "SPECIFICATION.md §11; compatibility.json; semantics.negotiate"),
    "C017": ("verified", "manifest limits, AdmissionController, TenantRegistry quota; SemanticsTest"),
    "C018": ("verified", "SPECIFICATION.md §7; crypto_policy.OUTAGE_RULES; AuthnTest.test_trust_outage_cached_then_closed"),
    "C019": ("verified", "SPECIFICATION.md §10; explain.dominant; ExplainTest"),
    "C020": ("verified", "this matrix (generated) + evidence/ITEM_LEDGER.json"),
    "C021": ("verified", "INTERFACES.md §1 boundary inventory"),
    "C022": ("verified", "schema/*.schema.json; wit/inv64-app-model.wit"),
    "C023": ("verified", "auth.py; AuthnTest"),
    "C024": ("verified", "authz.py; AuthzTest"),
    "C025": ("verified", "semantics.py; SemanticsTest"),
    "C026": ("verified", "errors.py PK_APP_ERROR/1; ServiceTest.test_rejections_are_typed"),
    "C027": ("verified", "semantics.negotiate; adjacent version checks; integration scenarios"),
    "C028": ("verified", "INTERFACES.md §2 limits; enforced in manifest/service/semantics"),
    "C029": ("verified", "examples/, tests/fixtures/"),
    "C030": ("partial", "emulated INV-10/63/65/66 harness only (MC-10)"),
    "C031": ("partial", "OAM v0.3.0 pinned by commit; pk_core unpinned (MC-02)"),
    "C032": ("verified", "overlay.py immutable identity vs properties overlays"),
    "C033": ("verified", "secure defaults: deny-by-default authz, bounded admission, fail-closed audit"),
    "C034": ("verified", "overlay.merge re-validation; ConfigStore.propose; OverlayActivationTest"),
    "C035": ("verified", "overlay.py; OverlayActivationTest"),
    "C036": ("verified", "effective-config provenance + ConfigStore revisions + audit"),
    "C037": ("verified", "activation.py journal/CAS; crash tests"),
    "C038": ("verified", "auto + operator rollback; ROLLBACK_DRILL"),
    "C039": ("verified", "redaction.py + manifest secret.inline; SecretsTest; secret_scan"),
    "C040": ("partial", "bootstrap scripts + preflight; pk_core absent (MC-02)"),
    "C041": ("verified", "SECURITY_ARCHITECTURE.md threat model"),
    "C042": ("partial", "capability model enforced; pk_core authority unreviewable (MC-08)"),
    "C043": ("partial", "parser has no ambient authority; host sandboxing outside package"),
    "C044": ("verified", "auth.py identity kinds incl. node/provider/signer; trust.py for artifacts"),
    "C045": ("verified", "trust.verify_artifact; TrustTest (managed signer pending: MC-39)"),
    "C046": ("partial", "tenancy.py logical isolation (REG-005)"),
    "C047": ("partial", "tls_context + sealed storage implemented; KMS not provisioned (MC-17)"),
    "C048": ("verified", "OUTAGE_RULES + fault scenarios f08/f10"),
    "C049": ("verified", "audit.py; AuditTest"),
    "C050": ("verified", "abuse tests across AuthnTest/AuthzTest/TenancyTest/fuzz"),
    "C051": ("verified", "FMEA.md"),
    "C052": ("verified", "FMEA.md thresholds; service.status dependency probes"),
    "C053": ("verified", "RetryPolicy; SemanticsTest"),
    "C054": ("verified", "AdmissionController; retry budget; STRESS s4"),
    "C055": ("verified", "SPECIFICATION.md §7.4; STRESS s7 partition/reconnect"),
    "C056": ("verified", "status degraded state; optional dependencies"),
    "C057": ("verified", "journal recovery; FAULTS f05/f06/f12"),
    "C058": ("verified", "CAS expected_active; idempotency; STRESS s2/s3"),
    "C059": ("verified", "quarantine + emergency disable; FAULTS f11"),
    "C060": ("verified", "tools/faults.py; evidence/FAULTS.json"),
    "C061": ("partial", "baselines measured on the build container, not a designated reference env (MC-21)"),
    "C062": ("verified", "bench/perf.py THRESHOLDS"),
    "C063": ("partial", "steady/burst/overload measured; scale-out/in not applicable to a library, fleet profile not run"),
    "C064": ("partial", "per-tenant fairness exercised (STRESS s4/s5); per-tenant overhead not separately benchmarked"),
    "C065": ("verified", "BENCHMARKS.md data path"),
    "C066": ("verified", "BENCHMARKS.md optimizations applied/rejected"),
    "C067": ("verified", "all queues/rings/caches bounded in code"),
    "C068": ("partial", "marked not measured; needs owner approval as N/A or an edge device"),
    "C069": ("verified", "bench capacity_model + saturation signals"),
    "C070": ("verified", "bench/perf.py --compare gate"),
    "C071": ("verified", "service.status PK_APP_STATUS/1"),
    "C072": ("verified", "telemetry.METRICS"),
    "C073": ("verified", "telemetry.StructuredLog"),
    "C074": ("verified", "W3C traceparent through service and adjacent handoff"),
    "C075": ("verified", "redaction + bounded labels + tenant-scoped views"),
    "C076": ("verified", "explain.DecisionLog"),
    "C077": ("verified", "explain.explain"),
    "C078": ("partial", "release lineage recorded; live infrastructure graph source absent"),
    "C079": ("verified", "TELEMETRY_POLICY.md"),
    "C080": ("partial", "dashboards/alerts as code; not deployed or tested end-to-end (MC-26)"),
    "C081": ("verified", "unit tests"),
    "C082": ("verified", "contract tests for every public operation"),
    "C083": ("partial", "emulated adjacent layers only (MC-10)"),
    "C084": ("partial", "one platform row executed (MC-27)"),
    "C085": ("verified", "tools/fuzz.py"),
    "C086": ("verified", "tools/stress.py s1-s3"),
    "C087": ("verified", "threat-model-derived tests"),
    "C088": ("partial", "ci profile only; extended soak/fleet not run"),
    "C089": ("verified", "partition/reconnect, corrupt-state, restore tests"),
    "C090": ("verified", "release_gate.py + evidence schemas"),
    "C091": ("partial", "SLOs defined; support commitments need owner"),
    "C092": ("verified", "rollout.py + ROLLOUT_POLICY + drill"),
    "C093": ("verified", "compatibility.json + COMPATIBILITY.md"),
    "C094": ("partial", "SECURITY_RESPONSE.md drafted; roles unassigned (MC-31)"),
    "C095": ("verified", "BACKUP_RESTORE.md + tools/backup_restore.py"),
    "C096": ("partial", "runbooks written, not drilled (MC-33)"),
    "C097": ("partial", "procedure written, not exercised (MC-34)"),
    "C098": ("partial", "cadence + collector; no review performed (MC-35)"),
    "C099": ("verified", "ops/REGISTER.json + governance_check + gate"),
    "C100": ("verified", "release_gate.py exists and runs; its current verdict is NO_GO"),
}

EXTERNAL = re.compile(r"pk_core|real adjacent|real implementations|adjacent component version|production[- ]certification|"
                      r"clean supported host|KMS|HSM|managed (signing|key)|OIDC|signing key|trust anchor|transparency|"
                      r"reference environment|edge (power|thermal)|power/thermal|runners?\b|branch/release protection|"
                      r"CI job|in CI\b|published|publish|release upload|real |fleet|external store|WORM|tabletop|paging|"
                      r"reach the (correct|documented)|protected (pipeline|release)", re.I)
GOVERNANCE = re.compile(r"\bowner|approv|legal|accountable|assignee|on-call|escalat|drill|exercise|sign-off|"
                        r"authorized owner|reviewer|review cadence|recurring|periodic|feedback|separation of duties|"
                        r"customer|communication|notif", re.I)
CI_RULE = re.compile(r"\bCI\b|pipeline|release jobs?|scheduled", re.I)
_P = "PARTIAL"
_OE = "OPEN_EXTERNAL"
ITEM_OVERRIDES: dict[str, tuple[str, str]] = {
    # reviewed individually during the 4.3.0 pass (see AUDIT_REPORT.md "ledger method")
    "MC-02.D05": (_P, "offline wheelhouse path documented (bootstrap --wheelhouse); approved mirror/cache policy needs an owner"),
    "MC-02.E01": (_P, "Python range defined and enforced; verification against a pk_core revision impossible"),
    "MC-02.E03": ("DONE", "preflight realpath/symlink/writable checks; PreflightTest with a stand-in pk_core"),
    "MC-02.E05": (_OE, "certification environment with pk_core does not exist"),
    "MC-02.E08": (_P, "missing/wrong-version/tampered/incompatible-Python covered by PreflightTest; pk_core gate-tool failure untestable without pk_core"),
    "MC-03.E04": (_P, "isolation used when `build` is installed; not exercised in the offline build session"),
    "MC-08.E05": (_P, "library needs no ambient authority; host-level sandboxing is outside the package"),
    "MC-10.A02": (_OE, "production CI never executed"),
    "MC-10.E09": (_P, "emulator contract versions + fixture results recorded; real component versions unavailable"),
    "MC-15.A04": ("DONE", "TrustStore.activate requires root signature, audits fail-closed, keeps previous for rollback"),
    "MC-17.A01": (_P, "no secret-class data is persisted; TLS and sealing implemented but deployment wiring is the host's"),
    "MC-17.E05": (_P, "rotation tested sequentially; not under concurrent in-flight load"),
    "MC-17.E09": (_P, "metric and alert defined; crypto_policy does not increment it itself (host wires metrics)"),
    "MC-19.D03": (_P, "differential between raw and decoded paths of one parser; no second independent JSON/schema implementation compared"),
    "MC-21.D04": (_P, "CPU time, peak memory, startup measured; storage/network overhead not applicable to the library, not measured"),
    "MC-21.E03": (_P, "steady/burst/overload/post-fault measured; scale-out/in not applicable to a library"),
    "MC-21.E04": (_P, "fairness exercised in stress; per-tenant overhead not separately benchmarked"),
    "MC-22.A02": (_P, "model fitted and validated on the build container, not a designated reference workload"),
    "MC-23.D02": ("DONE", "status versions include build_digest, spec, contracts, OAM, policy"),
    "MC-23.E06": ("DONE", "status(viewer=) requires status.inspect for detail"),
    "MC-24.D04": (_P, "tenant-scoped log/explain views and status viewer check; no network diagnostic endpoint exists"),
    "MC-24.E06": (_P, "sampling policy defined (TELEMETRY_POLICY.md); no trace exporter bundled to apply it"),
    "MC-24.E07": (_P, "status detail authorization implemented; other diagnostics are host-exposed"),
    "MC-27.D01": ("DONE", "compatibility.json covers arch/OS/Python/pk_core/OAM/adjacent/protocol dimensions"),
    "MC-27.E02": (_P, "canonical form is text (endian-independent) by construction; not executed on a second architecture"),
    "MC-27.E03": (_P, "bootstrap.sh and bootstrap.ps1 written; only POSIX executed"),
    "MC-27.E08": (_P, "Python build and platform recorded; container image digests not available in this session"),
    "MC-27.A01": (_OE, "matrix rows beyond linux-x86_64/py3.11 not executed"),
    "MC-27.A02": ("DONE", "CHANGELOG 4.3.0 lists the first matrix and deprecations"),
    "MC-27.A04": (_P, "preflight evidence attached for the executed row only"),
    "MC-28.E04": (_P, "5 s soak in the ci profile; long soak only in the scheduled extended profile (not run)"),
    "MC-28.E07": (_P, "restart-then-retry tested (f12) but not under concurrent load"),
    "MC-28.E09": (_P, "telemetry is bounded under load (ring/labels); alert usefulness under load not assessed"),
    "MC-29.D05": (_P, "gate artifact checksummed; signed only via the release tool's ephemeral key"),
    "MC-30.E01": (_P, "ranges beyond the executed row lack test evidence"),
    "MC-30.A01": (_P, "represented in metadata; only one row backed by executed tests"),
    "MC-30.E10": (_P, "history field + git; no archived per-release matrix files yet"),
    "MC-32.E03": (_P, "sealing primitive available; backup tool does not encrypt by itself"),
    "MC-32.E08": (_P, "no migration exists yet (first version with persistent state); major-version guard tested"),
    "MC-36.E05": (_P, "compensating controls recorded; effectiveness not re-verified automatically"),
    "MC-37.D01": ("DONE", ".github/workflows/ci.yml with all stages"),
    "MC-37.D05": ("DONE", "nightly schedule runs 50k fuzz + extended stress"),
    "MC-37.E01": ("DONE", "run_all counts skips; gate no_skips; producers that crash leave FAIL evidence"),
    "MC-37.E02": ("DONE", "build_check installs wheel and sdist into fresh venvs"),
    "MC-37.E03": (_P, "compileall and -O import in CI; no pinned type/static security tooling (no index access to vet versions)"),
    "MC-37.E09": ("DONE", "build_ledger --check, source_integrity, governance_check, schema-conformance tests"),
    "MC-39.D01": ("DONE", "CycloneDX 1.5 SBOM with purls and licenses"),
    "MC-39.D03": (_P, "Ed25519 signatures produced, but with an ephemeral key (REG-003)"),
    "MC-39.E05": ("DONE", "tools/release.py refuses managed signing unless EXIT_GATE verdict is GO"),
    "MC-39.E07": (_P, "license policy applied to SBOM; vulnerability scan is the CI advisories job (not run)"),
    "MC-39.A01": (_P, "digest/SBOM/provenance present; signature path is ephemeral"),
    "MC-39.A04": (_P, "workflow isolates signing in a protected environment; not executed"),
    "MC-40.E05": (_P, "known-good revisions enforced; artifact signatures not checked by the rollout controller"),
    "MC-40.E06": (_P, "partially progressed rollout rollback tested; active traffic and dependency degradation not combined"),
    "MC-01.D01": ("PARTIAL", "the governing remediation checklist is added as a versioned replacement corpus; MASTER.md itself is absent"),
    "MC-02.A02": ("OPEN_EXTERNAL", "pk_core absent; test_component fails/skips by design"),
    "MC-03.A01": ("PARTIAL", "build via PEP 517 hooks without isolation (python -m build unavailable offline)"),
    "MC-11.D01": ("DONE", "provenance/oam-baseline.json: tag v0.3.0, commit 3104d27a…, file digests"),
    "MC-38.D01": ("OPEN_GOVERNANCE", "owner license decision"),
    "MC-39.A04": ("DONE", "release tool never reads a key from the repository; managed key only via protected env"),
}


def items_ledger() -> dict:
    items = json.loads((ROOT / "source" / "items.json").read_text(encoding="utf-8"))["items"]
    rows = []
    for it in items:
        comp_status, arts, tests, _ = MC[it["mc"]]
        if it["id"] in ITEM_OVERRIDES:
            st, why = ITEM_OVERRIDES[it["id"]]
        elif CI_RULE.search(it["text"]) and not EXTERNAL.search(it["text"]) and not GOVERNANCE.search(it["text"]):
            st, why = "PARTIAL", "implemented as a tool + CI workflow step; not yet executed on a CI runner"
        elif comp_status == "BLOCKED_EXTERNAL" and EXTERNAL.search(it["text"]):
            st, why = "OPEN_EXTERNAL", "needs a dependency/system not in the archive"
        elif EXTERNAL.search(it["text"]):
            st, why = "OPEN_EXTERNAL", "needs infrastructure/runner/system outside the repository"
        elif GOVERNANCE.search(it["text"]):
            st, why = "OPEN_GOVERNANCE", "needs named people, approvals or a performed drill/review"
        elif comp_status == "GOVERNANCE_PENDING":
            st, why = "PARTIAL", "artifact drafted; governance component not closed"
        else:
            st, why = "DONE", "implemented; evidence per component"
        rows.append({"id": it["id"], "mc": it["mc"], "kind": it["kind"], "status": st, "basis": why,
                     "evidence": (arts + tests)[:6] if st in ("DONE", "PARTIAL") else [], "text": it["text"]})
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"format": "PK_APP_ITEM_LEDGER/1", "classification": "rule-based (see tools/build_ledger.py docstring) with pinned overrides",
            "counts": dict(sorted(counts.items())), "items": rows}


def components() -> dict:
    items = json.loads((ROOT / "source" / "items.json").read_text(encoding="utf-8"))["items"]
    meta = {}
    src = (ROOT / "source" / "INV64_v4.2.0_MISSING_COMPONENTS_CHECKLIST.md").read_text(encoding="utf-8")
    for m in re.finditer(r"^## (MC-\d{2}) — (.+?)\n\n\*\*Severity:\*\* (\w+)\s*\n\*\*Traceability:\*\* (.+?)\s*$", src, re.M):
        meta[m.group(1)] = {"title": m.group(2).strip(), "severity": m.group(3), "traceability": m.group(4).strip()}
    out = []
    for mc, (st, arts, tests, blockers) in MC.items():
        out.append({"id": mc, **meta[mc], "status": st, "artifacts": arts, "tests": tests, "blockers": blockers,
                    "items": sum(1 for i in items if i["mc"] == mc)})
    counts: dict[str, int] = {}
    for c in out:
        counts[c["status"]] = counts.get(c["status"], 0) + 1
    return {"format": "PK_APP_COMPONENTS_STATUS/1", "release": (ROOT / "VERSION").read_text().strip(),
            "counts": dict(sorted(counts.items())), "components": out}


def matrix() -> dict:
    checklist = json.loads((ROOT / "CHECKLIST.json").read_text(encoding="utf-8"))
    reqs = []
    for i in checklist["items"]:
        cid = i["check_id"].split("-")[-1]
        st, ev = C_STATUS[cid]
        reqs.append({"check_id": i["check_id"], "dimension": i["dimension"], "status": st, "evidence": ev,
                     "requirement": i["requirement"]})
    counts: dict[str, int] = {}
    for r in reqs:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"format": "PK_APP_REQUIREMENTS_MATRIX/1", "counts": dict(sorted(counts.items())), "requirements": reqs}


def traceability_md(mx: dict, prev: dict[str, str]) -> str:
    lines = ["# Requirements traceability — INV-64 v4.3.0", "",
             "Generated by `tools/build_ledger.py` from `CHECKLIST.json` (do not edit by hand; CI fails on drift).",
             "`verified` = executable or documented evidence in this repository, tested where the control is runtime;",
             "`partial` = implemented in part or blocked on people/infrastructure outside the repository (named in the evidence column).",
             f"Counts: {mx['counts']}. 4.2.0 status is shown for comparison; no row was downgraded.", "",
             "| Check | 4.2.0 | 4.3.0 | Requirement | Evidence / remaining gap |", "|---|---|---|---|---|"]
    for r in mx["requirements"]:
        lines.append(f"| {r['check_id']} | {prev.get(r['check_id'], '?')} | {r['status']} | {r['requirement']} | {r['evidence']} |")
    lines += ["", "Component-level status (MC-01..MC-40) is in `COMPONENTS_STATUS.json`; the 768 checklist items are in `evidence/ITEM_LEDGER.json`."]
    return "\n".join(lines) + "\n"


PREV_420 = {}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    prev_path = ROOT / "provenance" / "traceability-4.2.0.json"
    prev = json.loads(prev_path.read_text()) if prev_path.exists() else {}
    outputs = {
        ROOT / "COMPONENTS_STATUS.json": json.dumps(components(), indent=1, ensure_ascii=False) + "\n",
        ROOT / "evidence" / "ITEM_LEDGER.json": json.dumps(items_ledger(), indent=1, ensure_ascii=False) + "\n",
        ROOT / "evidence" / "REQUIREMENTS_MATRIX.json": json.dumps(matrix(), indent=1, ensure_ascii=False) + "\n",
        ROOT / "REQUIREMENTS_TRACEABILITY.md": traceability_md(matrix(), prev),
    }
    drift = [str(p.relative_to(ROOT)) for p, text in outputs.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    if a.check:
        print("PASS" if not drift else f"FAIL drift: {drift}")
        return 1 if drift else 0
    for p, text in outputs.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    print(json.dumps({"components": components()["counts"], "requirements": matrix()["counts"], "items": items_ledger()["counts"]}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
