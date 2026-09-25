"""Execute the MC checklist workflow against this package and emit evidence.

Usage (from the directory containing ``inv06_traditional_iac``)::

    python inv06_traditional_iac/tools/build_status.py [CHECKLIST.md]

Produces:
  governance/READINESS.json          72 MC items with status/artifacts/tests
  governance/TRACEABILITY.json       REQ → source → code → test → evidence → gate
  governance/CHECKLIST_STATUS.json   status of every checklist control (baseline, SC, DoD)
  governance/COMPONENT_CHECKLISTS.md the supplied checklist with evidenced items ticked
  evidence/test_results.json, benchmarks.json, capacity_model.json, copy_audit.json,
  evidence/sbom.cdx.json, acceptance_evidence.json, PRODUCTION_GATE.json
  MANIFEST.sha256

Signing: if ``INV06_EVIDENCE_KEY`` (≥32 bytes) is set, evidence is HMAC-signed
with it; otherwise evidence is digest-only and the gate records it as unsigned.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys

PKG = pathlib.Path(__file__).resolve().parents[1]
ROOT = PKG.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(PKG / "tools"))

import importlib  # noqa: E402

pkg = importlib.import_module(PKG.name)
release = importlib.import_module(PKG.name + ".release")
security = importlib.import_module(PKG.name + ".security")
from readiness_table import ALL, CHECK_RULES, CODE, DRAFT_DOC_CHECKS, EXTERNAL_CHECKS, ITEMS, OWNER_CHECKS  # noqa: E402

GOV, EVD = PKG / "governance", PKG / "evidence"
EVD.mkdir(exist_ok=True)


def dump(path: pathlib.Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_tests() -> dict:
    out = {}
    for name in ("test_component", "test_production"):
        for flags in ([], ["-O"]):
            cp = subprocess.run([sys.executable, *flags, str(PKG / "tests" / f"{name}.py")], capture_output=True, text=True, cwd=ROOT, timeout=900)
            tail = cp.stderr.strip().splitlines()
            ran = next((l for l in tail if l.startswith("Ran ")), "Ran ? tests")
            out[f"{name}{' -O' if flags else ''}"] = {"returncode": cp.returncode, "summary": ran + " / " + (tail[-1] if tail else ""),
                                                      "tests": int(ran.split()[1]) if ran.split()[1].isdigit() else None}
    out["all_passed"] = all(v["returncode"] == 0 for v in out.values() if isinstance(v, dict))
    return out


def traceability() -> dict:
    rows = []
    for line in (GOV / "REQUIREMENTS.md").read_text("utf-8").splitlines():
        m = re.match(r"\| (REQ-\d+) \| (.+?) \| (.+?) \| (.+?) \|$", line)
        if not m:
            continue
        rid, text, src, tests = m.groups()
        mcs = re.findall(r"MC-\d{3}", src)
        code = sorted({a for i in ITEMS if i[0] in mcs for a in i[3] if a.endswith(".py")}) or ["state.py"]
        rows.append({"requirement": rid, "statement": text, "source": src.strip(), "design": "governance/ARCHITECTURE.md",
                     "code": code, "tests": [t.strip() for t in re.split(r";", tests)], "evidence": "evidence/test_results.json",
                     "gate": "evidence/PRODUCTION_GATE.json"})
    return {"schema": "PK_TRACEABILITY/1", "rows": rows, "count": len(rows)}


def parse_checklist(md: str):
    comps = re.split(r"\n(?=# MC-\d{3} — )", md)
    return comps[0], comps[1:]


def status_for(mc: str, tier: str, kind: str, n: int | None) -> str:
    if tier == "blocked":
        return "blocked"
    if tier == "owner-required":
        return "owner-required"
    if tier == "external":
        return "external"
    if kind != "CHK":
        return "open"
    if n in OWNER_CHECKS:
        return "owner-required"
    if n in EXTERNAL_CHECKS:
        return "external"
    if tier == "draft":
        return "draft" if n in DRAFT_DOC_CHECKS else "open"
    rule = CHECK_RULES.get(n)
    if rule == ALL or (isinstance(rule, set) and mc in rule):
        return "met"
    return "open"


def main(checklist_path: str | None) -> int:
    tiers = {i[0]: i for i in ITEMS}
    dump(GOV / "READINESS.json", {"schema": "PK_READINESS/1", "version": pkg.__version__,
                                  "items": [{"id": i, "title": t, "status": s, "artifacts": a, "tests": te} for i, t, s, a, te in ITEMS]})
    dump(GOV / "TRACEABILITY.json", traceability())

    tests = run_tests()
    dump(EVD / "test_results.json", tests)
    bench = release.run_benchmarks()
    dump(EVD / "benchmarks.json", bench)
    slo = release.check_slos(bench)
    dump(EVD / "capacity_model.json", release.capacity_model(bench) | {"slo_check": slo})
    dump(EVD / "copy_audit.json", release.copy_audit())
    dump(EVD / "sbom.cdx.json", {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1,
                                 "metadata": {"component": {"type": "library", "name": "inv06-traditional-iac", "version": pkg.__version__}},
                                 "components": [], "dependencies": [],
                                 "properties": [{"name": "runtime-dependencies", "value": "none (python stdlib only)"}]})

    # ---- checklist execution
    statuses: dict[str, dict] = {}
    totals: dict[str, int] = {}
    if checklist_path:
        md = pathlib.Path(checklist_path).read_text("utf-8")
        head, comps = parse_checklist(md)
        out_parts = [head]
        for comp in comps:
            mc = comp[2:8]
            _, title, tier, arts, tst = tiers[mc]
            ev = ", ".join(arts)
            lines = []
            for line in comp.split("\n"):
                m = re.match(r"- \[ \] \*\*(MC-\d{3})-(CHK|SC)-(\d+)\*\*", line)
                if m:
                    kind, n = m.group(2), int(m.group(3))
                    st = status_for(mc, tier, kind, n)
                    cid = f"{mc}-{kind}-{m.group(3)}"
                    statuses[cid] = {"status": st, "component": mc}
                    totals[st] = totals.get(st, 0) + 1
                    if st == "met":
                        line = line.replace("- [ ]", "- [x]", 1) + f" — ✅ **Met (package-local):** {ev}" + (f"; tests: {'; '.join(tst)}" if tst else "")
                    elif st != "open":
                        line += f" — ⏳ **{st}**"
                elif line.startswith("- [ ] ") and "Definition of Done" not in line:
                    # Definition-of-Done items: never self-certified.
                    did = f"{mc}-DOD-{sum(1 for k in statuses if k.startswith(mc + '-DOD')) + 1:02d}"
                    statuses[did] = {"status": "open", "component": mc}
                    totals["open"] = totals.get("open", 0) + 1
                elif line.startswith("- **Status:**"):
                    line = f"- **Status:** {tier} (v4.3.0 execution pass, 2026-09-22)"
                elif line.startswith("- **Evidence location:**"):
                    line = f"- **Evidence location:** {ev}"
                lines.append(line)
            out_parts.append("\n".join(lines))
        banner = ("\n> **Execution record (v4.3.0, 2026-09-22):** ticked items are evidenced by package-local code/tests/docs in "
                  "`inv06_traditional_iac` 4.3.0. Unticked items are open, draft, owner-required, external or blocked as annotated. "
                  "Definition-of-Done items are never self-certified; they require the independent reviewers named in `governance/OWNERS.yaml`.\n")
        (GOV / "COMPONENT_CHECKLISTS.md").write_text(out_parts[0] + banner + "\n" + "\n".join(out_parts[1:]), encoding="utf-8")
    per_comp: dict[str, dict[str, int]] = {}
    for cid, v in statuses.items():
        d = per_comp.setdefault(v["component"], {})
        d[v["status"]] = d.get(v["status"], 0) + 1
    dump(GOV / "CHECKLIST_STATUS.json", {"schema": "PK_CHECKLIST_STATUS/1", "totals": totals, "per_component": per_comp, "controls": statuses})

    # ---- evidence + gate
    key = os.environ.get("INV06_EVIDENCE_KEY", "").encode()
    if len(key) >= 32:
        signer = security.Signer(security.StaticKeyProvider({"evidence": key}, {"evidence": "evidence"}), "evidence")
        ev = release.build_evidence(version=pkg.__version__, tests=tests, bench=bench, signer=signer)
        evidence_ok = True
    else:
        class _Unsigned:
            def sign(self, payload):
                return {"alg": "none", "note": "INV06_EVIDENCE_KEY not provided; digest-only evidence"}
        ev = release.build_evidence(version=pkg.__version__, tests=tests, bench=bench, signer=_Unsigned())
        evidence_ok = False
    dump(EVD / "acceptance_evidence.json", ev)
    readiness = json.loads((GOV / "READINESS.json").read_text())
    gate = release.production_gate(checklist_status={"totals": totals}, readiness=readiness, evidence_ok=evidence_ok,
                                   tests_ok=tests["all_passed"], slo_ok=slo["pass"])
    dump(EVD / "PRODUCTION_GATE.json", gate)

    # ---- human-readable execution report
    rows = []
    for i, t, st, arts, _ in ITEMS:
        c = per_comp.get(i, {})
        rows.append(f"| {i} | {t} | {st} | {c.get('met', 0)} | {c.get('open', 0)} | {c.get('owner-required', 0) + c.get('external', 0) + c.get('blocked', 0) + c.get('draft', 0)} | {', '.join(arts)} |")
    rep = [f"# INV-06 {pkg.__version__} — Checklist Execution Report", "",
           f"Gate verdict: **{gate['verdict']}**. Controls: " + ", ".join(f"{k} {v}" for k, v in sorted(totals.items())) + f" (total {sum(totals.values())}).", "",
           "Tests: " + "; ".join(f"`{k}` {v['summary']}" for k, v in tests.items() if isinstance(v, dict)), "",
           f"Reference SLO check: {'PASS' if slo['pass'] else 'FAIL'}.", "",
           "## Blockers", *[f"- {b}" for b in gate["blockers"]], "", "## Conditions", *[f"- {c}" for c in gate["conditions"]], "",
           "## Per component", "", "| ID | Component | Disposition | Met | Open | Pending (draft/owner/external/blocked) | Artifacts |", "|---|---|---|---|---|---|---|", *rows, "",
           "What \"met\" means: a control is ticked only when a package-local artifact or automated test evidences it. Independent review (CHK-050), owner identity (CHK-003), KMS/at-rest crypto (CHK-020), real adjacent-system integration (CHK-039), production-scale load (CHK-044) and vulnerability scanning (CHK-046) are never self-certified. The same applies to every Definition-of-Done item."]
    (PKG / "EXECUTION_REPORT.md").write_text("\n".join(rep) + "\n", encoding="utf-8")

    # ---- manifest (last, so it covers everything above)
    lines = []
    for p in sorted(PKG.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts and p.name != "MANIFEST.sha256" and not p.name.endswith(".pyc"):
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  ./{p.relative_to(PKG).as_posix()}")
    (PKG / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")
    print(json.dumps({"tests": {k: v["summary"] for k, v in tests.items() if isinstance(v, dict)}, "slo": slo, "totals": totals,
                      "gate": gate["verdict"], "blockers": len(gate["blockers"]), "conditions": len(gate["conditions"])}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
