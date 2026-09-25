"""Requirements traceability validator and report generator (MC-04).

    python tools/traceability.py --check     # validate + verify MATRIX.md is current (CI)
    python tools/traceability.py --write     # regenerate traceability/REQUIREMENTS_MATRIX.md

Checks: controlled status vocabulary; every implementation/verification reference resolves
to an existing file and symbol (so renamed/deleted code cannot leave stale links); a
`verified` requirement cites at least one executable check; waiver-proposed/waived rows
cite an existing waiver; reverse map reports test files no requirement claims."""
from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DOC = ROOT / "traceability" / "requirements.json"
MATRIX = ROOT / "traceability" / "REQUIREMENTS_MATRIX.md"
EXEC_PREFIXES = ("tests/", "ci/", "benchmarks/", "tools/")


def _symbol_exists(path: pathlib.Path, symbol: str) -> bool:
    text = path.read_text(encoding="utf-8")
    parts = symbol.split(".")
    for part in parts:
        if not re.search(rf"^\s*(def|class)\s+{re.escape(part)}\b|^\s*{re.escape(part)}\s*[:=]", text, re.M):
            return False
    return True


def resolve(ref: str) -> str | None:
    """Return an error string or None."""
    file, _, sym = ref.partition("::")
    p = ROOT / file
    if not p.exists():
        return f"missing file {file}"
    if sym and p.is_file() and not _symbol_exists(p, sym):
        return f"missing symbol {ref}"
    return None


def load() -> dict:
    return json.loads(DOC.read_text(encoding="utf-8"))


def validate(doc: dict) -> dict:
    errors, warnings = [], []
    vocab = set(doc["statuses"])
    waivers = {w["id"] for w in json.loads((ROOT / "governance" / "waivers.json").read_text())["waivers"]}
    ids = set()
    claimed = set()
    for r in doc["requirements"]:
        rid = r["id"]
        if rid in ids:
            errors.append(f"{rid}: duplicate id")
        ids.add(rid)
        if r["status"] not in vocab:
            errors.append(f"{rid}: status {r['status']} not in vocabulary")
        for ref in r["implementation"] + r["verification"]:
            e = resolve(ref)
            if e:
                errors.append(f"{rid}: {e}")
        for ref in r["verification"]:
            claimed.add(ref.split("::")[0])
        if r["status"] == "verified" and not any(v.startswith(EXEC_PREFIXES) for v in r["verification"]):
            errors.append(f"{rid}: verified without an executable verification path")
        if r["criticality"] == "mandatory" and not r["verification"]:
            errors.append(f"{rid}: mandatory requirement without verification path")
        if r["status"] in ("waiver-proposed", "waived") and r.get("waiver") not in waivers:
            errors.append(f"{rid}: waiver {r.get('waiver')} not in governance/waivers.json")
        if r["status"] in ("partial", "blocked-external", "governance-pending", "implemented") and not r.get("note"):
            errors.append(f"{rid}: {r['status']} requires a note explaining the gap")
    tests = {str(p.relative_to(ROOT)) for p in (ROOT / "tests").rglob("test_*.py")}
    unclaimed = sorted(tests - claimed)
    if unclaimed:
        warnings.append(f"test files claimed by no requirement: {unclaimed}")
    counts: dict = {}
    for r in doc["requirements"]:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"ok": not errors, "errors": errors, "warnings": warnings, "counts": counts,
            "requirements": len(doc["requirements"])}


def render(doc: dict) -> str:
    lines = [f"# PLN-05 requirements traceability matrix ({doc['version']})", "",
             "Generated from `traceability/requirements.json` by `tools/traceability.py --write`; do not edit by hand.", "",
             "| ID | Status | Implementation | Verification | Note |", "|---|---|---|---|---|"]
    for r in doc["requirements"]:
        lines.append(f"| {r['id']} | {r['status']} | {'<br>'.join(r['implementation'])} | "
                     f"{'<br>'.join(r['verification'])} | {r.get('note') or ''} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    argv = argv or sys.argv[1:]
    doc = load()
    if "--write" in argv:
        MATRIX.write_text(render(doc), encoding="utf-8")
    res = validate(doc)
    if "--check" in argv and (not MATRIX.exists() or MATRIX.read_text(encoding="utf-8") != render(doc)):
        res["ok"] = False
        res["errors"].append("REQUIREMENTS_MATRIX.md is stale; run --write")
    print(json.dumps(res, indent=1))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
