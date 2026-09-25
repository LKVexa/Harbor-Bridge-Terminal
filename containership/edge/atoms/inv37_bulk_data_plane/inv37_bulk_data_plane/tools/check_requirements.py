"""CI rule for REQUIREMENTS.md (C011, C020): every normative row has a unique
ID, an RFC-2119 keyword, a known owner role, an allowed verification method,
>=1 valid checklist trace and existing evidence paths."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
METHODS = {"unit", "contract", "integration", "benchmark", "security", "fuzz", "inspection", "operational"}
KWS = {"SHALL", "SHALL NOT", "SHOULD", "SHOULD NOT", "MAY"}


def check() -> list[str]:
    roles = set(json.loads((HERE / "governance" / "OWNERS.json").read_text())["roles"])
    ids = {i["check_id"][7:] for i in json.loads((HERE / "CHECKLIST.json").read_text())["items"]}
    problems, seen = [], set()
    rows = [l for l in (HERE / "REQUIREMENTS.md").read_text().splitlines() if l.startswith("| REQ-")]
    if not rows:
        return ["no requirements found"]
    for l in rows:
        cols = [c.strip() for c in l.strip("|").split("|")]
        if len(cols) != 7:
            problems.append(f"malformed row: {l[:40]}")
            continue
        rid, kw, text, owner, method, trace, ev = cols
        if rid in seen:
            problems.append(f"{rid}: duplicate id")
        seen.add(rid)
        if kw not in KWS or kw.split()[0] not in text:
            problems.append(f"{rid}: keyword missing/inconsistent")
        if owner not in roles:
            problems.append(f"{rid}: unknown owner {owner}")
        if method not in METHODS:
            problems.append(f"{rid}: bad verification {method}")
        cs = re.findall(r"C\d{3}", trace)
        if not cs or any(c not in ids for c in cs):
            problems.append(f"{rid}: bad trace {trace}")
        for p in [x.strip() for x in ev.split(";") if x.strip()]:
            if not (HERE / p).exists():
                problems.append(f"{rid}: evidence path missing {p}")
    return problems


if __name__ == "__main__":
    p = check()
    print(json.dumps({"status": "FAIL" if p else "PASS", "problems": p}, indent=1))
    sys.exit(1 if p else 0)
