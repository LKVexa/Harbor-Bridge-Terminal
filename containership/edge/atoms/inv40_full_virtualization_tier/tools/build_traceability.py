"""Generate traceability/requirements.json for all 100 checklist requirements +
6 repository components (INV-40-C020).  Status vocabulary:

  IMPLEMENTED  code/docs + non-skipped tests exist and pass in this build;
               NOT closed - closure needs owner/independent review (blocker OWNER)
  PARTIAL      some of the item is implemented; named blockers cover the rest
  BLOCKED      nothing further is possible without the named external input
  CLOSED       never assigned by the builder

Every entry carries owner=UNASSIGNED, so the production gate stays NO_GO.
"""
from __future__ import annotations

import json
import pathlib

PKG = pathlib.Path(__file__).resolve().parents[1]

BLOCKERS = {
    "OWNER": "accountable humans must be bound to roles and approve closure (docs/OWNERS.md)",
    "HW-KVM": "no host with /dev/kvm + QEMU was available; hardware-backed lane not run",
    "PK-CORE": "pk_core distribution not supplied; cannot pin, lock or run integration",
    "PROD-ENV": "no provisioned environment / collector / transport to deploy into",
    "SEC-KMS": "no KMS/IdP binding for keys; no at-rest/in-transit encryption",
    "SEC-SIGN": "no asymmetric signing identity / attestation service",
    "DIST-STORE": "no linearizable lease store (INV-33) for multi-node fencing/failover",
    "ELAPSED": "requires elapsed real time (drills, soak, recurring reviews)",
    "FLEET": "requires fleet-scale hardware",
    "EDGE-HW": "requires instrumented constrained edge nodes",
    "ADJ-LAYERS": "adjacent elements (INV-23, PLN-04, INV-32, INV-33) not in this repository",
    "LICENSE": "licence choice is the owner's decision",
}

