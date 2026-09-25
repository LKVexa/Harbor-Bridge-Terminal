"""C020: requirements traceability. Joins CHECKLIST.json (100 C-ids), the pk_core findings
(status + evidence per C-id, from conformance/pk_workflow_report.json), the 64 closure
components and spec/requirements.json into traceability/requirements-traceability.json.
``--check`` fails if any C-id is untraced or any referenced path is missing."""
import json, re, sys
from _tools_pkg import ROOT


def expand(ctrl):
    ids = set()
    for part in ctrl.replace(" ", "").split(","):
        m = re.fullmatch(r"C(\d{3})(?:-C(\d{3}))?", part)
        if m:
            a = int(m[1]); b = int(m[2] or m[1]); ids.update(f"C{i:03d}" for i in range(a, b + 1))
    return ids


def build():
    items = json.loads((ROOT / "CHECKLIST.json").read_text())["items"]
    report = json.loads((ROOT / "conformance" / "pk_workflow_report.json").read_text())
    findings = {f["check_id"]: f for st in report["stages"] for f in st["findings"]}
    closure = json.loads((ROOT / "conformance" / "closure-status.json").read_text())["components"]
    reqs = json.loads((ROOT / "spec" / "requirements.json").read_text())["requirements"]
    rows, problems = [], []
    for it in items:
        cid = it["check_id"].split("-")[-1]
        comps = [c for c in closure if cid in expand(c["controls"])]
        rq = [r["id"] for r in reqs if cid in expand(r["controls"].replace("–", "-"))]
        f = findings.get(it["check_id"], {})
        paths = sorted({p for c in comps for p in c["artifacts"] + c["verification"]})
        missing = [p for p in paths if not (ROOT / p).exists()]
        if missing:
            problems.append(f"{cid}: missing {missing}")
        if not f:
            problems.append(f"{cid}: no pk_core finding")
        rows.append({"check_id": it["check_id"], "dimension": it["dimension"], "requirement": it["requirement"],
                     "pk_core_status": f.get("status"), "pk_core_evidence": f.get("evidence", []),
                     "closure_components": [c["n"] for c in comps], "closure_status": sorted({c["status"] for c in comps}),
                     "spec_requirements": rq, "artifacts": paths})
    return {"schema": "urn:pk:inv17:traceability:1", "rows": rows,
            "summary": {"checks": len(rows), "with_pk_finding": sum(1 for r in rows if r["pk_core_status"]),
                        "with_closure_component": sum(1 for r in rows if r["closure_components"]),
                        "with_spec_requirement": sum(1 for r in rows if r["spec_requirements"])}, "problems": problems}


if __name__ == "__main__":
    t = build()
    (ROOT / "traceability").mkdir(exist_ok=True)
    (ROOT / "traceability" / "requirements-traceability.json").write_text(json.dumps(t, indent=2) + "\n")
    print(json.dumps(t["summary"]), "problems:", len(t["problems"]))
    for p in t["problems"][:10]: print("  ", p)
    sys.exit(1 if "--check" in sys.argv and t["problems"] else 0)
