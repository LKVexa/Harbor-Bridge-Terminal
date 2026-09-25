"""INV-38-C020 — Requirements Traceability Matrix generation and validation.

Generates traceability/INV38_RTM.{json,csv} from the canonical remediation_status
data and validates the invariants required by C020-T05: exactly 100 unique IDs,
no unknown IDs, and no item claiming completion without a linked evidence
artifact.  A human-readable report is generated from the same machine-readable
source so audit output cannot drift (C020-T06).
"""
from __future__ import annotations
import csv, hashlib, io, json, os

from . import remediation_status as rs

EVIDENCE_REQUIRED = {"DONE"}          # DONE must carry evidence + a test
FIELDS = ["id", "dimension", "priority", "status", "artifacts", "tests", "evidence", "note", "in_remediation_scope"]

def build() -> dict:
    data = rs.full_status()
    rows = []
    for cid in rs.ALL_IDS:
        item = data[cid]
        rows.append({
            "id": item["id"], "dimension": item["dimension"], "priority": item["priority"],
            "status": item["status"], "artifacts": ";".join(item["artifacts"]),
            "tests": ";".join(item["tests"]), "evidence": ";".join(item["evidence"]),
            "note": item["note"], "in_remediation_scope": item["in_remediation_scope"],
        })
    return {"schema": "rtm/1", "element": "INV-38", "rows": rows}

def validate(rtm: dict) -> list[str]:
    problems = []
    ids = [r["id"] for r in rtm["rows"]]
    if len(ids) != 100:
        problems.append(f"expected 100 IDs, found {len(ids)}")
    if len(set(ids)) != len(ids):
        problems.append("duplicate requirement IDs present")
    expected = {f"INV-38-{c}" for c in rs.ALL_IDS}
    unknown = set(ids) - expected
    if unknown:
        problems.append(f"unknown IDs: {sorted(unknown)}")
    for r in rtm["rows"]:
        if r["status"] in EVIDENCE_REQUIRED and not (r["evidence"] and r["tests"]):
            problems.append(f"{r['id']} is {r['status']} but lacks evidence/tests")
        if r["status"] == "DONE" and not r["artifacts"]:
            problems.append(f"{r['id']} DONE without repository artifact")
    return problems

def to_csv(rtm: dict) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=FIELDS)
    w.writeheader()
    for r in rtm["rows"]:
        w.writerow(r)
    return buf.getvalue()

def digest(rtm: dict) -> str:
    return hashlib.sha256(json.dumps(rtm, sort_keys=True).encode()).hexdigest()

def rollup(rtm: dict) -> dict:
    from collections import Counter
    scope = [r for r in rtm["rows"] if r["in_remediation_scope"]]
    return {"in_scope_total": len(scope),
            "by_status": dict(Counter(r["status"] for r in scope))}

def write_all(repo_root: str) -> dict:
    rtm = build()
    problems = validate(rtm)
    if problems:
        raise ValueError("RTM invalid:\n" + "\n".join(problems))
    trace = os.path.join(repo_root, "traceability")
    os.makedirs(trace, exist_ok=True)
    with open(os.path.join(trace, "INV38_RTM.json"), "w") as f:
        json.dump(rtm, f, indent=2, sort_keys=True)
    with open(os.path.join(trace, "INV38_RTM.csv"), "w") as f:
        f.write(to_csv(rtm))
    return {"digest": digest(rtm), "rollup": rollup(rtm)}

if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.dirname(__file__))
    print(json.dumps(write_all(root), indent=2))