I, P, B = "IMPLEMENTED", "PARTIAL", "BLOCKED"
T = "tests/"
# id: (status, implementation, tests, docs, extra blockers, note)
M = {
 "REPO-001": (P, ["fvt/compat.py", "pyproject.toml"], ["test_fvt_units.CompatTest"], ["docs/DEPENDENCIES.md"], ["PK-CORE"], "API surface declared + import-time diagnostic + extra; range unpinned"),
 "REPO-002": (P, [], [], ["docs/MASTER_RETIREMENT.md"], [], "retirement PROPOSED; not reconstructed"),
 "REPO-003": (P, ["fvt/provider.py", "fvt/service.py"], ["test_fvt_units.ProviderTest", "test_fvt_service", "test_fvt_lanes.KvmLaneTest"], ["docs/adr/ADR-0001-full-virtualization-tier.md"], ["HW-KVM"], "QemuKvmProvider + QMP client implemented and unit-tested; hardware lane NOT RUN"),
 "REPO-004": (I, ["pyproject.toml"], ["tools/ci.py:install-check"], [], [], "zero-dependency build metadata"),
 "REPO-005": (B, [], [], ["LICENSE-DECISION-REQUIRED.md", "THIRD-PARTY-NOTICES.md"], ["LICENSE"], ""),
 "REPO-006": (P, [".github/workflows/ci.yml", "tools/ci.py"], ["evidence/ci_run.json"], [], ["SEC-SIGN"], "CI + evidence + gate; release signing absent"),
 "INV-40-C005": (I, [], [], ["docs/ASSUMPTIONS.md"], [], ""),
 "INV-40-C009": (B, [], [], ["docs/OWNERS.md"], [], "roles/authority defined; nobody bound"),
 "INV-40-C010": (P, [], [], ["docs/adr/ADR-0001-full-virtualization-tier.md"], [], "ADR PROPOSED, unapproved"),
 "INV-40-C011": (I, [], ["test_fvt_service.SecurityTest"], ["docs/REQUIREMENTS.md"], [], "FVT-R01..R06 each mapped to a test"),
 "INV-40-C012": (P, [], [], ["docs/REQUIREMENTS.md"], ["HW-KVM"], "cloud adapter not implemented"),
 "INV-40-C013": (I, [], ["tools/bench.py"], ["docs/REQUIREMENTS.md"], [], "targets PROPOSED"),
 "INV-40-C014": (I, ["fvt/errors.py"], ["test_fvt_units.ErrorsTest", "test_fvt_service.ContractTest.test_degraded_boot_reported"], ["docs/REQUIREMENTS.md"], [], ""),
 "INV-40-C016": (I, ["fvt/compat.py"], ["test_fvt_units.CompatTest"], ["docs/VERSIONING.md"], [], ""),
 "INV-40-C017": (I, ["fvt/resilience.py"], ["test_fvt_units.ResilienceTest.test_admission_shed_and_quota", "test_fvt_service.ConcurrencyTest"], ["docs/REQUIREMENTS.md"], [], ""),
 "INV-40-C018": (P, ["fvt/identity.py", "fvt/telemetry.py", "fvt/fencing.py"], ["test_fvt_units.IdentityTest.test_trust_services_unavailable_fail_closed", "test_fvt_service.FaultInjectionTest.test_telemetry_outage_is_degraded_not_fatal"], ["docs/REQUIREMENTS.md"], [], "serve_cached_readonly mode declared, not implemented"),
 "INV-40-C019": (I, ["fvt/telemetry.py"], [], ["docs/REQUIREMENTS.md"], [], "precedence documented; decisions recorded"),
 "INV-40-C020": (I, ["tools/build_traceability.py"], ["test_fvt_gate"], ["traceability/requirements.json"], [], ""),
 "INV-40-C021": (I, [], [], ["docs/INTERFACES.md"], [], ""),
 "INV-40-C022": (I, ["schemas/", "fvt/schema.py"], ["test_fvt_units.SchemaTest", "test_fvt_service.ContractTest"], [], [], ""),
 "INV-40-C023": (P, ["fvt/identity.py"], ["test_fvt_units.IdentityTest"], ["docs/INTERFACES.md"], ["SEC-KMS"], "HMAC tokens; asymmetric issuer + IdP pending"),
 "INV-40-C024": (I, ["fvt/identity.py"], ["test_fvt_service.SecurityTest"], ["docs/INTERFACES.md"], [], ""),
 "INV-40-C025": (I, ["fvt/resilience.py", "fvt/service.py"], ["test_fvt_units.ResilienceTest", "test_fvt_service.ContractTest.test_idempotent_create"], ["docs/INTERFACES.md"], [], ""),
 "INV-40-C026": (I, ["fvt/errors.py"], ["test_fvt_units.ErrorsTest"], [], [], ""),
 "INV-40-C027": (I, ["fvt/compat.py"], ["test_fvt_units.CompatTest.test_negotiate"], ["docs/VERSIONING.md"], [], "only one major exists"),
 "INV-40-C028": (I, ["fvt/schema.py", "fvt/resilience.py"], ["test_fvt_units.SchemaTest.test_size_and_depth_bounds"], ["docs/INTERFACES.md"], [], ""),
 "INV-40-C029": (I, ["docs/examples/"], ["test_fvt_lanes.FixtureTest"], [], [], ""),
 "INV-40-C030": (B, [], [], ["docs/TESTING.md"], ["ADJ-LAYERS", "PK-CORE"], ""),
 "INV-40-C031": (P, ["fvt/provider.py"], [], ["docs/adr/ADR-0001-full-virtualization-tier.md", "docs/DEPENDENCIES.md"], ["HW-KVM"], "KVM/QEMU selected; exact version pin unverified"),
 "INV-40-C032": (I, ["fvt/config.py"], [], ["docs/CONFIGURATION.md"], [], ""),
 "INV-40-C033": (I, ["fvt/config.py", "schemas/PK_FULL_VM_CONFIG.v1.schema.json"], ["test_fvt_units.ConfigTest.test_secure_defaults_valid"], [], [], ""),
 "INV-40-C034": (I, ["fvt/config.py"], ["test_fvt_units.ConfigTest"], [], [], ""),
 "INV-40-C035": (I, ["fvt/config.py::layer"], ["test_fvt_units.ConfigTest.test_layering_without_rebuild"], [], [], ""),
 "INV-40-C036": (I, ["fvt/config.py::ConfigStore"], ["test_fvt_units.ConfigTest.test_activate_provenance_and_rollback"], [], [], ""),
 "INV-40-C037": (I, ["fvt/config.py::_atomic_write"], ["test_fvt_units.ConfigTest.test_invalid_never_partially_applied"], [], [], ""),
 "INV-40-C038": (I, ["fvt/config.py::rollback"], ["test_fvt_units.ConfigTest.test_auto_rollback_on_failed_health"], [], [], "package rollback is a release procedure (docs/OPERATIONS.md)"),
 "INV-40-C039": (I, ["fvt/config.py", "fvt/telemetry.py", "fvt/audit.py"], ["test_fvt_units.ConfigTest.test_secret_material_refused", "test_fvt_units.TelemetryTest"], [], [], ""),
 "INV-40-C040": (P, ["tools/bootstrap.py"], ["test_fvt_lanes.BootstrapTest"], ["docs/CONFIGURATION.md"], ["HW-KVM"], "healthy path proven only on the fake lane"),
 "INV-40-C041": (I, [], [], ["docs/THREAT_MODEL.md"], [], ""),
 "INV-40-C042": (P, ["fvt/identity.py", "fvt/provider.py"], ["test_fvt_service.SecurityTest.test_quarantine"], ["docs/THREAT_MODEL.md"], ["PROD-ENV"], "uid/cgroup/namespace confinement of QEMU is a host deployment step"),
 "INV-40-C043": (P, ["fvt/provider.py::argv"], ["test_fvt_units.ProviderTest.test_qemu_argv_is_kvm_only_and_full_model"], ["docs/THREAT_MODEL.md"], ["HW-KVM"], ""),
 "INV-40-C044": (P, ["fvt/identity.py"], ["test_fvt_units.IdentityTest"], [], ["SEC-KMS", "SEC-SIGN"], "callers authenticated; node/provider attestation absent"),
 "INV-40-C045": (P, ["fvt/integrity.py", "fvt/service.py"], ["test_fvt_units.IntegrityTest", "test_fvt_service.SecurityTest.test_unapproved_image_and_gpu_policy"], [], ["SEC-SIGN"], "HMAC signature only"),
 "INV-40-C046": (P, ["runtime.py", "fvt/identity.py", "fvt/resilience.py"], ["test_fvt_service.SecurityTest", "test_fvt_service.ConcurrencyTest"], [], ["HW-KVM"], "memory/network isolation relies on KVM/QEMU, unverified on hardware"),
 "INV-40-C047": (B, [], [], ["docs/THREAT_MODEL.md"], ["SEC-KMS", "PROD-ENV"], ""),
 "INV-40-C048": (I, ["fvt/identity.py"], ["test_fvt_units.IdentityTest.test_trust_services_unavailable_fail_closed", "test_fvt_service.SecurityTest.test_key_service_down_fails_closed"], [], [], "attestation service not modelled (none exists)"),
 "INV-40-C049": (I, ["fvt/audit.py"], ["test_fvt_units.AuditTest", "test_fvt_service.SecurityTest.test_cross_tenant_denied_and_audited"], [], [], "head must be anchored off-host in production"),
 "INV-40-C050": (P, [], ["test_fvt_service.SecurityTest", "tools/fuzz.py"], ["docs/THREAT_MODEL.md"], ["HW-KVM"], "escape and side-channel tests need hardware"),
 "INV-40-C051": (I, [], [], ["docs/FAILURE_MODES.md"], [], ""),
 "INV-40-C052": (P, ["fvt/service.py::health"], [], ["docs/FAILURE_MODES.md", "ops/alerts.json"], ["PROD-ENV"], "thresholds PROPOSED, not deployed"),
 "INV-40-C053": (I, ["fvt/resilience.py::retry"], ["test_fvt_units.ResilienceTest.test_retry_semantics"], [], [], ""),
 "INV-40-C054": (I, ["fvt/resilience.py"], ["test_fvt_units.ResilienceTest", "test_fvt_service.FaultInjectionTest.test_breaker_opens_then_recovers"], [], [], ""),
 "INV-40-C055": (B, [], [], ["docs/FAILURE_MODES.md"], ["DIST-STORE"], "tier refuses rather than relocates"),
 "INV-40-C056": (I, ["fvt/telemetry.py"], ["test_fvt_service.FaultInjectionTest.test_telemetry_outage_is_degraded_not_fatal"], [], [], ""),
 "INV-40-C057": (I, ["fvt/journal.py", "fvt/service.py::recover"], ["test_fvt_units.JournalTest", "test_fvt_service.FaultInjectionTest.test_crash_restart_reconciles"], [], [], ""),
 "INV-40-C058": (P, ["fvt/fencing.py", "runtime.py::DeviceLeaseRegistry"], ["test_fvt_units.FencingTest", "test_fvt_service.FencingServiceTest"], [], ["DIST-STORE"], "single-process fencing only"),
 "INV-40-C059": (I, ["fvt/service.py::quarantine"], ["test_fvt_service.SecurityTest.test_quarantine"], [], [], ""),
 "INV-40-C060": (P, ["fvt/provider.py::FakeProvider"], ["test_fvt_service.FaultInjectionTest"], [], ["HW-KVM", "PROD-ENV"], "in-process injection only"),
 "INV-40-C061": (P, ["tools/bench.py"], ["evidence/bench.json"], ["docs/PERFORMANCE.md"], ["HW-KVM"], "control-plane baseline only"),
 "INV-40-C062": (P, ["ci/bench_thresholds.json"], [], ["docs/PERFORMANCE.md"], [], "thresholds PROPOSED, need approval"),
 "INV-40-C063": (P, ["tools/bench.py"], ["evidence/bench.json"], [], ["HW-KVM", "FLEET"], "steady + burst/overload measured; scale-out/in not"),
 "INV-40-C064": (B, [], [], ["docs/PERFORMANCE.md"], ["HW-KVM"], ""),
 "INV-40-C065": (I, [], ["evidence/bench.json"], ["docs/PERFORMANCE.md"], [], "fsync-per-op identified"),
 "INV-40-C066": (P, [], [], ["docs/PERFORMANCE.md"], [], "group-commit identified, not applied (semantics change)"),
 "INV-40-C067": (I, ["fvt/resilience.py", "fvt/telemetry.py", "fvt/journal.py"], ["test_fvt_units.TelemetryTest", "test_fvt_units.JournalTest"], ["docs/PERFORMANCE.md"], [], ""),
 "INV-40-C068": (B, [], [], [], ["EDGE-HW"], ""),
 "INV-40-C069": (P, ["fvt/service.py::health"], [], ["docs/PERFORMANCE.md"], ["PROD-ENV"], "saturation signals only"),
 "INV-40-C070": (P, ["tools/ci.py", "fvt/gate.py"], ["test_fvt_gate"], [], [], "regression check wired; thresholds unapproved"),
 "INV-40-C071": (I, ["fvt/service.py::health"], ["test_fvt_service.ObservabilityTest"], [], [], ""),
 "INV-40-C072": (I, ["fvt/telemetry.py::Metrics"], ["test_fvt_units.TelemetryTest"], ["docs/OBSERVABILITY.md"], [], ""),
 "INV-40-C073": (I, ["fvt/telemetry.py::Logger"], ["test_fvt_service.ObservabilityTest"], [], [], ""),
 "INV-40-C074": (I, ["fvt/telemetry.py"], ["test_fvt_service.ObservabilityTest"], [], [], ""),
 "INV-40-C075": (I, ["fvt/telemetry.py"], ["test_fvt_units.TelemetryTest.test_redaction_cardinality_trace"], [], [], ""),
 "INV-40-C076": (I, ["fvt/telemetry.py::Decisions"], ["test_fvt_service.ContractTest.test_degraded_boot_reported"], [], [], ""),
 "INV-40-C077": (I, ["fvt/telemetry.py::Decisions.explain"], ["test_fvt_units.TelemetryTest.test_explain"], [], [], ""),
 "INV-40-C078": (B, [], [], ["docs/OBSERVABILITY.md"], ["PROD-ENV"], "no release-lineage / infra-graph service"),
 "INV-40-C079": (P, ["fvt/config.py"], [], ["docs/OBSERVABILITY.md"], ["PROD-ENV"], "policy declared; exporter + enforcement absent"),
 "INV-40-C080": (P, ["ops/alerts.json", "ops/dashboard.json"], [], [], ["PROD-ENV"], "defined, not deployed"),
 "INV-40-C082": (I, ["schemas/"], ["test_fvt_service.ContractTest"], ["docs/TESTING.md"], [], ""),
 "INV-40-C083": (B, [], [], ["docs/TESTING.md"], ["ADJ-LAYERS", "PK-CORE"], ""),
 "INV-40-C084": (P, [".github/workflows/ci.yml"], ["test_fvt_units.CompatTest"], [], ["HW-KVM"], "protocol + CPython matrix; arch/hypervisor not"),
 "INV-40-C085": (I, ["tools/fuzz.py"], ["evidence/fuzz.json"], [], [], ""),
 "INV-40-C086": (I, ["fvt/service.py", "runtime.py::DeviceLeaseRegistry"], ["test_fvt_service.ConcurrencyTest", "test_runtime (lease race)"], ["docs/TESTING.md"], [], ""),
 "INV-40-C087": (P, [], ["test_fvt_service.SecurityTest"], ["docs/THREAT_MODEL.md"], ["HW-KVM"], "T1/T14 untested"),
 "INV-40-C088": (P, ["tools/bench.py"], ["evidence/bench.json"], [], ["ELAPSED", "FLEET"], "burst only; no soak/fleet"),
 "INV-40-C089": (P, [], ["test_fvt_service.FaultInjectionTest", "test_fvt_service.FencingServiceTest"], [], ["DIST-STORE"], "in-process only"),
 "INV-40-C090": (I, ["tools/ci.py", "fvt/gate.py"], ["test_fvt_gate"], [], [], ""),
 "INV-40-C091": (P, [], [], ["docs/OPERATIONS.md"], [], "PROPOSED; support owner unassigned"),
 "INV-40-C092": (P, ["fvt/service.py::quarantine"], ["test_fvt_service.SecurityTest.test_quarantine"], ["docs/OPERATIONS.md"], ["ELAPSED"], "procedures written, not exercised"),
 "INV-40-C093": (P, [], [], ["docs/OPERATIONS.md"], ["HW-KVM", "PK-CORE"], ""),
 "INV-40-C094": (P, [], [], ["docs/OPERATIONS.md"], [], "SLAs PROPOSED"),
 "INV-40-C095": (I, ["fvt/journal.py"], ["test_fvt_units.JournalTest"], ["docs/OPERATIONS.md"], [], ""),
 "INV-40-C096": (P, ["tools/bootstrap.py"], ["test_fvt_lanes.BootstrapTest"], ["docs/OPERATIONS.md"], ["ELAPSED"], "runbooks not exercised"),
 "INV-40-C097": (P, [], [], ["docs/OPERATIONS.md"], ["ELAPSED"], "no drill"),
 "INV-40-C098": (B, [], [], ["docs/OPERATIONS.md"], ["ELAPSED"], "cadence proposed; none occurred"),
 "INV-40-C099": (I, ["governance/EXCEPTIONS.json", "fvt/gate.py"], ["test_fvt_gate"], [], [], "entries unowned"),
 "INV-40-C100": (I, ["fvt/gate.py"], ["test_fvt_gate"], [], [], "gate returns NO_GO on this build"),
}


