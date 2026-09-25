"""Generate COMPONENT_STATUS.json and TRACEABILITY.json from the checklist + component_map.

Deterministic: output depends only on repository content (no timestamps, host
paths or interpreter versions), so regeneration on any host is byte-identical.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
PKG = HERE.parent
sys.path.insert(0, str(HERE))
import component_map  # noqa: E402

CHECKLIST_MD = PKG / "docs/checklist/inv55_secrets_integration_v4.2.0_COMPREHENSIVE_MISSING_COMPONENT_CHECKLIST.md"
_HEAD = re.compile(r"^### (\d+)\. (.+)$")
_PRIO = re.compile(r"^\*\*Priority:\*\* (P\d)")
_GAP = re.compile(r"^\*\*Audit gap:\*\* (.*)$")


def parse_checklist():
    comps, cur = {}, None
    for line in CHECKLIST_MD.read_text(encoding="utf-8").splitlines():
        m = _HEAD.match(line)
        if m:
            cur = int(m.group(1))
            comps[cur] = {"n": cur, "title": m.group(2).strip(), "priority": None, "audit_gap": None, "items": 0}
            continue
        if cur is None:
            continue
        if (m := _PRIO.match(line)):
            comps[cur]["priority"] = m.group(1)
        elif (m := _GAP.match(line)):
            comps[cur]["audit_gap"] = m.group(1)
        elif line.startswith("- [ ]"):
            comps[cur]["items"] += 1
    return comps


def artifact_exists(a: str) -> bool:
    path = re.split(r"::|#| \(", a, maxsplit=1)[0].strip()
    return (PKG / path).exists()


def build():
    comps = parse_checklist()
    rows, problems = [], []
    for n in range(1, 101):
        c = comps.get(n)
        if c is None:
            problems.append(f"component {n} missing from checklist")
            continue
        status, arts, tests, blocker = component_map.M[n]
        missing = [a for a in arts if not artifact_exists(a)]
        if missing:
            problems.append(f"#{n}: missing artifact(s) {missing}")
        if status == "IMPLEMENTED" and not tests:
            problems.append(f"#{n}: IMPLEMENTED without a named test")
        if status in ("PARTIAL", "BLOCKED", "DRAFTED") and not blocker:
            problems.append(f"#{n}: {status} without a blocker")
        crefs = sorted(set(re.findall(r"C0*(\d{1,3})", c["audit_gap"] or "")), key=int)
        rows.append({**c, "id": f"INV55-COMP-{n:03d}", "status": status, "artifacts": arts, "tests": tests,
                     "blocker": blocker, "owner": "UNASSIGNED", "approval": None, "complete": False,
                     "checklist_refs": [f"INV-55-C{int(x):03d}" for x in crefs]})
    status = {"schema": "inv55-component-status/1", "source": CHECKLIST_MD.relative_to(PKG).as_posix(),
              "rule": "complete == IMPLEMENTED + named tests passing + a valid human approval; nothing is complete in this snapshot",
              "components": rows}
    req_md = (PKG / "docs/requirements/REQUIREMENTS.md").read_text()
    reqs = []
    for line in req_md.splitlines():
        m = re.match(r"^\| (R-[A-Z]+-\d+) \| (.+?) \| (.+) \|$", line)
        if m:
            reqs.append({"id": m.group(1), "requirement": m.group(2), "tests": re.findall(r"`([^`]+)`", m.group(3))})
    checklist = json.loads((PKG / "CHECKLIST.json").read_text())
    by_ref = {}
    for r in rows:
        for ref in r["checklist_refs"]:
            by_ref.setdefault(ref, []).append(r["id"])
    trace = {"schema": "inv55-traceability/1",
             "requirements": reqs,
             "components": [{"id": r["id"], "title": r["title"], "status": r["status"], "artifacts": r["artifacts"],
                             "tests": r["tests"], "owner": r["owner"], "release_gate": "tools/gate.py::components"} for r in rows],
             "checklist_items": [{"check_id": it["check_id"], "dimension": it["dimension"],
                                  "components": by_ref.get(it["check_id"], [])} for it in checklist["items"]]}
    return status, trace, problems


def main():
    status, trace, problems = build()
    for p in problems:
        print("PROBLEM:", p)
    (PKG / "COMPONENT_STATUS.json").write_text(json.dumps(status, indent=1, sort_keys=True) + "\n")
    (PKG / "TRACEABILITY.json").write_text(json.dumps(trace, indent=1, sort_keys=True) + "\n")
    print(f"build_status: {len(status['components'])} components, {len(trace['requirements'])} requirements, {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
