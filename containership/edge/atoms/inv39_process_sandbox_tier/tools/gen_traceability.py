"""MC-011 — build TRACEABILITY.json: MC-001..106 status + C001..C100 -> MC mapping, derived from the
checklist's component index and tools/status_table.py.  Deterministic output."""
from __future__ import annotations

import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
from status_table import S  # noqa: E402

CHK = HERE / "docs" / "INV39_MISSING_COMPONENTS_IMPLEMENTATION_CHECKLIST_v5.0.0.md"


def expand(link: str) -> list[str]:
    out = []
    for a, b in re.findall(r"C(\d{3})(?:-C(\d{3}))?", link):
        out += [f"C{n:03d}" for n in range(int(a), int(b or a) + 1)]
    return out


def main():
    rows = re.findall(r"^\| (MC-\d{3}) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", CHK.read_text(), re.M)
    assert len(rows) == 106, len(rows)
    checks = json.loads((HERE / "CHECKLIST.json").read_text())["items"]
    comps, by_check = [], {c["check_id"].split("-")[-1]: [] for c in checks}
    for mc, prio, cat, title, link in rows:
        status, code, tests, gap = S[mc]
        cs = expand(link)
        for c in cs:
            by_check.setdefault(c, []).append(mc)
        comps.append({"id": mc, "priority": prio.strip(), "category": cat.strip(), "component": title.strip(),
                      "checks": cs, "status": status, "code": code, "tests": tests, "gap": gap,
                      "owner": "_UNASSIGNED_", "accepted": False})
    trace = [{"check": f"INV-39-{c['check_id'].split('-')[-1]}", "dimension": c["dimension"],
              "requirement": c["requirement"], "components": by_check.get(c["check_id"].split("-")[-1], []),
              "status": ("NO_RESIDUAL_GAP" if not by_check.get(c["check_id"].split("-")[-1]) else
                         min((next(x["status"] for x in comps if x["id"] == m) for m in by_check[c["check_id"].split("-")[-1]]),
                             key=["BLOCKED", "PARTIAL", "IMPLEMENTED"].index)),
              "owner": "_UNASSIGNED_"} for c in checks]
    summary = {s: sum(1 for c in comps if c["status"] == s) for s in ("IMPLEMENTED", "PARTIAL", "BLOCKED")}
    doc = {"schema": "INV39_TRACEABILITY/1", "version": (HERE / "VERSION").read_text().strip(),
           "summary": summary, "accepted": 0, "components": comps, "checks": trace}
    (HERE / "TRACEABILITY.json").write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
