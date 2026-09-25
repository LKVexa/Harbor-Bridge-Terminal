"""Requirements traceability: C001-C100 and GAP-001..042 -> code/config/tests/docs/evidence.

    python -m inv21_local_service_chaining.tools.traceability --out evidence/traceability.json --md docs/TRACEABILITY.md

Statuses in ``GAPS`` are implementer-asserted CEILINGS. This tool (and the release
gate, which passes the failing test modules of its own run) can only LOWER them:
a gap whose cited test module failed in the gate run is downgraded to ``partial``.

Status vocabulary (never upgraded by this tool):
* ``implemented_unverified`` -- every referenced artifact exists and the referenced
  tests pass in the recorded gate run; awaits independent second-pass audit.
* ``partial``   -- implemented with a named residual that blocks closure.
* ``blocked``   -- cannot be completed from this repository; blocker named.
* ``verified``  -- ONLY set from an independent reviewer record in
  governance/approvals.json (none exists, so nothing is verified).
"""
from __future__ import annotations

import argparse
import json
import pathlib

PKG = pathlib.Path(__file__).resolve().parents[1]

# id: (status, owner/system-of-record, impl, tests, docs, residual)
GAPS = {
    "GAP-001": ("blocked", "pk_core framework", ["../pyproject.toml", "tests/test_component.py"], ["tests/test_component.py"],
                ["docs/COMPATIBILITY.md"], "pk_core source/version/hash UNRESOLVED; conformance test fails (no skip)"),
    "GAP-002": ("partial", "package metadata", ["../pyproject.toml", "../constraints.txt", "../MANIFEST.in"],
                ["tests/test_packaging.py"], ["docs/OPERATIONS.md"], "licence metadata placeholder pending GAP-039"),
    "GAP-003": ("implemented_unverified", "schemas/", ["schemas", "schema.py", "tools/schema_diff.py"],
                ["tests/test_errors_schema.py", "tests/test_second_pass_findings.py"], ["docs/COMPATIBILITY.md"],
                "second-pass SP-09 fixed; re-audit required"),
    "GAP-004": ("partial", "INV-13 capability authority", ["policy.py", "chain.py"], ["tests/test_policy_residency.py", "tests/test_second_pass_findings.py",
                "tests/test_fault_injection.py", "tests/test_adjacent_contracts.py"], ["docs/adr/ADR-002-fail-closed-capability-provider.md"],
                "real INV-13 provider not present; wired via stand-in only"),
    "GAP-005": ("partial", "runtime identity issuer", ["context.py", "chain.py"], ["tests/test_identity_context.py",
                "tests/test_adversarial.py"], ["docs/adr/ADR-001-authenticated-call-context.md"],
                "workload attestation and KMS key distribution are estate services; bearer-token replay within max_token_age_s needs mTLS/channel binding (ADR-005)"),
    "GAP-006": ("implemented_unverified", "transport adapter", ["transport.py"], ["tests/test_async_transport.py",
                "tests/test_semantic_equivalence.py"], ["docs/adr/ADR-004-wire-protocol-and-error-envelope.md"], None),
    "GAP-007": ("implemented_unverified", "chain.py", ["chain.py"], ["tests/test_async_transport.py"], ["docs/DESIGN.md"], None),
    "GAP-008": ("implemented_unverified", "context.py/admission.py", ["context.py", "admission.py", "chain.py"],
                ["tests/test_admission_lifecycle_config.py", "tests/test_async_transport.py"], ["docs/DESIGN.md"], None),
    "GAP-009": ("implemented_unverified", "admission.py", ["admission.py", "chain.py"], ["tests/test_admission_lifecycle_config.py",
                "tests/test_fault_injection.py", "tests/test_concurrency.py", "tests/test_second_pass_findings.py"],
                ["docs/CAPACITY_MODEL.md"], "second-pass SP-03/SP-04 fixed; re-audit required"),
    "GAP-010": ("implemented_unverified", "INV-10 feed / residency.py", ["residency.py"], ["tests/test_policy_residency.py",
                "tests/test_second_pass_findings.py"], ["docs/adr/ADR-003-leased-residency.md"], "second-pass SP-07 fixed; re-audit required"),
    "GAP-011": ("implemented_unverified", "lifecycle.py", ["lifecycle.py"], ["tests/test_admission_lifecycle_config.py"],
                ["docs/DESIGN.md"], None),
    "GAP-012": ("implemented_unverified", "config.py", ["config.py", "schemas/chain_config.schema.json"],
                ["tests/test_admission_lifecycle_config.py"], ["docs/OPERATIONS.md"], None),
    "GAP-013": ("implemented_unverified", "ConfigStore", ["config.py", "chain.py"], ["tests/test_admission_lifecycle_config.py",
                "tests/test_second_pass_findings.py"], ["docs/OPERATIONS.md"], "second-pass SP-04 fixed; re-audit required"),
    "GAP-014": ("partial", "governance/OWNERS.json", ["governance/OWNERS.json", "../CODEOWNERS", "docs/adr"], [],
                ["docs/INCIDENT_RESPONSE.md"], "owner/escalation contacts PROPOSED, not confirmed; ADRs not approved"),
    "GAP-015": ("implemented_unverified", "tools/traceability.py", ["tools/traceability.py"], ["tests/test_governance.py"],
                ["docs/TRACEABILITY.md"], None),
    "GAP-016": ("partial", "docs/COMPATIBILITY.md", ["docs/COMPATIBILITY.md"], ["tests/test_runtime.py"], ["docs/COMPATIBILITY.md"],
                "pk_core and adjacent-component versions unknown"),
    "GAP-017": ("partial", "tools/release_gate.py", ["tools/release_gate.py", "tools/sbom.py"], ["tests/test_governance.py"],
                ["docs/PATCHING_EOL.md"], "artifact signing BLOCKED (no signing identity); vuln scan NOT_RUN (no scanner/index)"),
    "GAP-018": ("implemented_unverified", "audit.py", ["audit.py", "chain.py"], ["tests/test_audit_telemetry.py", "tests/test_adversarial.py",
                "tests/test_second_pass_findings.py"], ["docs/OPERATIONS.md"], "second-pass SP-05/SP-08 fixed; re-audit required"),
    "GAP-019": ("implemented_unverified", "telemetry.py/transport.py", ["telemetry.py", "chain.py", "transport.py"],
                ["tests/test_audit_telemetry.py", "tests/test_async_transport.py"], ["docs/OPERATIONS.md"], None),
    "GAP-020": ("implemented_unverified", "telemetry.py", ["telemetry.py"], ["tests/test_audit_telemetry.py"],
                ["docs/TELEMETRY_PRIVACY.md"], None),
    "GAP-021": ("partial", "ops/", ["ops/alerts.yaml", "ops/dashboard.grafana.json"], ["tests/test_governance.py"],
                ["docs/INCIDENT_RESPONSE.md"], "rules/dashboard not deployed or evaluated against a live Prometheus"),
    "GAP-022": ("partial", "tools/bench.py", ["tools/bench.py", "evidence/bench.json", "evidence/bench_baseline.json"],
                ["tools/bench.py --check"], ["docs/CAPACITY_MODEL.md"],
                "contract SLO p99<20us NOT MET in CPython; soak/fleet-scale and power/thermal not measured"),
    "GAP-023": ("implemented_unverified", "docs/CAPACITY_MODEL.md", ["docs/CAPACITY_MODEL.md", "chain.py"],
                ["tests/test_audit_telemetry.py"], ["docs/CAPACITY_MODEL.md"], None),
    "GAP-024": ("implemented_unverified", "tools/bench.py", ["tools/bench.py", "evidence/bench.json"], ["tools/bench.py"],
                ["docs/SEMANTIC_EQUIVALENCE.md"], None),
    "GAP-025": ("implemented_unverified", "tests", ["tests/test_fuzz_property.py"], ["tests/test_fuzz_property.py"], ["docs/THREAT_MODEL.md"], None),
    "GAP-026": ("implemented_unverified", "tests", ["tests/test_concurrency.py"], ["tests/test_concurrency.py"], ["docs/DESIGN.md"], None),
    "GAP-027": ("partial", "docs/THREAT_MODEL.md", ["tests/test_adversarial.py"], ["tests/test_adversarial.py",
                "tests/test_second_pass_findings.py"], ["docs/THREAT_MODEL.md"],
                "second-pass found identity spoofing the first suite missed (SP-01/02); fixed. Follow-up audit: in-process "
                "handler code can mint a hop seal via private chainer state (caller spoof) -- in-process handlers are "
                "inside the trust boundary; isolating them needs the INV-20 component sandbox"),
    "GAP-028": ("blocked", "assembled estate", ["tests/test_adjacent_contracts.py"], ["tests/test_adjacent_contracts.py"],
                ["docs/COMPATIBILITY.md"], "INV-20/INV-10/INV-16/INV-13/SCH-01 packages not in this repository"),
    "GAP-029": ("partial", "CI matrix", ["../.github/workflows/ci.yml"], ["(full suite on CPython 3.10-3.13)"],
                ["docs/COMPATIBILITY.md"], "only Linux x86_64 executed; aarch64/macOS/Windows untested"),
    "GAP-030": ("implemented_unverified", "tests", ["tests/test_fault_injection.py"], ["tests/test_fault_injection.py"],
                ["docs/OPERATIONS.md"], None),
    "GAP-031": ("implemented_unverified", "lifecycle.py/chain.py", ["lifecycle.py", "chain.py", "residency.py"],
                ["tests/test_admission_lifecycle_config.py"], ["docs/OPERATIONS.md"], None),
    "GAP-032": ("implemented_unverified", "residency.py", ["residency.py"], ["tests/test_policy_residency.py"],
                ["docs/OPERATIONS.md"], None),
    "GAP-033": ("implemented_unverified", "rollout.py", ["rollout.py"], ["tests/test_rollout.py"], ["docs/OPERATIONS.md"], None),
    "GAP-034": ("partial", "docs/PATCHING_EOL.md", ["docs/PATCHING_EOL.md"], [], ["docs/PATCHING_EOL.md"], "policy PROPOSED, not approved"),
    "GAP-035": ("partial", "docs/INCIDENT_RESPONSE.md", ["docs/INCIDENT_RESPONSE.md"], [], ["docs/INCIDENT_RESPONSE.md"],
                "contacts unassigned"),
    "GAP-036": ("partial", "governance/", ["governance/waivers.json", "governance/reviews.json"], ["tests/test_governance.py"],
                ["docs/REVIEWS.md"], "no review performed yet; waivers unapproved"),
    "GAP-037": ("implemented_unverified", "tools/release_gate.py", ["tools/release_gate.py"], ["tests/test_governance.py"],
                ["AUDIT_REPORT_4.3.0.md"], "gate runs and returns NO_GO (correctly)"),
    "GAP-038": ("partial", "../.github/workflows/ci.yml", ["../.github/workflows/ci.yml"], [], ["docs/OPERATIONS.md"],
                "workflow authored but never executed on a CI runner"),
    "GAP-039": ("blocked", "owner", ["../NOTICE"], [], [], "licence choice is an owner decision"),
    "GAP-040": ("partial", "context.py", ["context.py", "chain.py", "schemas/call_context.schema.json"],
                ["tests/test_identity_context.py", "tests/test_second_pass_findings.py"],
                ["docs/adr/ADR-001-authenticated-call-context.md"],
                "SP-01/SP-02 fixed for callers; residual: co-resident handler code can forge a hop seal or leak a sealed "
                "child ctx during its root call (same principal/tenant) -- needs INV-20 sandbox isolation"),
    "GAP-041": ("implemented_unverified", "errors.py", ["errors.py", "schemas/error.schema.json"], ["tests/test_errors_schema.py"],
                ["docs/DESIGN.md"], None),
    "GAP-042": ("implemented_unverified", "tests", ["tests/test_semantic_equivalence.py"], ["tests/test_semantic_equivalence.py"],
                ["docs/SEMANTIC_EQUIVALENCE.md"], "one documented allowed difference (cross-tenant code)"),
}

