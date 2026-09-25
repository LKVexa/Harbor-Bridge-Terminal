"""Requirements traceability matrix generator / CI gate (#43).

Parses the professional completion checklist (every checkbox gets a stable ID
``GAP07-CL-<component>-<n>`` / ``GAP07-CL-G-<n>`` / ``GAP07-CL-F-<n>``), imports the
100 historical controls from CHECKLIST.json unchanged, and joins them with the
component implementation map below.  States follow the checklist vocabulary:
design-complete, code-complete, test-complete, integrated, production-validated,
waived, blocked.  Item states are inherited from their component, except items
whose text requires an activity this package cannot perform (independent review,
live provider/registry/fleet runs, production-equivalent environments...), which
are marked ``blocked`` with the external owner - so aggregate percentages can
never hide a P0 gap.

  python tools/traceability.py            # write TRACEABILITY.json + TRACEABILITY.md
  python tools/traceability.py --check    # CI gate: stale links, P0 honesty
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys

import _path

ROOT = _path.ROOT
CHECKLIST = os.path.join(ROOT, "docs", "GAP07_MISSING_COMPONENTS_PROFESSIONAL_CHECKLIST_v5.0.0.md")

T = "tests/"
C = {  # component -> (state, modules, tests, operational evidence, external dependency note)
    1: ("test-complete", ["algorithms.py", "signing.py", "canonical.py", "docs/SIGNATURE_PROFILE.md"], [T + "test_v6_signing.py", T + "test_v6_assurance.py"], ["vectors/v6_vectors.json"], "independent crypto review (#37); CI matrix run on Windows/edge/Wasm verifiers"),
    2: ("code-complete", ["keys.py", "docs/KEY_CEREMONY.md"], [T + "test_v6_keys.py"], ["ops/alerts/gap07-rules.yaml"], "live-provider conformance runs against the estate's chosen KMS/HSM; IAM least-privilege evidence"),
    3: ("test-complete", ["trust.py", "docs/adr/ADR-002-trust-roots.md"], [T + "test_v6_trust.py"], [], "CRL/OCSP not implemented (revocation via signed trust deltas); PKI review"),
    4: ("test-complete", ["dsse.py", "docs/adr/ADR-005-attestation-format.md"], [T + "test_v6_attest_tlog.py", T + "test_v6_admission.py"], [], "conformance fixtures from external SLSA producers (e.g. slsa-github-generator) not bundled"),
    5: ("test-complete", ["tlog.py", "docs/adr/ADR-004-transparency.md"], [T + "test_v6_attest_tlog.py"], [], "live Rekor/private-log service; RekorClient is an adapter skeleton"),
    6: ("test-complete", ["store.py", "docs/adr/ADR-007-persistence.md"], [T + "test_v6_state.py"], ["docs/RUNBOOKS.md"], "encryption-at-rest of trust metadata is deployment-side (integrity is enforced)"),
    7: ("test-complete", ["distribution.py"], [T + "test_v6_state.py"], ["docs/RUNBOOKS.md"], "authenticated transport (mTLS relay) is estate-side"),
    8: ("test-complete", ["policy.py", "fixtures/gap13/"], [T + "test_v6_admission.py", T + "test_v6_integration.py"], [], "real GAP-13 engine end-to-end run"),
    9: ("test-complete", ["registry.py"], [T + "test_v6_admission.py"], [], "live OCI registry client + auth; tested against local content store"),
    10: ("test-complete", ["admission.py", "service.py", "docs/ADMISSION_PATHS.md", "deploy/k8s/gap07.yaml"], [T + "test_v6_admission.py", T + "test_v6_integration.py"], ["ops/alerts/gap07-rules.yaml"], "AdmissionReview translation + runtime plugins; penetration testing"),
    11: ("test-complete", ["audit_export.py"], [T + "test_v6_admission.py"], ["docs/RUNBOOKS.md"], "WORM/object-lock storage configuration and retention tests"),
    12: ("test-complete", ["timesrc.py"], [T + "test_v6_state.py"], ["docs/RUNBOOKS.md"], "NTS/TPM time sources feeding the time authority"),
    13: ("test-complete", ["policy.py", "dsse.py"], [T + "test_v6_admission.py", T + "test_v6_attest_tlog.py"], [], ""),
    14: ("test-complete", ["compromise.py"], [T + "test_v6_admission.py"], ["docs/RUNBOOKS.md"], "incident drill with estate SOC"),
    15: ("test-complete", ["controls.py"], [T + "test_v6_admission.py"], [], ""),
    16: ("test-complete", ["sbom.py"], [T + "test_v6_admission.py"], [], "vulnerability feed integration (VEX producer) estate-side"),
    17: ("test-complete", ["admission.py", "schemas/PK_ARTIFACT_BUNDLE-1.schema.json"], [T + "test_v6_admission.py"], [], ""),
    18: ("test-complete", ["canonical.py", "vectors/v6_vectors.json", "tools/gen_vectors.py"], [T + "test_v6_assurance.py"], [], "non-Python consumer implementations must run the vectors"),
    19: ("test-complete", ["algorithms.py", "COMPATIBILITY.json"], [T + "test_v6_signing.py"], [], ""),
    20: ("test-complete", ["controls.py"], [T + "test_v6_admission.py"], [], ""),
    21: ("test-complete", ["trust.py", "signing.py", "admission.py"], [T + "test_v6_signing.py", T + "test_v6_admission.py"], [], ""),
    22: ("test-complete", ["controls.py"], [T + "test_v6_admission.py"], ["ops/alerts/gap07-rules.yaml"], ""),
    23: ("test-complete", ["registry.py"], [T + "test_v6_admission.py"], [], ""),
    24: ("test-complete", ["store.py"], [T + "test_v6_state.py"], [], ""),
    25: ("test-complete", ["telemetry.py", "service.py"], [T + "test_v6_admission.py", T + "test_v6_integration.py"], [], "OTel SDK exporter wiring (IDs/attributes are OTel-compatible)"),
    26: ("design-complete", ["ops/alerts/gap07-rules.yaml", "ops/dashboards/gap07-dashboard.json"], [], [], "load into estate Prometheus/Grafana and fire-drill alerts"),
    27: ("test-complete", ["distribution.py", "ops/slo-budgets.json"], [T + "test_v6_state.py"], [], "fleet-wide measurement"),
    28: ("code-complete", ["COMPATIBILITY.json", "tools/traceability.py"], [], [], ""),
    29: ("test-complete", [T + "test_v6_assurance.py"], [T + "test_v6_assurance.py"], [], "coverage-guided fuzzing (atheris/OSS-Fuzz) for long campaigns"),
    30: ("test-complete", [T + "test_v6_assurance.py"], [T + "test_v6_assurance.py"], [], ""),
    31: ("test-complete", [T + "test_v6_assurance.py", T + "test_v6_state.py"], [T + "test_v6_assurance.py"], [], ""),
    32: ("test-complete", [T + "test_v6_assurance.py", T + "test_v6_state.py", T + "test_v6_keys.py"], [T + "test_v6_assurance.py"], [], "network-partition / real disk-full on target hosts"),
    33: ("code-complete", ["tools/benchmark.py", "ops/slo-budgets.json"], [], ["RELEASE_EVIDENCE.json"], "edge-node power/thermal measurement on target hardware"),
    34: ("code-complete", ["tools/soak.py"], [], [], "fleet-scale soak on real sites"),
    35: ("test-complete", ["store.py", "docs/RUNBOOKS.md"], [T + "test_v6_state.py"], [], "RPO/RTO drill evidence"),
    36: ("design-complete", ["docs/THREAT_MODEL.md"], [], [], "threat-model review sign-off"),
    37: ("blocked", ["docs/SECURITY_REVIEW.md"], [], [], "independent reviewer - cannot be self-certified"),
    38: ("code-complete", ["tools/release.py"], [], ["RELEASE_EVIDENCE.json", "SBOM.cdx.json", "MANIFEST.sha256"], ""),
    39: ("design-complete", ["DEPENDENCIES.md", "requirements.txt", "tools/release.py"], [], ["SBOM.cdx.json"], "pip-audit + lockfile run in CI"),
    40: ("design-complete", ["docs/RUNBOOKS.md"], [], [], "game-day exercises"),
    41: ("design-complete", ["OWNERS.yaml"], [], [], "named owners/on-call to be assigned by the estate"),
    42: ("design-complete", ["docs/adr/"], [], [], "ADR-003/004 have open estate decisions"),
    43: ("code-complete", ["tools/traceability.py", "TRACEABILITY.json"], [], [], ""),
    44: ("blocked", ["contract.py", "component.py"], [T + "test_component.py"], [], "estate pk_core package not supplied"),
    45: ("blocked", ["fixtures/gap13/"], [T + "test_v6_integration.py"], [], "GAP-06/GAP-08/PLN-06/PLN-07 implementations not supplied; only GAP-13 contract fixtures included"),
    46: ("design-complete", ["ci/github-workflow.yml"], [], [], "install into the estate repository and run"),
    47: ("design-complete", ["deploy/k8s/gap07.yaml"], [], [], "image build, registry, cert-manager issuer, PVC class are estate-specific"),
    48: ("code-complete", ["tools/release.py"], [], [], "release-authority key ceremony + pinned SPKI distribution"),
}
PRIORITY = {**{i: "P0" for i in range(1, 13)}, **{i: "P1" for i in range(13, 29)}, **{i: "P2" for i in range(29, 44)}, **{i: "External" for i in range(44, 49)}}
EXTERNAL_WORDS = re.compile(r"(independent|reviewer|review confirms|review validates|passes security review|penetration|production-equivalent|"
                            r"windows|edge nodes|embedded/wasm|cross-platform|cross-language|multiple in-toto|heterogeneous|drill|game|fleet|"
                            r"target hardware|power/thermal|named|on-call|compliance|legal hold|worm|object-lock|clean environment|authenticated `pk_core`|"
                            r"gap-06|gap-08|pln-06|pln-07|least-privilege and tied|iam|workload identity|ceremony|encrypt|crl|ocsp|opentelemetry|retention|authenticated tls|mutually authenticated|authenticated transport|nts|tpm time|ptp)", re.I)


def parse():
    items, comp, section, n = [], "G", "Global completion gates", {}
    for line in open(CHECKLIST, encoding="utf-8"):
        m = re.match(r"^## (\d+)\. (.+)", line)
        if m:
            comp, section = int(m.group(1)), m.group(2).strip()
            continue
        if line.startswith("## ") and ("Final" in line or "Release" in line or "Recommended" in line):
            comp, section = "F", line[3:].strip()
        m = re.match(r"^- \[ \] (.+)", line)
        if m:
            n[comp] = n.get(comp, 0) + 1
            items.append({"id": f"GAP07-CL-{comp}-{n[comp]:02d}", "component": comp, "section": section, "text": m.group(1).strip()})
    return items


def build():
    items = parse()
    rows = []
    for it in items:
        c = it["component"]
        if isinstance(c, int):
            state, mods, tests, ops, ext = C[c]
            pri = PRIORITY[c]
        else:
            state, mods, tests, ops, ext, pri = "design-complete", ["README.md", "docs/"], [], [], "programme-level gate", "Global" if c == "G" else "Final"
        item_state = state
        blocker = None
        if EXTERNAL_WORDS.search(it["text"]) and state != "blocked":
            item_state, blocker = "blocked", ext or "requires an activity outside this package"
        elif state == "blocked":
            blocker = ext
        rows.append({**it, "priority": pri, "state": item_state, "component_state": state, "implementation": mods, "tests": tests,
                     "operational_evidence": ops, "external_dependency": ext or None, "blocker": blocker, "owner": "UNASSIGNED (see OWNERS.yaml)"})
    with open(os.path.join(ROOT, "CHECKLIST.json"), encoding="utf-8") as fh:
        hist = json.load(fh)["items"]
    legacy = [{"id": h["check_id"], "dimension": h["dimension"], "text": h["requirement"], "state": "blocked",
               "blocker": "assessment executes through the estate pk_core adapter (component 44)", "implementation": ["component.py", "contract.py"]} for h in hist]
    summary = {}
    for r in rows:
        s = summary.setdefault(r["priority"], {})
        s[r["state"]] = s.get(r["state"], 0) + 1
    p0_open = [r["id"] for r in rows if r["priority"] == "P0" and r["state"] != "production-validated"]
    doc = {"schema": "PK_TRACEABILITY/1", "checklist_sha256": hashlib.sha256(open(CHECKLIST, "rb").read()).hexdigest(),
           "states": ["design-complete", "code-complete", "test-complete", "integrated", "production-validated", "waived", "blocked"],
           "summary_by_priority": summary, "p0_not_production_validated": len(p0_open),
           "production_ready": False if p0_open else True, "items": rows, "historical_controls": legacy}
    return doc


def md(doc):
    lines = ["# GAP-07 traceability matrix (generated - do not edit)", "",
             f"Checklist digest `{doc['checklist_sha256'][:16]}…`. P0 items not production-validated: **{doc['p0_not_production_validated']}**. production_ready = **{doc['production_ready']}**.", "",
             "| priority | " + " | ".join(doc["states"]) + " |", "|---|" + "---|" * len(doc["states"])]
    for p, s in sorted(doc["summary_by_priority"].items()):
        lines.append(f"| {p} | " + " | ".join(str(s.get(x, 0)) for x in doc["states"]) + " |")
    lines += ["", "## Component view", "", "| # | component state | implementation | blocker / external |", "|---|---|---|---|"]
    for c, (state, mods, *_rest, ext) in C.items():
        lines.append(f"| {c} | {state} | {', '.join('`'+m+'`' for m in mods[:3])} | {ext or '—'} |")
    return "\n".join(lines) + "\n"


def check(doc):
    missing = sorted({p for r in doc["items"] for p in r["implementation"] + r["tests"] + r["operational_evidence"]
                      if p not in ("TRACEABILITY.json", "RELEASE_EVIDENCE.json", "SBOM.cdx.json", "MANIFEST.sha256", "COMPATIBILITY.json") and not os.path.exists(os.path.join(ROOT, p))})
    bad = [r["id"] for r in doc["items"] if r["priority"] == "P0" and not r["implementation"]]
    if missing or bad:
        print(json.dumps({"stale_links": missing, "p0_without_implementation": bad}, indent=2))
        return 1
    print(json.dumps({"ok": True, "items": len(doc["items"]), "historical": len(doc["historical_controls"]),
                      "p0_not_production_validated": doc["p0_not_production_validated"], "production_ready": doc["production_ready"]}))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    d = build()
    if a.check:
        sys.exit(check(d))
    with open(os.path.join(ROOT, "TRACEABILITY.json"), "w", encoding="utf-8") as fh:
        json.dump(d, fh, indent=1)
        fh.write("\n")
    with open(os.path.join(ROOT, "TRACEABILITY.md"), "w", encoding="utf-8") as fh:
        fh.write(md(d))
    print(json.dumps({"items": len(d["items"]), "summary": d["summary_by_priority"]}, indent=1))
