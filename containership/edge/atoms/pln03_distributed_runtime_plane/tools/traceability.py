"""Generate TRACEABILITY.json (MC-011): checklist item -> MC finding -> requirement IDs -> implementation -> tests -> evidence."""
from __future__ import annotations

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def expand(spec: str) -> set[int]:
    out: set[int] = set()
    for part in spec.split(","):
        m = re.findall(r"C(\d+)", part)
        if len(m) == 2:
            out |= set(range(int(m[0]), int(m[1]) + 1))
        elif len(m) == 1:
            out.add(int(m[0]))
    return out


def main() -> None:
    items = json.loads((ROOT / "CHECKLIST.json").read_text())["items"]
    status = {i["id"]: i for i in json.loads((ROOT / "REMEDIATION_STATUS.json").read_text())["items"]}
    reqs = {}
    for line in (ROOT / "docs" / "REQUIREMENTS.md").read_text().splitlines():
        m = re.match(r"\| (REQ-[A-Z]+-\d+) \|.*\| (.+?) \| (.+?) \|$", line)
        if m:
            reqs[m.group(1)] = line
    mc_for: dict[int, list[str]] = {}
    for mid, st in status.items():
        for n in expand(st["checklist"]):
            mc_for.setdefault(n, []).append(mid)
    rows = []
    for it in items:
        mids = sorted(mc_for.get(it["ordinal"], []))
        arts = sorted({a for m in mids for a in status[m]["artifacts"]})
        tests = sorted({t for m in mids for t in status[m]["tests"]})
        req_ids = sorted({r for r, line in reqs.items() if any(a.split("/")[-1] and a.split("/")[-1] in line for a in arts if a.endswith(".py"))})
        sts = sorted({status[m]["status"] for m in mids})
        rows.append({"check_id": it["check_id"], "dimension": it["dimension"], "requirement": it["requirement"],
                     "findings": mids, "requirement_ids": req_ids, "implementation": arts, "tests": tests,
                     "status": sts or ["NO_FINDING (pk_core conformance: component.py)"],
                     "evidence": "evidence/EVIDENCE.json"})
    (ROOT / "TRACEABILITY.json").write_text(json.dumps({"schema": "pk.traceability/1",
        "version": (ROOT / "VERSION").read_text().strip(), "release_revision": None,
        "checklist": rows}, indent=2) + "\n")
    print(f"{len(rows)} rows; {sum(1 for r in rows if r['findings'])} linked to findings")


if __name__ == "__main__":
    main()