# Checklist items not covered by a GAP control mapping -> evidence (contract.py covers C001-C008 prose).
EXTRA = {
    "C001": ["contract.py", "docs/DESIGN.md"], "C002": ["contract.py", "README.md"], "C003": ["contract.py", "docs/COMPATIBILITY.md"],
    "C004": ["contract.py", "docs/DESIGN.md"], "C005": ["contract.py", "docs/DESIGN.md"], "C006": ["contract.py", "config.py"],
    "C007": ["contract.py"], "C008": ["contract.py", "docs/COMPATIBILITY.md"], "C009": ["governance/OWNERS.json"],
    "C010": ["docs/adr"], "C012": ["docs/DESIGN.md"], "C013": ["contract.py", "docs/CAPACITY_MODEL.md"],
    "C015": ["lifecycle.py"], "C017": ["admission.py"], "C019": ["docs/DESIGN.md"], "C020": ["tools/traceability.py"],
    "C025": ["context.py", "admission.py"], "C027": ["docs/COMPATIBILITY.md"], "C028": ["docs/CAPACITY_MODEL.md", "transport.py"],
    "C032": ["../pyproject.toml", "config.py"], "C033": ["config.py"], "C034": ["config.py"], "C035": ["config.py"],
    "C036": ["config.py"], "C037": ["config.py"], "C038": ["config.py", "rollout.py"], "C039": ["docs/OPERATIONS.md", "telemetry.py"],
    "C041": ["docs/THREAT_MODEL.md"], "C043": ["docs/THREAT_MODEL.md"], "C045": ["tools/release_gate.py"],
    "C046": ["chain.py", "residency.py"], "C047": ["transport.py"], "C049": ["audit.py"], "C050": ["tests/test_adversarial.py"],
    "C052": ["chain.py"], "C053": ["admission.py"], "C054": ["admission.py"], "C057": ["residency.py"], "C058": ["residency.py"],
    "C059": ["lifecycle.py"], "C060": ["tests/test_fault_injection.py"], "C061": ["tools/bench.py"], "C062": ["docs/CAPACITY_MODEL.md"],
    "C063": ["tools/bench.py"], "C064": ["tools/bench.py"], "C065": ["tools/bench.py"], "C066": ["chain.py"], "C067": ["docs/CAPACITY_MODEL.md"],
    "C068": ["docs/CAPACITY_MODEL.md"], "C069": ["docs/CAPACITY_MODEL.md"], "C070": ["tools/bench.py"], "C071": ["chain.py"],
    "C072": ["telemetry.py"], "C073": ["audit.py"], "C074": ["context.py"], "C075": ["telemetry.py"], "C076": ["telemetry.py"],
    "C077": ["chain.py"], "C078": ["audit.py"], "C079": ["docs/TELEMETRY_PRIVACY.md"], "C080": ["ops/alerts.yaml"],
    "C081": ["tests"], "C083": ["tests/test_adjacent_contracts.py"], "C084": ["docs/COMPATIBILITY.md"], "C085": ["tests/test_fuzz_property.py"],
    "C086": ["tests/test_concurrency.py"], "C087": ["tests/test_adversarial.py"], "C088": ["tools/bench.py"], "C089": ["tests/test_fault_injection.py"],
    "C091": ["contract.py", "docs/CAPACITY_MODEL.md"], "C092": ["rollout.py", "docs/OPERATIONS.md"], "C094": ["docs/PATCHING_EOL.md"],
    "C095": ["docs/OPERATIONS.md"], "C096": ["docs/OPERATIONS.md"], "C097": ["docs/INCIDENT_RESPONSE.md"], "C098": ["docs/REVIEWS.md"],
    "C099": ["governance/waivers.json"], "C100": ["tools/release_gate.py"],
}
# items whose status is dominated by a named residual regardless of mapping
C_RESIDUAL = {
    "C009": "owner/escalation unconfirmed", "C010": "ADRs not approved", "C047": "TLS supported/enforced off-loopback; at-rest encryption of audit log is an estate storage control",
    "C062": "SLO p99<20us not met", "C068": "power/thermal not measured", "C084": "only Linux x86_64 executed",
    "C088": "no soak/fleet-scale run", "C091": "SLO/error budget not approved", "C094": "policy not approved",
    "C097": "contacts unassigned", "C098": "no review performed yet",
}
ORDER = {"blocked": 0, "partial": 1, "implemented_unverified": 2, "verified": 3}