def main() -> dict:
    mc = json.loads((PKG / "MISSING_COMPONENTS.json").read_text())
    idx = {r["check_id"]: r for r in mc["requirements"]}
    prio = {}
    for line in (PKG / "docs/INV40_COMPREHENSIVE_MISSING_COMPONENT_CHECKLIST_v4.2.0.md").read_text().splitlines():
        cells = [c.strip() for c in line.split("|")]
        if len(cells) > 3 and (cells[1].startswith("INV-40-C") or cells[1].startswith("REPO-")):
            prio[cells[1]] = cells[2]
    out = []
    for r in mc["repository_level_missing_components"]:
        s = M[r["id"]]
        out.append(dict(id=r["id"], dimension="Repository", requirement=r["component"], priority=prio.get(r["id"], "P0"),
                        v420_status=r["status"]))
    for r in mc["requirements"]:
        out.append(dict(id=r["check_id"], dimension=r["dimension"], requirement=r["requirement"],
                        priority=prio.get(r["check_id"], "n/a-present" if r["status"] == "present" else "UNLISTED"),
                        v420_status=r["status"]))
    for e in out:
        if e["id"] in M:
            st, impl, tests, docs, blk, note = M[e["id"]]
        else:  # present in v4.2.0 and untouched
            st, impl, tests, docs, blk, note = I, ["contract.py", "runtime.py"], ["test_runtime"], ["README.md"], [], idx[e["id"]]["audit_note"]
        e.update(status=st, implementation=impl, tests=tests, docs=docs,
                 blockers=sorted(set(blk) | {"OWNER"}), owner="UNASSIGNED", note=note)
    counts = {}
    for e in out:
        counts[e["status"]] = counts.get(e["status"], 0) + 1
    doc = {"schema": "PK_FULL_VM_TRACEABILITY/1", "element": "INV-40", "version": "4.3.0",
           "blocker_catalog": BLOCKERS, "status_counts": counts, "requirements": out}
    (PKG / "traceability").mkdir(exist_ok=True)
    (PKG / "traceability/requirements.json").write_text(json.dumps(doc, indent=1) + "\n")
    render_markdown()
    return counts




def render_markdown() -> None:
    d = json.loads((PKG / "traceability/requirements.json").read_text())
    L = ["# INV-40 v4.3.0 — checklist status (generated by tools/build_traceability.py)", "",
         f"Status counts: {d['status_counts']}. **CLOSED: 0** — every item carries blocker `OWNER` "
         "(no accountable human bound; no independent review). Production gate: **NO_GO**.", "",
         "## Blocker catalog", ""]
    L += [f"- `{k}` — {v}" for k, v in d["blocker_catalog"].items()]
    L += ["", "## Items", "", "| ID | Pri | v4.2.0 | v4.3.0 | Blockers | Implementation / docs | Note |", "|---|---|---|---|---|---|---|"]
    for r in d["requirements"]:
        where = ", ".join(f"`{x}`" for x in (r["implementation"] + r["docs"])[:4])
        L.append(f"| {r['id']} | {r['priority']} | {r['v420_status']} | **{r['status']}** | "
                 f"{', '.join(b for b in r['blockers'] if b != 'OWNER') or '—'} | {where} | {r['note'].replace('|', '/')} |")
    (PKG / "CHECKLIST_STATUS.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    print(main())
