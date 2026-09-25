"""MC-06: generate the requirements-to-evidence matrix (100 checks) and validate it."""
from _common import PKG, dump
import json, re, sys
from registry import R

def coverage():
    """C-id -> MC ids, parsed from MISSING_COMPONENTS.md coverage column (ranges expanded)."""
    out: dict[str, set[str]] = {}
    for line in (PKG / "MISSING_COMPONENTS.md").read_text().splitlines():
        m = re.match(r"\| (MC-\d+) \|.*\| ([^|]*) \|$", line)
        if not m: continue
        for a, b in re.findall(r"C(\d{3})(?:-C?(\d{3}))?", m.group(2)):
            for n in range(int(a), int(b or a) + 1): out.setdefault(f"SCH-01-C{n:03d}", set()).add(m.group(1))
    return out

def build():
    items = json.loads((PKG / "CHECKLIST.json").read_text())["items"]
    shall = json.loads((PKG / "governance/SHALL.json").read_text())["requirements"]
    cov = coverage(); rows = []
    for it in items:
        cid = it["check_id"]; mcs = sorted(cov.get(cid, ()))
        states = sorted({R[m][0] for m in mcs})
        rows.append({"check_id": cid, "dimension": it["dimension"], "components": mcs,
                     "shall": sorted(s["id"] for s in shall if cid in s["checks"]),
                     "code": sorted({a for m in mcs for a in R[m][1]}), "tests": sorted({t for m in mcs for t in R[m][2]}),
                     "component_states": states, "owner": "UNASSIGNED",
                     "gate": "NOT_PASSED" if mcs else "UNMAPPED_TO_MC (4.2.0 engine or generic item)"})
    return {"schema": "PK_RTM/1", "rows": rows}

def validate(doc) -> list[str]:
    errs = []
    ids = [r["check_id"] for r in doc["rows"]]
    if len(ids) != 100 or len(set(ids)) != 100: errs.append("RTM must hold exactly 100 unique checks")
    for r in doc["rows"]:
        for p in r["code"]:
            if not (PKG / p).exists(): errs.append(f"{r['check_id']}: missing artifact {p}")
        if r["gate"] == "PASS" and r["owner"] == "UNASSIGNED": errs.append(f"{r['check_id']}: PASS without owner")
    return errs

if __name__ == "__main__":
    doc = build(); dump(PKG / "evidence/RTM.json", doc); errs = validate(doc)
    print(json.dumps({"rows": len(doc["rows"]), "mapped": sum(1 for r in doc["rows"] if r["components"]), "errors": errs}))
    sys.exit(1 if errs else 0)