def build(failing_modules=()) -> dict:
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    comps = json.loads((PKG / "MISSING_COMPONENTS_4.2.0.json").read_text())["components"]
    by_c: dict = {}
    for c in comps:
        for cid in c["checklist"]:
            by_c.setdefault(cid, []).append(c["id"])
    approvals = json.loads((PKG / "governance/approvals.json").read_text())["approvals"]
    verified = {a["item"] for a in approvals if a.get("kind") == "independent_verification"}

    def exists(ref):
        if ref.startswith("(") or " " in ref:
            return True
        return (PKG / ref).exists()

    gaps = []
    for gid, (st, sor, impl, tests, docs, residual) in GAPS.items():
        missing = [r for r in impl + tests + docs if not exists(r)]
        status = "verified" if gid in verified else st
        failed = [m for m in failing_modules if any(m in x for x in tests)]
        if failed and status == "implemented_unverified":
            status = "partial"; residual = (residual or "") + f"; cited tests failed in gate run: {failed}"
        if missing and status != "blocked":
            status = "partial"; residual = (residual or "") + f"; missing artifacts: {missing}"
        comp = next(c for c in comps if c["id"] == gid)
        gaps.append({"id": gid, "title": comp["name"], "severity": comp["severity"], "controls": comp["checklist"],
                     "system_of_record": sor, "status": status, "implementation": impl, "tests": tests, "docs": docs,
                     "residual": residual, "closure_rule": "close only after independent second-pass audit"})
    gstat = {g["id"]: g["status"] for g in gaps}
    rows = []
    for it in items:
        cid = it["check_id"]; short = cid.split("-")[-1]
        glist = by_c.get(cid, [])
        refs = sorted(set(EXTRA.get(short, []) + [r for g in glist for r in GAPS[g][2] + GAPS[g][3]]))
        sts = [gstat[g] for g in glist]
        status = min(sts, key=ORDER.get) if sts else ("implemented_unverified" if refs else "blocked")
        residual = C_RESIDUAL.get(short)
        if residual and ORDER[status] > ORDER["partial"]:
            status = "partial"
        if not refs:
            residual = (residual or "") + " no evidence mapped"
        rows.append({"check_id": cid, "dimension": it["dimension"], "requirement": it["requirement"], "gaps": glist,
                     "evidence": refs, "status": "verified" if cid in verified else status, "residual": residual})
    summary = {s: sum(1 for r in rows if r["status"] == s) for s in ORDER}
    gsummary = {s: sum(1 for g in gaps if g["status"] == s) for s in ORDER}
    return {"schema": "INV21_TRACEABILITY/1", "items": rows, "gaps": gaps, "summary_checklist": summary,
            "summary_gaps": gsummary, "unmapped": [r["check_id"] for r in rows if not r["evidence"]]}


def to_md(t: dict) -> str:
    out = ["# INV-21 Requirements Traceability (generated by tools/traceability.py — do not edit)", "",
           f"Checklist status: {t['summary_checklist']}  ", f"Gap status: {t['summary_gaps']}", "",
           "## Gaps", "", "| Gap | Sev | Status | Evidence | Residual |", "|---|---|---|---|---|"]
    for g in t["gaps"]:
        out.append(f"| {g['id']} {g['title']} | {g['severity']} | {g['status']} | "
                   f"{', '.join(g['implementation'] + g['tests'])} | {g['residual'] or ''} |")
    out += ["", "## Checklist C001–C100", "", "| Item | Gaps | Status | Evidence | Residual |", "|---|---|---|---|---|"]
    for r in t["items"]:
        out.append(f"| {r['check_id']} | {', '.join(r['gaps'])} | {r['status']} | {', '.join(r['evidence'])} | {r['residual'] or ''} |")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out"); ap.add_argument("--md")
    a = ap.parse_args(argv)
    t = build()
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(t, indent=1) + "\n")
    if a.md:
        pathlib.Path(a.md).write_text(to_md(t))
    print(json.dumps({"checklist": t["summary_checklist"], "gaps": t["summary_gaps"], "unmapped": t["unmapped"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
